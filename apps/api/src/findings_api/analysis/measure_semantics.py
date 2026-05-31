"""Resolve what generic measure columns (e.g. `value`) actually represent."""

from __future__ import annotations

import json
import logging
import re

import pandas as pd

from findings_api.analysis.profile import read_table_frame
from findings_api.config import settings

logger = logging.getLogger(__name__)

MEASURE_COLUMN_NAMES = frozenset({"value", "val", "amount", "obs_value"})
_INDICATOR_COLUMNS = ("indicator", "indicator_name", "series", "series_title", "variable")
_INDICATOR_ID_COLUMNS = ("indicator_id", "series_id", "variable_code")
_UNIT_COLUMNS = ("unit", "units", "unit_of_measure", "uom")
_TRUSTED_SOURCES = frozenset({"indicator_column"})


def measure_slug(label: str, *, fallback: str, used: set[str]) -> str:
    """Build a unique, SQL-safe column name from a measure label.

    e.g. "Population living in slums (% of urban population)" ->
    "population_living_in_slums". Guarantees a valid identifier that does not
    collide with names already in ``used``.
    """
    base = re.sub(r"[^a-z0-9]+", "_", (label or "").lower()).strip("_")
    base = re.sub(r"_+", "_", base)[:48].strip("_")
    if not base or base[0].isdigit():
        base = f"measure_{base}".strip("_")
    if not base:
        base = fallback
    candidate = base
    n = 2
    while candidate in used:
        candidate = f"{base}_{n}"
        n += 1
    used.add(candidate)
    return candidate


def _constant_string(series: pd.Series) -> str | None:
    non_null = series.dropna()
    if len(non_null) == 0:
        return None
    as_str = non_null.astype(str).str.strip()
    as_str = as_str[as_str != ""]
    if len(as_str) == 0:
        return None
    if as_str.nunique() == 1:
        return str(as_str.iloc[0])
    return None


def _first_constant(df: pd.DataFrame, names: tuple[str, ...]) -> str | None:
    for name in names:
        if name in df.columns:
            found = _constant_string(df[name])
            if found:
                return found
    return None


def format_measure_disclosure(measure_context: dict[str, str | None]) -> str:
    """Human-readable note when a generic column name was interpreted."""
    column = measure_context.get("column") or "value"
    label = measure_context.get("label") or ""
    source = measure_context.get("source") or ""
    if source == "ai_inferred":
        return f'The field `{column}` — AI determined this represents: {label}'
    if source == "indicator_column":
        return f'The field `{column}` holds values for: {label} (from indicator metadata in the dataset)'
    if source == "catalog_title":
        return f'The field `{column}` is interpreted as: {label} (from catalog title)'
    return f'The field `{column}` is interpreted as: {label}'


def measure_analysis_note(measure_context: dict[str, str | None] | None) -> str | None:
    if not measure_context or not measure_context.get("label"):
        return None
    return measure_context.get("disclosure") or format_measure_disclosure(measure_context)


def append_measure_note(
    caveat: str,
    measure_context: dict[str, str | None] | None,
) -> str:
    note = measure_analysis_note(measure_context)
    if not note:
        return caveat
    if caveat.strip():
        return f"{caveat.strip()} {note}"
    return note


def _sample_rows_for_prompt(df: pd.DataFrame, *, limit: int = 4) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    sample = df.head(limit)
    for _, row in sample.iterrows():
        clean: dict[str, object] = {}
        for key, value in row.items():
            if pd.isna(value):
                clean[str(key)] = None
            elif isinstance(value, pd.Timestamp):
                clean[str(key)] = value.isoformat()
            elif hasattr(value, "item"):
                clean[str(key)] = value.item()
            else:
                clean[str(key)] = value
        rows.append(clean)
    return rows


def _metadata_hints(df: pd.DataFrame) -> dict[str, str]:
    hints: dict[str, str] = {}
    for name in _INDICATOR_COLUMNS + _INDICATOR_ID_COLUMNS + _UNIT_COLUMNS:
        if name in df.columns:
            val = _constant_string(df[name])
            if val:
                hints[name] = val
    return hints


def _parse_ai_measure_response(text: str) -> dict[str, str] | None:
    text = text.strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[^{}]*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    if not isinstance(payload, dict):
        return None
    label = str(payload.get("label") or "").strip()
    if not label or len(label) > 200:
        return None
    unit = str(payload.get("unit") or "").strip()
    out: dict[str, str] = {"label": label}
    if unit:
        out["unit"] = unit[:80]
    return out


