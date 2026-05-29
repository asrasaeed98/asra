from __future__ import annotations

import math

import pandas as pd
from scipy import stats

from findings_api.analysis.labels import build_column_labels, measure_label
from findings_api.analysis.measure_semantics import append_measure_note, format_measure_disclosure
from findings_api.analysis.profile import read_table_frame, sql_ident
from findings_api.analysis.types import Finding

_MAX_P = 0.05


def _score(slope: float, p_value: float | None) -> float:
    if p_value is None or p_value <= 0:
        return abs(slope)
    return abs(slope) * min(20.0, -math.log10(p_value))


def _aggregate_by_time(work: pd.DataFrame, value_col: str, time_col: str) -> pd.DataFrame:
    """Collapse panel rows to one value per timestamp (global average)."""
    if work[time_col].nunique() >= len(work) * 0.9:
        return work
    grouped = (
        work.groupby(time_col, observed=True)[value_col]
        .mean()
        .reset_index()
        .rename(columns={value_col: value_col})
    )
    return grouped[[time_col, value_col]]


def run_trend(
    conn,
    table: str,
    value_col: str,
    time_col: str,
    *,
    resource_id: str,
    dataset_title: str,
    finding_offset: int,
    aggregate_by_time: bool = False,
    measure_context: dict[str, str | None] | None = None,
    measure_contexts: dict[str, dict[str, str | None]] | None = None,
) -> list[Finding]:
    df = read_table_frame(conn, table)
    if value_col not in df.columns or time_col not in df.columns:
        return []
    if measure_context is None and measure_contexts:
        measure_context = measure_contexts.get(value_col)
    work = df[[value_col, time_col]].dropna()
    if len(work) < 12:
        return []

    if not pd.api.types.is_datetime64_any_dtype(work[time_col]):
        work[time_col] = pd.to_datetime(work[time_col], errors="coerce", utc=True)
    work = work.dropna()
    if len(work) < 12:
        return []

    if aggregate_by_time or work[time_col].nunique() < len(work):
        work = _aggregate_by_time(work, value_col, time_col)
        aggregated = True
    else:
        aggregated = False
    if len(work) < 8:
        return []

    x = work[time_col].astype("int64") / 1e9
    y = pd.to_numeric(work[value_col], errors="coerce")
    work = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(work) < 8 or work["y"].nunique() < 2:
        return []

    slope, _, r, p, _ = stats.linregress(work["x"], work["y"])
    if pd.isna(p) or float(p) >= _MAX_P:
        return []

    idx = finding_offset + 1
    direction = "upward" if slope > 0 else "downward"
    measure = measure_label(value_col, dataset_title=dataset_title, measure_context=measure_context)
    column_labels = build_column_labels(
        [value_col, time_col],
        dataset_title=dataset_title,
        measure_contexts=measure_contexts or ({value_col: measure_context} if measure_context else None),
    )
    agg_sql = (
        f"SELECT {sql_ident(time_col)}, AVG({sql_ident(value_col)}) AS {sql_ident(value_col)} "
        f"FROM {table} WHERE {sql_ident(value_col)} IS NOT NULL "
        f"GROUP BY 1 ORDER BY 1"
    )
    raw_sql = (
        f"SELECT {sql_ident(time_col)}, {sql_ident(value_col)} FROM {table} "
        f"WHERE {sql_ident(value_col)} IS NOT NULL ORDER BY 1"
    )
    return [
        Finding(
            id=f"f_{idx}",
            type="time_trend",
            title=f"{measure} shows an {direction} trend over time",
            columns=[value_col, time_col],
            value=round(float(r), 4),
            p_value=round(float(p), 6),
            n=len(work),
            method="linear_trend",
            caveat=append_measure_note(
                "trend uses global average by year across countries when data is panel-shaped",
                measure_context,
            ),
            sql=agg_sql if aggregated else raw_sql,
            datasets=[resource_id],
            score=_score(float(slope), float(p)),
            details={
                "dataset_title": dataset_title,
                "direction": direction,
                "aggregated": aggregated,
                "measure_context": measure_context,
                "measure_disclosure": (
                    format_measure_disclosure(measure_context)
                    if measure_context
                    else None
                ),
                "column_labels": column_labels,
            },
        )
    ]
