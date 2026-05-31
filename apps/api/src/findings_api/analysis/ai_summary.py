"""Grounded executive summary from analysis results (Anthropic + validation)."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any

from findings_api.config import settings

logger = logging.getLogger(__name__)

_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d+)"
    r"(?![A-Za-z0-9_])"
)

_SYSTEM_PROMPT = (
    "You write plain-language key findings for a public-data analysis app. "
    "Interpret cryptic column names using dataset titles, source publishers, column labels, "
    "glossaries, measure context, and sample rows. Never invent statistics."
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
        if abs(round(candidate) - value) < 0.5 and abs(round(candidate) - candidate) < 0.01:
            if abs(round(candidate) - value) < 0.5:
                return True
    return False


def _expand_allowed_numbers(allowed: set[float]) -> None:
    allowed.update(float(i) for i in range(1, 26))
    for value in list(allowed):
        if 0 < abs(value) <= 1.01:
            allowed.add(round(value * 100, 4))
            allowed.add(round(abs(value) * 100, 4))
        if abs(value) >= 1 and abs(round(value) - value) < 0.01:
            allowed.add(float(round(value)))


def _years_from_text(text: str) -> set[float]:
    return {float(match.group(1)) for match in re.finditer(r"\b(19\d{2}|20[0-3]\d)\b", text)}


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
    allowed.update(_years_from_text(context_text))
    _expand_allowed_numbers(allowed)
    for num in _numbers_in_text(summary):
        if not _number_allowed(num, allowed):
            logger.warning("AI summary rejected: number %s not in findings", num)
            return False
    return True


def _column_labels(details: dict[str, Any], columns: list[str]) -> list[str]:
    labels: list[str] = []
    for idx, col in enumerate(columns):
        if details.get("measure_context") and idx == 0 and details["measure_context"].get("label"):
            labels.append(str(details["measure_context"]["label"]))
            continue
        labels.append(col)
    return labels


def _finding_payload(finding: dict[str, Any]) -> dict[str, Any]:
    details = finding.get("details") or {}
    columns = finding.get("columns") or []
    payload: dict[str, Any] = {
        "id": finding.get("id"),
        "rank_score": finding.get("score"),
        "headline": details.get("headline") or finding.get("title"),
        "impact": details.get("impact"),
        "type": finding.get("type"),
        "method": finding.get("method"),
        "columns": columns,
        "column_labels": _column_labels(details, columns) if columns else [],
        "direction": details.get("direction"),
        "primary": details.get("primary"),
        "badge": details.get("badge"),
        "n": finding.get("n"),
        "p_value": finding.get("p_value"),
        "effect": finding.get("value"),
        "caveat": finding.get("caveat"),
        "chart_title": details.get("chart_title"),
    }
    ctx = details.get("measure_context")
    if ctx:
        payload["measure_context"] = {
            k: ctx.get(k) for k in ("label", "unit", "source", "disclosure") if ctx.get(k)
        }
    if finding.get("type") == "group_comparison" and details.get("group_means"):
        payload["group_means"] = details.get("group_means")
        payload["highest_group"] = details.get("highest_group")
        payload["lowest_group"] = details.get("lowest_group")
    return {k: v for k, v in payload.items() if v is not None}


def _summary_sort_key(finding: dict[str, Any]) -> tuple:
    details = finding.get("details") or {}
    if details.get("primary"):
        return (0, -abs(float(finding.get("value") or 0)))
    if finding.get("type") == "spearman_correlation":
        return (1, -abs(float(finding.get("value") or 0)))
    return (2, 0)


def _display_findings(context: dict[str, Any]) -> list[dict[str, Any]]:
    all_findings = context.get("all_findings") or []
    display_ids = set(context.get("display_finding_ids") or [])
    if display_ids:
        ordered = [f for f in all_findings if f.get("id") in display_ids]
        if ordered:
            return ordered
    return all_findings[:5]


def _dataset_titles(context: dict[str, Any]) -> list[str]:
    return [str(d.get("title") or "Dataset") for d in context.get("datasets") or []]


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

    ordered = sorted(findings, key=_summary_sort_key)
    primary = next((f for f in ordered if (f.get("details") or {}).get("primary")), None)

    intro_parts: list[str] = []
    if primary and primary.get("type") == "spearman_correlation":
        intro_parts.append(
            "The main result is how the two selected measures relate after joining the datasets."
        )
    elif dataset_titles:
        intro_parts.append(f"This summary covers {', '.join(dataset_titles[:2])}.")
    if user_intent:
        intro_parts.append(f"You asked about: {user_intent.strip()}")
    if not intro_parts:
        intro_parts.append("Here are the main patterns from your analysis.")

    impacts = [
        (f.get("details") or {}).get("impact") or f.get("title")
        for f in ordered[:5]
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


def _build_prompt(context: dict[str, Any]) -> str:
    user_intent = context.get("user_intent")
    intent_block = ""
    if user_intent:
        intent_block = f"""