def infer_measure_label_with_ai(
    *,
    column: str,
    catalog_title: str,
    column_names: list[str],
    sample_rows: list[dict[str, object]],
    metadata_hints: dict[str, str],
    metadata_label: str = "",
) -> dict[str, str] | None:
    """Call Anthropic to name what a generic measure column represents."""
    if not settings.anthropic_api_key:
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        prompt = f"""You label generic numeric columns in open-data tables for a statistics app.

The column to interpret is named `{column}` (often a placeholder like "value" from an API).

Dataset catalog title: {catalog_title or "Unknown"}
Other columns: {", ".join(column_names)}
Constant metadata fields: {json.dumps(metadata_hints, ensure_ascii=False)}
Existing metadata label (may be incomplete): {metadata_label or "none"}
Sample rows:
{json.dumps(sample_rows, ensure_ascii=False, default=str)}

Return ONLY JSON with keys:
- "label": short human name for what `{column}` measures (e.g. "Access to clean fuels (% of population)")
- "unit": optional unit string if clear (e.g. "percent", "USD", "people")

Do not invent numbers. Use catalog title and constant indicator/series fields when present."""

        response = client.messages.create(
            model=settings.anthropic_model_measure,
            max_tokens=180,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return _parse_ai_measure_response(text)
    except Exception:
        logger.exception("AI measure label inference failed for column %s", column)
        return None


def _finalize_context(result: dict[str, str | None]) -> dict[str, str | None]:
    result["disclosure"] = format_measure_disclosure(result)
    if result.get("source") == "ai_inferred":
        result["ai_inferred"] = "true"
    else:
        result["ai_inferred"] = "false"
    return result


def resolve_measure_label(
    conn,
    table: str,
    column: str,
    *,
    catalog_title: str = "",
    use_ai: bool = True,
) -> dict[str, str | None]:
    """
    Infer a human label for a measure column.

    Priority:
    1. Constant in-table indicator name (World Bank `indicator`, FRED series title)
    2. AI inference (for generic `value` columns when no trusted indicator metadata)
    3. Catalog dataset title
    4. Constant indicator id / series id
    """
    col = column.lower()
    result: dict[str, str | None] = {
        "column": column,
        "label": catalog_title or column,
        "description": None,
        "source": "catalog_title" if catalog_title else "column_name",
        "unit": None,
        "ai_inferred": "false",
        "disclosure": "",
    }

    if col not in MEASURE_COLUMN_NAMES and col not in ("amount",):
        result["label"] = column
        result["source"] = "column_name"
        return _finalize_context(result)

    try:
        df = read_table_frame(conn, table)
    except Exception:
        if catalog_title:
            result["label"] = catalog_title
        return _finalize_context(result)

    indicator = _first_constant(df, _INDICATOR_COLUMNS)
    if indicator:
        result["label"] = indicator
        result["source"] = "indicator_column"
        result["description"] = f"Measured indicator: {indicator}"
    elif catalog_title:
        result["label"] = catalog_title
        result["source"] = "catalog_title"
    else:
        indicator_id = _first_constant(df, _INDICATOR_ID_COLUMNS)
        if indicator_id:
            result["label"] = indicator_id
            result["source"] = "indicator_id_column"

    unit = _first_constant(df, _UNIT_COLUMNS)
    if unit:
        result["unit"] = unit

    should_ai = (
        use_ai
        and result.get("source") not in _TRUSTED_SOURCES
    )
    if should_ai:
        ai = infer_measure_label_with_ai(
            column=column,
            catalog_title=catalog_title,
            column_names=[str(c) for c in df.columns],
            sample_rows=_sample_rows_for_prompt(df),
            metadata_hints=_metadata_hints(df),
            metadata_label=str(result.get("label") or ""),
        )
        if ai:
            result["label"] = ai["label"]
            result["source"] = "ai_inferred"
            if ai.get("unit"):
                result["unit"] = ai["unit"]
            result["description"] = format_measure_disclosure(result)

    if result.get("unit") and result.get("description") and str(result["unit"]) not in str(result["description"]):
        if result["source"] == "indicator_column":
            result["description"] = f'{result["description"]} ({result["unit"]})'
    elif result.get("unit") and not result.get("description"):
        result["description"] = f'Unit: {result["unit"]}'

    return _finalize_context(result)


def measure_label_from_context(
    column: str,
    *,
    catalog_title: str = "",
    measure_context: dict[str, str | None] | None = None,
) -> str:
    """Format a chart/finding axis label for a measure column."""
    if measure_context and measure_context.get("label"):
        label = str(measure_context["label"])
        unit = measure_context.get("unit")
        if unit and unit not in label:
            return f"{label} ({unit})"
        return label
    if column.lower() in MEASURE_COLUMN_NAMES and catalog_title:
        return catalog_title
    from findings_api.analysis.labels import column_label

    return column_label(column)
