"""Agent Lab tool-use loop.

Runs: model → (optional tools) → model … until a final text answer.
Returns reply_text, result cards, and a structured ``trace`` for the notes UI.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

from providers import complete, provider_info
from tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger("nyc_tonight.agent")

MAX_TOOL_ROUNDS = int(os.getenv("MAX_TOOL_ROUNDS", "5"))

SYSTEM_PROMPT = """You are NYC Tonight, a concise, friendly concierge for New York City and a
demo agent for learners. You help people find restaurants, check the weather, and find live events.

How you work:
- Use the tools to fetch REAL data. Never invent restaurants, events, ratings, addresses, dates, weather, or links.
- Answer ONLY the CURRENT user message. Do not continue or reopen earlier topics
  (for example, do not fetch restaurants again after a weather-only follow-up).
- After you have the tool results for this ask, give a short final answer. Do not call extra tools
  "to be helpful" unless the user asked for them now.
- Pick the right tool(s) from what is offered this turn.
- Translate vague language into filters: "cheap" stays informal (Open Data has no price tier);
  infer neighborhood/cuisine from context; "tonight" means today.
- Default location is New York City.

Your final reply:
- Keep it short: 1-3 sentences. The app shows result CARDS below your text, so do NOT list
  every result. Briefly frame the picks.