The user asked this research question — address it directly in the intro when possible:
\"{user_intent}\"
"""

    payload = {
        "datasets": context.get("datasets") or [],
        "both_datasets_nyc_open_data": context.get("both_datasets_nyc_open_data"),
        "join": context.get("join"),
        "methods_run": context.get("methods_run") or [],
        "analysis_overview": context.get("analysis_overview") or {},
        "column_glossary": context.get("column_glossary") or [],
        "all_findings": [_finding_payload(f) for f in context.get("all_findings") or []],
        "featured_finding_ids": context.get("display_finding_ids") or [],
    }

    return f"""Write key findings for a non-technical audience based ONLY on the analysis context below.
{intent_block}
Return ONLY valid JSON (no markdown fences, no commentary) in exactly this shape:
{{
  "intro": "1-2 short sentences: what was analyzed, the headline pattern, and (if provided) how it relates to the user's question",
  "highlights": [
    "One plain-language bullet per major finding (3 to 6 items)",
    "Each bullet is one digestible sentence",
    "Lead with the strongest / featured findings; cover other important patterns when relevant"
  ],
  "caveat": "One sentence: correlation/group differences are not proof of causation"
}}

Rules:
- Use plain language. Avoid jargon like p-value, Spearman, Kruskal, chi-square unless unavoidable.
- When column names are cryptic (e.g. value, amt, yr), infer readable names from dataset titles, sources, column labels, glossary, measure_context, and sample_rows — then write using those plain names.
- If datasets were joined, mention what they were combined on and what that comparison means in plain terms.
- If both datasets are NYC Open Data, you may say so when relevant.
- Do NOT invent numbers — only reuse figures explicitly present in the JSON below.
- Do NOT use markdown headers or titles.
- highlights must be an array of strings, not a single paragraph.
- Do not mention SQL, internal test names, or machine-learning algorithm names.

Analysis context JSON:
{json.dumps(payload, indent=2, default=str)}"""


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
        blocks.append({"type": "list", "items": items[:8]})

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


_NO_DIGITS_RETRY = (
    "\n\nIMPORTANT: Do not use any digits (0-9) in your JSON values. "
    "Describe magnitudes qualitatively (e.g. \"most countries\", \"strong relationship\")."
)


def _context_validation_text(context: dict[str, Any]) -> str:
    return json.dumps(context, default=str)


def _anthropic_summary_blocks(
    client: Any,
    context: dict[str, Any],
    *,
    prompt_suffix: str = "",
    on_usage: Callable[[str, int, int], None] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    prompt = _build_prompt(context) + prompt_suffix
    response = client.messages.create(
        model=settings.anthropic_model_summary,
        max_tokens=1200,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    if on_usage is not None:
        usage = getattr(response, "usage", None)
        on_usage(
            settings.anthropic_model_summary,
            int(getattr(usage, "input_tokens", 0) or 0),
            int(getattr(usage, "output_tokens", 0) or 0),
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
    return text, blocks


def generate_ai_summary(
    context: dict[str, Any],
    *,
    allow_ai: bool = True,
    on_usage: Callable[[str, int, int], None] | None = None,
) -> tuple[str, str, list[dict[str, Any]], str | None]:
    """
    Return (plain_text, source, blocks, fallback_reason).

    ``source`` is ``anthropic`` or ``template``. ``fallback_reason`` is set when
    the template path was chosen after AI was skipped or failed.
    """
    all_findings = context.get("all_findings") or []
    display = _display_findings(context)
    titles = _dataset_titles(context)
    user_intent = context.get("user_intent")
    validation_context = _context_validation_text(context)

    if not all_findings:
        blocks = template_summary_blocks([], user_intent=user_intent, dataset_titles=titles)
        return blocks_to_plain_text(blocks), "template", blocks, None

    if not settings.anthropic_api_key:
        blocks = template_summary_blocks(display, user_intent=user_intent, dataset_titles=titles)
        return blocks_to_plain_text(blocks), "template", blocks, "no_api_key"
    if not allow_ai:
        blocks = template_summary_blocks(display, user_intent=user_intent, dataset_titles=titles)
        return blocks_to_plain_text(blocks), "template", blocks, "budget_exhausted"

    fallback_reason: str | None = "api_error"
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        for attempt, suffix in enumerate(("", _NO_DIGITS_RETRY)):
            try:
                text, blocks = _anthropic_summary_blocks(
                    client,
                    context,
                    prompt_suffix=suffix,
                    on_usage=on_usage,
                )
            except Exception:
                logger.exception("AI summary generation failed (attempt %s)", attempt + 1)
                continue

            if validate_summary_numbers(
                _blocks_to_validation_text(blocks),
                all_findings,
                context_text=validation_context,
            ):
                return text, "anthropic", blocks, None

            if attempt == 0:
                logger.warning("AI summary failed validation; retrying without digits")
                fallback_reason = "validation_failed"
            else:
                logger.warning("AI summary failed validation after retry; using template fallback")
    except Exception:
        logger.exception("AI summary generation failed")

    blocks = template_summary_blocks(display, user_intent=user_intent, dataset_titles=titles)
    return blocks_to_plain_text(blocks), "template", blocks, fallback_reason


def legacy_text_to_blocks(text: str) -> list[dict[str, Any]]:
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
