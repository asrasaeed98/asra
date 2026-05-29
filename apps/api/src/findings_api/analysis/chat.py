"""Grounded chat over computed analysis results (cost-bounded)."""

from __future__ import annotations

import json
import logging
from typing import Any

from findings_api.analysis.ai_usage import BUDGET_MESSAGE
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
    "Answer ONLY using the analysis results provided in the user message "
    "(the AI summary, the computed findings, and the dataset facts). "
    "Use 'dataset_facts' to answer basic factual questions about the data — e.g. "
    "the time/year coverage (from a column's min/max or time_coverage), the number "
    "of rows, how many distinct categories or countries, and value ranges. "
    "When a column lists its full 'values', you may confirm whether a specific item "
    "(e.g. a country, region, or category) is present or absent by checking that list. "
    "If a column only shows 'examples' (too many values to list in full), say you can "
    "only see a sample and can't fully confirm membership. "
    "If the results do not contain the answer, say you don't have that information "
    "from this analysis rather than guessing. "
    "Never claim causation from a correlation or group difference. "
    "Do not predict future values and do not invent numbers — only cite figures that "
    "appear in the provided results. "
    "Keep replies under 120 words, in plain language, and avoid jargon."
)


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


def build_chat_context(results: dict[str, Any]) -> dict[str, Any]:
    """Compact, grounded context — never the raw dataset."""
    report = results.get("analysis_report") or {}
    datasets = [d.get("title") for d in (report.get("datasets") or []) if d.get("title")]
    glossary = results.get("column_glossary") or []
    fields = [
        {"field": g.get("label") or g.get("name"), "about": g.get("description")}
        for g in glossary
        if g.get("description") or (g.get("label") and g.get("label") != g.get("name"))
    ]
    # dataset_facts answers basic factual questions (year coverage, value ranges,
    # row counts, distinct categories) cheaply — listed first so it survives the
    # context truncation cap.
    return {
        "datasets": datasets,
        "dataset_facts": results.get("dataset_facts") or [],
        "summary": results.get("ai_summary"),
        "findings": _compact_findings(results),
        "fields": fields[:20],
    }


def generate_chat_reply(
    results: dict[str, Any],
    history: list[dict[str, str]],
    question: str,
) -> dict[str, Any]:
    """Return {reply, tokens_in, tokens_out, grounded}. Always safe to call."""
    if not settings.anthropic_api_key:
        return {
            "reply": "Chat is unavailable because the server has no AI key configured.",
            "tokens_in": 0,
            "tokens_out": 0,
            "grounded": False,
            "ok": False,
        }

    try:
        import anthropic

        context = build_chat_context(results)
        context_json = json.dumps(context, ensure_ascii=False, default=str)[
            : settings.chat_context_char_cap
        ]

        messages: list[dict[str, str]] = []
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
                    "Analysis results (your only source of truth):\n"
                    f"{context_json}\n\nUser question: {question}"
                ),
            }
        )

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model_chat,
            max_tokens=settings.chat_max_tokens,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        reply = "".join(b.text for b in response.content if b.type == "text").strip()
        usage = getattr(response, "usage", None)
        tokens_in = int(getattr(usage, "input_tokens", 0) or 0)
        tokens_out = int(getattr(usage, "output_tokens", 0) or 0)
        if not reply:
            reply = "I couldn't generate an answer for that. Try rephrasing your question."
        return {
            "reply": reply,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "grounded": True,
            "ok": True,
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
            }
        return {
            "reply": "Something went wrong answering that. Please try again in a moment.",
            "tokens_in": 0,
            "tokens_out": 0,
            "grounded": False,
            "ok": False,
        }


def _is_budget_error(exc: Exception) -> bool:
    if type(exc).__name__ in _BUDGET_ERROR_TYPES:
        return True
    text = str(exc).lower()
    return any(hint in text for hint in _BUDGET_ERROR_HINTS)