- If a tool fails or returns nothing, say so briefly and offer what you did find.
- Never promise to make a booking. Reservation links open a search page the user completes."""


def _has_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    """True if any phrase appears as a whole word/phrase (avoids 'eat' in 'weather')."""
    for phrase in phrases:
        if " " in phrase:
            if phrase in text:
                return True
        elif re.search(rf"\b{re.escape(phrase)}\b", text):
            return True
    return False


def _tools_for_message(message: str) -> list[dict[str, Any]]:
    """Narrow tool schemas to the current ask so history cannot pull in extra tools.

    Weather-only / food-only / events-only get a focused tool set. Broader asks get all tools.
    """
    m = (message or "").lower()
    weather = _has_phrase(
        m,
        (
            "weather",
            "temperature",
            "forecast",
            "raining",
            "rainy",
            "humid",
            "humidity",
            "how hot",
            "how cold",
            "umbrella",
        ),
    )
    food = _has_phrase(
        m,
        (
            "dinner",
            "lunch",
            "brunch",
            "breakfast",
            "restaurant",
            "restaurants",
            "eat",
            "food",
            "cuisine",
            "dining",
            "hungry",
            "reserve",
            "reservation",
        ),
    )
    events = _has_phrase(
        m,
        (
            "event",
            "events",
            "concert",
            "concerts",
            "show",
            "shows",
            "comedy",
            "sports",
            "theater",
            "theatre",
            "tickets",
            "music",
            "what's happening",
            "whats happening",
            "something fun",
        ),
    )
    plan = _has_phrase(
        m, ("plan my night", "plan a night", "whole night", "night out")
    )

    if plan or (weather and food) or (weather and events) or (food and events):
        return TOOL_DEFINITIONS

    allowed: set[str] | None = None
    if weather and not food and not events:
        allowed = {"get_weather"}
    elif food and not weather and not events:
        allowed = {"search_restaurants", "build_reservation_link"}
    elif events and not weather and not food:
        allowed = {"search_events"}

    if not allowed:
        return TOOL_DEFINITIONS
    return [t for t in TOOL_DEFINITIONS if t["name"] in allowed]


def run_agent(
    message: str,
    conversation_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    info = provider_info()
    if info.name == "groq" and not info.configured:
        return _setup_reply(
            "GROQ_API_KEY is missing. Add it to backend/.env or switch to Ollama "
            "(unset LLM_PROVIDER / use LLM_PROVIDER=ollama)."
        )
    if info.name == "anthropic" and not info.configured:
        return _setup_reply(
            "ANTHROPIC_API_KEY is missing. Prefer Groq (GROQ_API_KEY) or Ollama for the free lab."
        )

    messages: list[dict[str, Any]] = []
    for turn in conversation_history or []:
        role = turn.get("role")
        text = turn.get("content")
        if role in ("user", "assistant") and text:
            messages.append({"role": role, "content": text})
    messages.append({"role": "user", "content": message})

    tool_defs = _tools_for_message(message)
    logger.info(
        "tools_for_message=%s",
        [t["name"] for t in tool_defs],
    )

    collected_cards: list[dict[str, Any]] = []
    rounds: list[dict[str, Any]] = []

    for round_num in range(MAX_TOOL_ROUNDS):
        t0 = time.perf_counter()
        try:
            response = complete(
                system=SYSTEM_PROMPT,
                messages=messages,
                tool_definitions=tool_defs,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("LLM call failed")
            return {
                "reply_text": f"I hit an error talking to the AI service ({exc}). Please try again.",
                "results": _dedupe_cards(collected_cards),
                "trace": _build_trace(info, rounds, error=str(exc)),
            }

        latency_ms = int((time.perf_counter() - t0) * 1000)
        tool_calls = response.get("tool_calls") or []
        assistant_text = (response.get("content") or "").strip()

        round_entry: dict[str, Any] = {
            "round": round_num,
            "stop_reason": response.get("stop_reason"),
            "assistant_text": assistant_text or None,
            "tool_calls": [
                {"id": tc["id"], "name": tc["name"], "input": tc.get("arguments") or {}}
                for tc in tool_calls
            ],
            "tool_results": [],
            "latency_ms": latency_ms,
        }

        if response.get("stop_reason") != "tool_use" or not tool_calls:
            rounds.append(round_entry)
            reply = assistant_text or "Here's what I found."
            return {
                "reply_text": reply,
                "results": _dedupe_cards(collected_cards),
                "trace": _build_trace(info, rounds),
            }

        # Persist assistant turn (OpenAI-style with tool_calls)
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": assistant_text or None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc.get("arguments") or {}),
                    },
                }
                for tc in tool_calls
            ],
        }
        messages.append(assistant_msg)

        for tc in tool_calls:
            logger.info("Round %d: tool=%s input=%s", round_num, tc["name"], tc.get("arguments"))
            outcome = execute_tool(tc["name"], tc.get("arguments") or {})
            collected_cards.extend(outcome.get("cards", []))
            content_payload = outcome.get("content", {})
            summary = _summarize_tool_result(tc["name"], content_payload)
            round_entry["tool_results"].append(
                {
                    "tool_use_id": tc["id"],
                    "name": tc["name"],
                    "summary": summary,
                    "ok": bool(content_payload.get("ok", True)),
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(content_payload),
                }
            )

        rounds.append(round_entry)

    # Max rounds — ask for a final answer without tools
    try:
        messages.append(
            {
                "role": "user",
                "content": "Please give your final short answer now based on the results so far.",
            }
        )
        final = complete(
            system=SYSTEM_PROMPT,
            messages=messages,
            tool_definitions=[],  # no tools
        )
        reply_text = (final.get("content") or "").strip()
    except Exception:  # noqa: BLE001
        reply_text = ""

    return {
        "reply_text": reply_text or "Here are the best matches I could find.",
        "results": _dedupe_cards(collected_cards),
        "trace": _build_trace(info, rounds, truncated=True),
    }


def _setup_reply(text: str) -> dict[str, Any]:
    info = provider_info()
    return {
        "reply_text": text,
        "results": [],
        "trace": _build_trace(info, [], error=text),
    }


def _build_trace(
    info: Any,
    rounds: list[dict[str, Any]],
    *,
    error: str | None = None,
    truncated: bool = False,
) -> dict[str, Any]:
    tool_names: list[str] = []
    for r in rounds:
        for tc in r.get("tool_calls") or []:
            if tc.get("name") and tc["name"] not in tool_names:
                tool_names.append(tc["name"])
    return {
        "provider": info.name,
        "model": info.model,
        "round_count": len(rounds),
        "tools_used": tool_names,
        "rounds": rounds,
        "error": error,
        "truncated": truncated,
    }


def _summarize_tool_result(name: str, content: dict[str, Any]) -> str:
    if not content.get("ok", True) and content.get("message"):
        return str(content["message"])
    if name == "get_weather":
        temp = content.get("temperature_f")
        summary = content.get("summary") or content.get("condition")
        bits = [b for b in [summary, f"{temp}°F" if temp is not None else None] if b]
        return ", ".join(bits) if bits else "Weather fetched"
    count = content.get("count")
    if count is not None:
        return f"{count} result(s)"
    if content.get("url"):
        return f"Link ready ({content.get('platform', 'reservation')})"
    return "Done"


def _dedupe_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for c in cards:
        key = (c.get("type", ""), (c.get("name") or "").lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out
