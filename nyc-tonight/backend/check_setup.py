#!/usr/bin/env python3
"""Quick local setup check for clones. Run from backend/: python check_setup.py"""

from __future__ import annotations

import sys

from dotenv import load_dotenv

load_dotenv()

from agent_loop import _tools_for_message  # noqa: E402
from providers import ollama_reachable, provider_info  # noqa: E402
from tools import TOOL_DEFINITIONS, tool_sources_status  # noqa: E402


def main() -> int:
    info = provider_info()
    print(f"provider: {info.name} ({info.model}) configured={info.configured} [{info.detail}]")
    if info.name == "ollama":
        print(f"ollama_reachable: {ollama_reachable()}")
    print(f"tools: {[t['name'] for t in TOOL_DEFINITIONS]}")
    print(f"sources: {tool_sources_status()}")

    samples = {
        "What's the weather like today?": ["get_weather"],
        "Find me dinner in Chinatown tonight": [
            "search_restaurants",
            "build_reservation_link",
        ],
    }
    ok = True
    for msg, expect in samples.items():
        got = [t["name"] for t in _tools_for_message(msg)]
        match = got == expect
        ok = ok and match
        print(f"route {msg!r} -> {got} {'OK' if match else 'FAIL expected ' + str(expect)}")

    if info.name == "groq" and not info.configured:
        print("HINT: set GROQ_API_KEY in .env (or use Ollama)")
        return 1
    if info.name == "ollama" and not ollama_reachable():
        print("HINT: start Ollama and pull a model, or set GROQ_API_KEY")
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
