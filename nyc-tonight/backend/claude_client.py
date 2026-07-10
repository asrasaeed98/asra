"""Claude client: runs the tool-use loop for the NYC Tonight agent.

Given a user message + prior conversation, this sends the request to Claude
with the tool definitions, executes any tools Claude asks for, feeds the
results back, and repeats until Claude produces a final text answer.

Returns (reply_text, cards) where ``cards`` is the accumulated list of
structured result cards produced by the search tools, for the frontend.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from anthropic import Anthropic

from tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger("nyc_tonight.claude")

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = int(os.getenv("ANTHROPIC_MAX_TOKENS", "1200"))
MAX_TOOL_ROUNDS = int(os.getenv("MAX_TOOL_ROUNDS", "5"))

SYSTEM_PROMPT = """You are NYC Tonight, a concise, friendly concierge for New York City.
You help people find restaurants to eat at and live events to go to tonight (or on a given date).

How you work:
- Use the tools to fetch REAL data. Never invent restaurants, events, ratings, addresses, dates, or links.
- Pick the right tool(s) for the request:
  - Dining / food / drinks -> search_restaurants
  - Concerts / shows / sports / comedy / "what's happening" / "something fun" -> search_events
  - A broad "plan my night" request -> call BOTH search_restaurants and search_events.
- Translate vague language into concrete filters yourself: "cheap" -> price_tier 1, "moderate" -> 2,
  "nice/upscale" -> 3-4; "tonight" -> today's date; infer neighborhood and cuisine from context.
- Default the NYC location context; the user is in New York City unless they say otherwise.

Your final reply:
- Keep it short and conversational — 1-3 sentences. The app renders result CARDS below your text,
  so do NOT list every result or repeat all addresses/links. Instead, briefly frame the picks
  ("Here are a few cheap dinner spots in Chinatown, all open now — the top one is a solid bet.").
- If a data source returns nothing or fails, say so briefly and offer the alternative you did find
  (e.g. "No events matched tonight, but here are some dinner options nearby.").
- Never promise to make a booking. Reservation links just open a pre-filled search page the user
  completes themselves."""


def _extract_text(content_blocks: list[Any]) -> str:
    parts = [b.text for b in content_blocks if getattr(b, "type", None) == "text"]
    return "\n".join(p for p in parts if p).strip()


def run_agent(
    message: str,
    conversation_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the full tool-use loop for one user turn.

    ``conversation_history`` is a list of {role, content} dicts where content is
    plain text (prior user/assistant turns from the frontend).
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "reply_text": "The server is missing ANTHROPIC_API_KEY, so I can't think right now. "
            "Add it to the backend .env and restart.",
            "results": [],
        }

    client = Anthropic(api_key=api_key)

    messages: list[dict[str, Any]] = []
    for turn in conversation_history or []:
        role = turn.get("role")
        text = turn.get("content")
        if role in ("user", "assistant") and text:
            messages.append({"role": role, "content": text})
    messages.append({"role": "user", "content": message})

    collected_cards: list[dict[str, Any]] = []

    for round_num in range(MAX_TOOL_ROUNDS):
        try:
            response = client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Anthropic API call failed")
            return {
                "reply_text": f"I hit an error talking to the AI service ({exc}). Please try again.",
                "results": collected_cards,
            }

        # Persist the assistant turn (may contain text and/or tool_use blocks).
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            reply_text = _extract_text(response.content) or "Here's what I found."
            return {"reply_text": reply_text, "results": _dedupe_cards(collected_cards)}

        # Execute every tool_use block and build the tool_result turn.
        tool_results = []
        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            logger.info("Round %d: tool=%s input=%s", round_num, block.name, block.input)
            outcome = execute_tool(block.name, block.input or {})
            collected_cards.extend(outcome.get("cards", []))
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(outcome.get("content", {})),
                }
            )

        messages.append({"role": "user", "content": tool_results})

    # Ran out of tool rounds — ask for a final summary without tools.
    try:
        final = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages
            + [
                {
                    "role": "user",
                    "content": "Please give your final short answer now based on the results so far.",
                }
            ],
        )
        reply_text = _extract_text(final.content)
    except Exception:  # noqa: BLE001
        reply_text = ""

    return {
        "reply_text": reply_text or "Here are the best matches I could find.",
        "results": _dedupe_cards(collected_cards),
    }


def _dedupe_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop duplicate cards (same type+name) while preserving order."""
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for c in cards:
        key = (c.get("type", ""), (c.get("name") or "").lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out
