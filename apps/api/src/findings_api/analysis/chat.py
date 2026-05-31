"""Grounded chat over computed analysis results (cost-bounded)."""

from __future__ import annotations

import json
import logging
from typing import Any

import duckdb

from findings_api.analysis.ai_usage import BUDGET_MESSAGE
from findings_api.analysis.chat_sql import build_query_schema, execute_chat_query
from findings_api.config import settings

logger = logging.getLogger(__name__)

# Substrings / exception names that indicate we've exhausted credit or hit limits.
_BUDGET_ERROR_HINTS = (
    "credit",
    "insufficient",
    "quota",
    "billing",
    "rate limit",
    "rate_limit",
    "too many requests",
)
_BUDGET_ERROR_TYPES = {
    "RateLimitError",
    "AuthenticationError",
    "PermissionDeniedError",
}

SYSTEM_PROMPT = (
    "You are a careful data-analyst assistant embedded in an analytics app. "
    "Answer using the analysis results provided (summary, findings, dataset facts) "
    "and, when needed, the run_duckdb_query tool to look up row-level facts from "
    "the user's loaded session tables. "
    "Use the tool for questions that need rankings, specific countries/entities, "
    "or values not already in the results — e.g. highest/lowest by country. "
    "Write read-only SELECT queries only; prefer analysis_* or cross_measure_* tables. "
    "For rankings on joined indicators, use cross_measure_merged when present. "
    "Use dataset_facts for coverage questions (years, row counts, value ranges). "
    "When a column lists its full 'values', you may confirm membership. "
    "If examples only are shown, say membership cannot be fully confirmed. "
    "If the user asks about individual countries but entities are regional/income "
    "groupings only (e.g. 'IDA only', 'East Asia & Pacific'), say that limitation "
    "once, then answer with the best available grouping from the data. "
    "Never claim causation from a correlation. "
    "Do not invent numbers — cite figures from results or query output only. "
    "Do not ask follow-up questions. Do not offer to help load data, run a new "
    "analysis, or do anything outside this chat — you cannot. "
    "When something is not in the loaded data, state the gap in one sentence and stop. "
    "Never narrate upcoming actions (e.g. 'Let me query', 'I'll check'). "
    "When row-level data is needed, call run_duckdb_query immediately, then answer "
    "with the query results in the same reply. "
    "Use short bullet lists for comparisons; do not use markdown tables. "
    "Keep replies under 120 words, plain language."
)

_QUERY_PROMISE_HINTS = (
    "let me query",
    "i'll query",
    "i will query",
    "let me check",
    "i'll check",
    "i will check",
    "let me look",
    "i'll look",
    "i will look",
)

_DUCKDB_TOOL = {
    "name": "run_duckdb_query",
    "description": (
        "Run a read-only SELECT on the session DuckDB tables to fetch rows needed "
        "to answer the user (rankings, top/bottom entities, specific values). "
        "Results are capped at 25 rows."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "Single SELECT statement using allowed session tables.",
            },
            "purpose": {
                "type": "string",
                "description": "One short phrase describing what the query retrieves.",
            },
        },
        "required": ["sql"],
    },
}


def _compact_findings(results: dict[str, Any]) -> list[dict[str, Any]]:
    findings = results.get("findings") or []
    display_ids = set(results.get("display_finding_ids") or [])
    chosen = [f for f in findings if f.get("id") in display_ids] or findings[:6]
    out: list[dict[str, Any]] = []
    for f in chosen[:8]:
        details = f.get("details") or {}
        out.append(
            {
                "headline": details.get("headline") or f.get("title"),
                "impact": details.get("impact"),
                "type": f.get("type"),
                "fields": f.get("columns"),
                "n": f.get("n"),
                "p_value": f.get("p_value"),
                "effect": f.get("value"),
            }
        )
    return out


