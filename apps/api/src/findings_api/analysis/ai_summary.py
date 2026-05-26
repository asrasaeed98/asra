"""Grounded executive summary from top findings (Anthropic + validation)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from findings_api.config import settings

logger = logging.getLogger(__name__)

_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9_])"  # not part of an identifier
    r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d+)"
    r"(?![A-Za-z0-9_])"
)


def _collect_allowed_numbers(findings: list[dict[str, Any]]) -> set[float]:
    allowed: set[float] = set()

    def walk(obj: Any) -> None:
        if obj is None:
            return
        if isinstance(obj, bool):
            return
        if isinstance(obj, (int, float)):
            allowed.add(float(obj))
            return
        if isinstance(obj, str):
            for match in _NUMBER_RE.finditer(obj):
                allowed.add(float(match.group(1).replace(",", "")))
            return
        if isinstance(obj, dict):
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)

    for finding in findings:
        walk(finding)
    # Common small counts the model may use when referring to finding count.
    allowed.update({float(i) for i in range(1, 11)})
    return allowed


def _numbers_in_text(text: str) -> list[float]:
    found: list[float] = []
    for match in _NUMBER_RE.finditer(text):
        try:
            found.append(float(match.group(1).replace(",", "")))
        except ValueError:
            continue
    return found


def _number_allowed(value: float, allowed: set[float]) -> bool:
    for candidate in allowed:
        if candidate == value:
            return True
        scale = max(abs(candidate), abs(value), 1.0)
        if abs(candidate - value) <= 0.01 * scale:
            return True
        # Whole-number display (120000 vs 120,000 already normalized)
        if abs(round(candidate) - value) < 0.5 and abs(round(candidate) - candidate) < 0.01:
            if abs(round(candidate) - value) < 0.5:
                return True
    return False


def validate_summary_numbers(
    summary: str,
    findings: list[dict[str, Any]],
    *,
    context_text: str = "",
) -> bool:
    """Reject summaries that introduce digits not present in finding JSON or context."""
    allowed = _collect_allowed_numbers(findings)
    for match in _NUMBER_RE.finditer(context_text):
        try:
            allowed.add(float(match.group(1).replace(",", "")))
        except ValueError:
            continue
    for num in _numbers_in_text(summary):
        if not _number_allowed(num, allowed):
            logger.warning("AI summary rejected: number %s not in findings", num)
            return False
    return True


def _finding_payload(finding: dict[str, Any]) -> dict[str, Any]:
    details = finding.get("details") or {}
    return {
        "headline": details.get("headline") or finding.get("title"),
        "impact": details.get("impact"),
        "type": finding.get("type"),
        "n": finding.get("n"),
        "p_value": finding.get("p_value"),
        "effect": finding.get("value"),
        "caveat": finding.get("caveat"),
    }


def template_summary_blocks(
    findings: list[dict[str, Any]],
    *,
    user_intent: str | None = None,
    dataset_titles: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Structured fallback summary."""
    if not findings:
        return [
            {
                "type": "paragraph",
                "text": (
                    "We did not find statistically significant patterns in this sample. "
                    "Try a dataset with more rows and varied numeric columns, such as NEH grant CSVs on data.gov."
                ),
            }
        ]

    intro_parts: list[str] = []
    if dataset_titles:
        intro_parts.append(f"This summary covers {', '.join(dataset_titles[:2])}.")
    if user_intent:
        intro_parts.append(f"You asked about: {user_intent.strip()}")
    if not intro_parts:
        intro_parts.append("Here are the main patterns from your analysis.")

    impacts = [
        (f.get("details") or {}).get("impact") or f.get("title")
        for f in findings[:5]
        if (f.get("details") or {}).get("impact") or f.get("title")
    ]

    blocks: list[dict[str, Any]] = [{"type": "paragraph", "text": " ".join(intro_parts)}]
    if impacts:
        blocks.append({"type": "list", "items": impacts[:5]})
    blocks.append(
        {
            "type": "paragraph",
            "text": (
                "These points come directly from computed statistical tests. "
                "Correlation and group differences do not prove causation."
            ),
        }
    )
    return blocks


def template_summary(
    findings: list[dict[str, Any]],
    *,
    user_intent: str | None = None,
    dataset_titles: list[str] | None = None,
) -> str:
    """Plain-text fallback (legacy field)."""
    return blocks_to_plain_text(
        template_summary_blocks(findings, user_intent=user_intent, dataset_titles=dataset_titles)
    )


