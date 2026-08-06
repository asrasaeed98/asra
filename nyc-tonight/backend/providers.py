"""LLM providers for the Agent Lab tool-use loop.

Resolution order:
1. ``LLM_PROVIDER`` env if set (groq | ollama | anthropic)
2. Else Groq when ``GROQ_API_KEY`` is set
3. Else Ollama (local, free)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger("nyc_tonight.providers")

GROQ_BASE = "https://api.groq.com/openai/v1"
OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
DEFAULT_ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = int(os.getenv("ANTHROPIC_MAX_TOKENS", os.getenv("LLM_MAX_TOKENS", "1200")))
HTTP_TIMEOUT = 60.0


@dataclass
class ProviderInfo:
    name: str
    model: str
    configured: bool
    detail: str = ""


def _env_key(name: str) -> str:
    return (os.getenv(name) or "").strip()


def resolve_provider_name() -> str:
    explicit = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    if explicit in ("groq", "ollama", "anthropic"):
        return explicit
    if _env_key("GROQ_API_KEY"):
        return "groq"
    return "ollama"


def provider_info() -> ProviderInfo:
    name = resolve_provider_name()
    if name == "groq":
        key = bool(_env_key("GROQ_API_KEY"))
        return ProviderInfo(
            name="groq",
            model=DEFAULT_GROQ_MODEL,
            configured=key,
            detail="missing GROQ_API_KEY" if not key else "ok",
        )
    if name == "anthropic":
        key = bool(_env_key("ANTHROPIC_API_KEY"))
        return ProviderInfo(
            name="anthropic",
            model=DEFAULT_ANTHROPIC_MODEL,
            configured=key,
            detail="missing ANTHROPIC_API_KEY" if not key else "ok",
        )
    # ollama — probe later in health; configured means base URL assumed
    return ProviderInfo(
        name="ollama",
        model=DEFAULT_OLLAMA_MODEL,
        configured=True,
        detail=OLLAMA_BASE,
    )


def anthropic_tools_to_openai(tool_definitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Anthropic-style tool schemas to OpenAI function tools."""
    out = []
    for t in tool_definitions:
        out.append(
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description") or "",
                    "parameters": t.get("input_schema") or {"type": "object", "properties": {}},
                },
            }
        )
    return out


def complete_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    system: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> dict[str, Any]:
    """One chat completion against an OpenAI-compatible API.

    Returns a normalized dict:
      { role, content, tool_calls: [{id, name, arguments}], stop_reason }
    where stop_reason is 'tool_use' or 'end_turn'.
    """
    api_messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    api_messages.extend(messages)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    body: dict[str, Any] = {
        "model": model,
        "messages": api_messages,
        "max_tokens": MAX_TOKENS,
        "temperature": 0.3,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    resp = httpx.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json=body,
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    finish = choice.get("finish_reason") or "stop"

    tool_calls_raw = message.get("tool_calls") or []
    tool_calls = []
    for tc in tool_calls_raw:
        fn = tc.get("function") or {}
        args = fn.get("arguments") or "{}"
        if isinstance(args, str):
            try:
                args_obj = json.loads(args) if args.strip() else {}
            except json.JSONDecodeError:
                args_obj = {"_raw": args}
        else:
            args_obj = args
        tool_calls.append(
            {
                "id": tc.get("id") or f"call_{len(tool_calls)}",
                "name": fn.get("name") or "",
                "arguments": args_obj,
            }
        )

    stop_reason = "tool_use" if tool_calls or finish == "tool_calls" else "end_turn"
    return {
        "role": "assistant",
        "content": message.get("content") or "",
        "tool_calls": tool_calls,
        "stop_reason": stop_reason,
        "raw_assistant_message": message,
    }


def complete_anthropic(
    *,
    system: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> dict[str, Any]:
    """Anthropic Messages API — kept as optional provider."""
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=DEFAULT_ANTHROPIC_MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        tools=tools,
        messages=messages,
    )
    text_parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    tool_calls = []
    for b in response.content:
        if getattr(b, "type", None) == "tool_use":
            tool_calls.append(
                {
                    "id": b.id,
                    "name": b.name,
                    "arguments": b.input or {},
                }
            )
    stop = "tool_use" if response.stop_reason == "tool_use" else "end_turn"
    return {
        "role": "assistant",
        "content": "\n".join(text_parts).strip(),
        "tool_calls": tool_calls,
        "stop_reason": stop,
        "raw_assistant_message": response.content,
        "anthropic": True,
    }


def complete(
    *,
    system: str,
    messages: list[dict[str, Any]],
    tool_definitions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Dispatch to the resolved provider. ``messages`` use OpenAI-style roles."""
    name = resolve_provider_name()
    openai_tools = anthropic_tools_to_openai(tool_definitions)

    if name == "groq":
        key = _env_key("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY is not set")
        return complete_openai_compatible(
            base_url=GROQ_BASE,
            api_key=key,
            model=DEFAULT_GROQ_MODEL,
            system=system,
            messages=messages,
            tools=openai_tools,
        )

    if name == "anthropic":
        # Anthropic expects its own message format with content blocks.
        # Convert OpenAI-style history when possible.
        return _complete_anthropic_from_openai_messages(
            system=system,
            messages=messages,
            tool_definitions=tool_definitions,
        )

    # ollama
    return complete_openai_compatible(
        base_url=OLLAMA_BASE,
        api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
        model=DEFAULT_OLLAMA_MODEL,
        system=system,
        messages=messages,
        tools=openai_tools,
    )


def _complete_anthropic_from_openai_messages(
    *,
    system: str,
    messages: list[dict[str, Any]],
    tool_definitions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Best-effort bridge: OpenAI-style messages → Anthropic messages."""
    anthro_messages: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role == "assistant":
            content: list[Any] = []
            if m.get("content"):
                content.append({"type": "text", "text": m["content"]})
            for tc in m.get("tool_calls") or []:
                content.append(
                    {
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc.get("arguments") or {},
                    }
                )
            if content:
                anthro_messages.append({"role": "assistant", "content": content})
        elif role == "tool":
            # Fold into a user tool_result turn (merge consecutive)
            block = {
                "type": "tool_result",
                "tool_use_id": m.get("tool_call_id"),
                "content": m.get("content") or "",
            }
            if anthro_messages and anthro_messages[-1]["role"] == "user" and isinstance(
                anthro_messages[-1]["content"], list
            ):
                anthro_messages[-1]["content"].append(block)
            else:
                anthro_messages.append({"role": "user", "content": [block]})
        elif role == "user":
            anthro_messages.append({"role": "user", "content": m.get("content") or ""})

    return complete_anthropic(
        system=system, messages=anthro_messages, tools=tool_definitions
    )


def ollama_reachable() -> bool:
    try:
        # Ollama native health is at / without /v1
        base = OLLAMA_BASE.replace("/v1", "")
        r = httpx.get(base, timeout=2.0)
        return r.status_code < 500
    except Exception:  # noqa: BLE001
        return False
