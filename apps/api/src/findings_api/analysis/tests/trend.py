from __future__ import annotations

import math

import pandas as pd
from scipy import stats

from findings_api.analysis.labels import column_label
from findings_api.analysis.profile import read_table_frame, sql_ident
from findings_api.analysis.types import Finding

_MAX_P = 0.05


def _score(slope: float, p_value: float | None) -> float:
    if p_value is None or p_value <= 0:
        return abs(slope)
    return abs(slope) * min(20.0, -math.log10(p_value))


def run_trend(
    conn,
    table: str,
    value_col: str,
    time_col: str,
    *,
    resource_id: str,
    dataset_title: str,
    finding_offset: int,
) -> list[Finding]:
    df = read_table_frame(conn, table)
    if value_col not in df.columns or time_col not in df.columns:
        return []
    work = df[[value_col, time_col]].dropna()
    if len(work) < 12:
        return []

    if not pd.api.types.is_datetime64_any_dtype(work[time_col]):
        work[time_col] = pd.to_datetime(work[time_col], errors="coerce", utc=True)
    work = work.dropna()
    if len(work) < 12:
        return []

    x = work[time_col].astype("int64") / 1e9
    y = pd.to_numeric(work[value_col], errors="coerce")
    work = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(work) < 12 or work["y"].nunique() < 2:
        return []

    slope, _, r, p, _ = stats.linregress(work["x"], work["y"])
    if pd.isna(p) or float(p) >= _MAX_P:
        return []

    idx = finding_offset + 1
    direction = "upward" if slope > 0 else "downward"
    return [
        Finding(
            id=f"f_{idx}",
            type="time_trend",
            title=f"{column_label(value_col)} shows an {direction} trend over time",
            columns=[value_col, time_col],
            value=round(float(r), 4),
            p_value=round(float(p), 6),
            n=len(work),
            method="linear_trend",
            caveat="trends may reflect seasonality or missing confounders",
            sql=(
                f"SELECT {sql_ident(time_col)}, {sql_ident(value_col)} FROM {table} "
                f"WHERE {sql_ident(value_col)} IS NOT NULL ORDER BY 1"
            ),
            datasets=[resource_id],
            score=_score(float(slope), float(p)),
            details={"dataset_title": dataset_title, "direction": direction},
        )
    ]