def blocks_to_plain_text(blocks: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for block in blocks:
        if block.get("type") == "paragraph" and block.get("text"):
            parts.append(str(block["text"]))
        elif block.get("type") == "list":
            items = block.get("items") or []
            parts.append("\n".join(f"• {item}" for item in items))
    return "\n\n".join(parts)


def _build_prompt(
    findings: list[dict[str, Any]],
    *,
    user_intent: str | None,
    dataset_titles: list[str],
) -> str:
    payload = {
        "datasets": dataset_titles,
        "user_intent": user_intent,
        "findings": [_finding_payload(f) for f in findings],
    }
    return f"""Write key findings for a non-technical audience based ONLY on these computed results.

Return ONLY valid JSON (no markdown fences, no commentary) in exactly this shape:
{{
  "intro": "1-2 short sentences: what dataset and the headline pattern",
  "highlights": [
    "One plain-language bullet per major finding (3 to 5 items)",
    "Each bullet is one digestible sentence",
    "Most important finding first"
  ],
  "caveat": "One sentence: correlation/group differences are not proof of causation"
}}

Rules:
- Use plain language (avoid p-value, Spearman, Kruskal unless unavoidable).
- Do NOT invent numbers — only reuse figures explicitly present in the JSON below.
- Do NOT use markdown headers or titles.
- highlights must be an array of strings, not a single paragraph.
- Do not mention SQL, tests, or machine learning.

Findings JSON:
{json.dumps(payload, indent=2)}"""


def _parse_summary_json(text: str) -> list[dict[str, Any]] | None:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None

    blocks: list[dict[str, Any]] = []
    intro = data.get("intro")
    if isinstance(intro, str) and intro.strip():
        blocks.append({"type": "paragraph", "text": intro.strip()})

    highlights = data.get("highlights")
    items: list[str] = []
    if isinstance(highlights, list):
        items = [str(h).strip() for h in highlights if str(h).strip()]
    elif isinstance(highlights, str) and highlights.strip():
        items = [line.strip() for line in highlights.split("\n") if line.strip()]
    if items:
        blocks.append({"type": "list", "items": items[:6]})

    caveat = data.get("caveat")
    if isinstance(caveat, str) and caveat.strip():
        blocks.append({"type": "paragraph", "text": caveat.strip()})

    return blocks if blocks else None


def _blocks_to_validation_text(blocks: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for block in blocks:
        if block.get("type") == "paragraph":
            parts.append(str(block.get("text") or ""))
        elif block.get("type") == "list":
            parts.extend(str(x) for x in block.get("items") or [])
    return "\n".join(parts)


def sanitize_summary_text(text: str) -> str:
    """Drop markdown headings from legacy plain-text summaries."""
    blocks = _parse_summary_json(text)
    if blocks:
        return blocks_to_plain_text(blocks)
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        if stripped.startswith("#"):
            continue
        if re.match(r"^executive summary\b", stripped, re.I):
            continue
        lines.append(line)
    collapsed = "\n".join(lines)
    parts = [p.strip() for p in re.split(r"\n\s*\n", collapsed) if p.strip()]
    return "\n\n".join(parts)


def generate_ai_summary(
    findings: list[dict[str, Any]],
    *,
    user_intent: str | None = None,
    dataset_titles: list[str] | None = None,
) -> tuple[str, str, list[dict[str, Any]]]:
    """
    Return (plain_text, source, blocks) where source is anthropic | template.
    """
    titles = dataset_titles or []
    if not findings:
        blocks = template_summary_blocks([], user_intent=user_intent, dataset_titles=titles)
        return blocks_to_plain_text(blocks), "template", blocks

    if not settings.anthropic_api_key:
        blocks = template_summary_blocks(findings, user_intent=user_intent, dataset_titles=titles)
        return blocks_to_plain_text(blocks), "template", blocks

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        prompt = _build_prompt(findings, user_intent=user_intent, dataset_titles=titles)
        response = client.messages.create(
            model=settings.anthropic_model_summary,
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        blocks = _parse_summary_json(text)
        if not blocks:
            text = sanitize_summary_text(text)
            if not text:
                raise ValueError("empty model response")
            blocks = legacy_text_to_blocks(text)
        else:
            text = blocks_to_plain_text(blocks)

        if validate_summary_numbers(
            _blocks_to_validation_text(blocks),
            findings,
            context_text=" ".join(dataset_titles) + " " + (user_intent or ""),
        ):
            return text, "anthropic", blocks
        logger.warning("AI summary failed validation; using template fallback")
    except Exception:
        logger.exception("AI summary generation failed")

    blocks = template_summary_blocks(findings, user_intent=user_intent, dataset_titles=titles)
    return blocks_to_plain_text(blocks), "template", blocks


def legacy_text_to_blocks(text: str) -> list[dict[str, Any]]:
    """Convert plain summary text into paragraph/list blocks."""
    blocks: list[dict[str, Any]] = []
    paragraph_lines: list[str] = []
    list_items: list[str] = []

    def flush_paragraph() -> None:
        joined = " ".join(paragraph_lines).strip()
        if joined:
            blocks.append({"type": "paragraph", "text": joined})
        paragraph_lines.clear()

    def flush_list() -> None:
        if list_items:
            blocks.append({"type": "list", "items": list_items.copy()})
            list_items.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            flush_list()
            flush_paragraph()
            continue
        if stripped.startswith("#"):
            continue
        if re.match(r"^executive summary\b", stripped, re.I):
            continue
        bullet = re.match(r"^[-*•]\s+(.+)", stripped)
        if bullet:
            flush_paragraph()
            list_items.append(bullet.group(1).strip())
            continue
        flush_list()
        paragraph_lines.append(stripped)

    flush_list()
    flush_paragraph()
    return blocks if blocks else [{"type": "paragraph", "text": text.strip()}]