def build_chat_context(
    results: dict[str, Any],
    *,
    query_schema: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compact, grounded context — never the raw dataset."""
    report = results.get("analysis_report") or {}
    datasets = [d.get("title") for d in (report.get("datasets") or []) if d.get("title")]
    glossary = results.get("column_glossary") or []
    fields = [
        {"field": g.get("label") or g.get("name"), "about": g.get("description")}
        for g in glossary
        if g.get("description") or (g.get("label") and g.get("label") != g.get("name"))
    ]
    ctx: dict[str, Any] = {
        "datasets": datasets,
        "analysis_mode": report.get("analysis_mode"),
        "dataset_facts": results.get("dataset_facts") or [],
        "summary": results.get("ai_summary"),
        "findings": _compact_findings(results),
        "fields": fields[:20],
    }
    if query_schema:
        ctx["queryable_tables"] = query_schema
    return ctx


def _usage_tokens(response) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    return (
        int(getattr(usage, "input_tokens", 0) or 0),
        int(getattr(usage, "output_tokens", 0) or 0),
    )


def _text_from_response(response) -> str:
    return "".join(b.text for b in response.content if b.type == "text").strip()


def _looks_like_query_promise(reply: str, *, query_used: bool) -> bool:
    """Model sometimes ends with 'Let me query…' without calling the tool."""
    if query_used or not reply:
        return False
    low = reply.lower().strip()
    if len(low) > 180:
        return False
    return any(hint in low for hint in _QUERY_PROMISE_HINTS)


def generate_chat_reply(
    results: dict[str, Any],
    history: list[dict[str, str]],
    question: str,
    *,
    conn: duckdb.DuckDBPyConnection | None = None,
) -> dict[str, Any]:
    """Return {reply, tokens_in, tokens_out, grounded, ok, query_used}."""
    if not settings.anthropic_api_key:
        return {
            "reply": "Chat is unavailable because the server has no AI key configured.",
            "tokens_in": 0,
            "tokens_out": 0,
            "grounded": False,
            "ok": False,
            "query_used": False,
        }

    try:
        import anthropic

        query_schema = build_query_schema(conn) if conn is not None else None
        context = build_chat_context(results, query_schema=query_schema)
        context_json = json.dumps(context, ensure_ascii=False, default=str)[
            : settings.chat_context_char_cap
        ]

        messages: list[dict[str, Any]] = []
        turn_cap = settings.chat_history_turns * 2
        for turn in history[-turn_cap:]:
            role = turn.get("role")
            content = turn.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": str(content)})
        messages.append(
            {
                "role": "user",
                "content": (
                    "Analysis results (primary source; use run_duckdb_query when row-level "
                    "data is missing):\n"
                    f"{context_json}\n\nUser question: {question}"
                ),
            }
        )

        tools = [_DUCKDB_TOOL] if conn is not None and query_schema else None
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        tokens_in = 0
        tokens_out = 0
        query_used = False
        max_rounds = settings.chat_max_query_rounds if tools else 0

        response = client.messages.create(
            model=settings.anthropic_model_chat,
            max_tokens=settings.chat_max_tokens,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=tools,
        )
        tin, tout = _usage_tokens(response)
        tokens_in += tin
        tokens_out += tout

        rounds = 0
        while response.stop_reason == "tool_use" and conn is not None and rounds < max_rounds:
            rounds += 1
            query_used = True
            messages.append({"role": "assistant", "content": response.content})
            tool_results: list[dict[str, Any]] = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                if block.name != "run_duckdb_query":
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"ok": False, "error": "Unknown tool"}),
                            "is_error": True,
                        }
                    )
                    continue
                sql = str((block.input or {}).get("sql") or "")
                payload = execute_chat_query(conn, sql)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(payload, ensure_ascii=False, default=str)[
                            :8000
                        ],
                    }
                )
            messages.append({"role": "user", "content": tool_results})
            response = client.messages.create(
                model=settings.anthropic_model_chat,
                max_tokens=settings.chat_max_tokens,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=tools,
            )
            tin, tout = _usage_tokens(response)
            tokens_in += tin
            tokens_out += tout

        reply = _text_from_response(response)
        if _looks_like_query_promise(reply, query_used=query_used) and tools:
            messages.append({"role": "assistant", "content": response.content})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Call run_duckdb_query now and answer with the results. "
                        "Do not say you will query — include the answer."
                    ),
                }
            )
            response = client.messages.create(
                model=settings.anthropic_model_chat,
                max_tokens=settings.chat_max_tokens,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=tools,
            )
            tin, tout = _usage_tokens(response)
            tokens_in += tin
            tokens_out += tout
            rounds = 0
            while response.stop_reason == "tool_use" and conn is not None and rounds < max_rounds:
                rounds += 1
                query_used = True
                messages.append({"role": "assistant", "content": response.content})
                tool_results: list[dict[str, Any]] = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    if block.name != "run_duckdb_query":
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps({"ok": False, "error": "Unknown tool"}),
                                "is_error": True,
                            }
                        )
                        continue
                    sql = str((block.input or {}).get("sql") or "")
                    payload = execute_chat_query(conn, sql)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(payload, ensure_ascii=False, default=str)[
                                :8000
                            ],
                        }
                    )
                messages.append({"role": "user", "content": tool_results})
                response = client.messages.create(
                    model=settings.anthropic_model_chat,
                    max_tokens=settings.chat_max_tokens,
                    system=SYSTEM_PROMPT,
                    messages=messages,
                    tools=tools,
                )
                tin, tout = _usage_tokens(response)
                tokens_in += tin
                tokens_out += tout
            reply = _text_from_response(response)

        if _looks_like_query_promise(reply, query_used=query_used):
            return {
                "reply": "I couldn't complete that lookup. Please try asking again.",
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "grounded": False,
                "ok": False,
                "query_used": query_used,
            }

        if not reply:
            reply = "I couldn't generate an answer for that. Try rephrasing your question."
        return {
            "reply": reply,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "grounded": True,
            "ok": True,
            "query_used": query_used,
        }
    except Exception as exc:
        logger.exception("Chat reply generation failed")
        if _is_budget_error(exc):
            return {
                "reply": BUDGET_MESSAGE,
                "tokens_in": 0,
                "tokens_out": 0,
                "grounded": False,
                "ok": False,
                "query_used": False,
            }
        return {
            "reply": "Something went wrong answering that. Please try again in a moment.",
            "tokens_in": 0,
            "tokens_out": 0,
            "grounded": False,
            "ok": False,
            "query_used": False,
        }


def _is_budget_error(exc: Exception) -> bool:
    if type(exc).__name__ in _BUDGET_ERROR_TYPES:
        return True
    text = str(exc).lower()
    return any(hint in text for hint in _BUDGET_ERROR_HINTS)
