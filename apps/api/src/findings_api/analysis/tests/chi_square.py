from __future__ import annotations

import math

import pandas as pd
from scipy.stats import chi2_contingency

from findings_api.analysis.labels import column_label
from findings_api.analysis.profile import read_table_frame, sql_ident
from findings_api.analysis.types import Finding

_MAX_P = 0.05
_MIN_CELL = 5


def _score(cramers_v: float, p_value: float | None) -> float:
    if p_value is None or p_value <= 0:
        return cramers_v
    return cramers_v * min(20.0, -math.log10(p_value))


def run_chi_square(
    conn,
    table: str,
    col_a: str,
    col_b: str,
    *,
    resource_id: str,
    dataset_title: str,
    finding_offset: int,
) -> list[Finding]:
    df = read_table_frame(conn, table)
    if col_a not in df.columns or col_b not in df.columns:
        return []
    work = df[[col_a, col_b]].dropna()
    if len(work) < 20:
        return []
    if work[col_a].nunique() > 20 or work[col_b].nunique() > 20:
        return []

    table_df = pd.crosstab(work[col_a], work[col_b])
    if table_df.size == 0 or table_df.min().min() < _MIN_CELL:
        return []

    chi2, p, _, _ = chi2_contingency(table_df)
    if pd.isna(p) or float(p) >= _MAX_P:
        return []

    n = len(work)
    r, k = table_df.shape
    cramers = math.sqrt(chi2 / (n * min(r - 1, k - 1))) if n and min(r, k) > 1 else 0.0
    idx = finding_offset + 1
    return [
        Finding(
            id=f"f_{idx}",
            type="chi_square",
            title=f"{column_label(col_a)} and {column_label(col_b)} appear linked",
            columns=[col_a, col_b],
            value=round(float(cramers), 4),
            p_value=round(float(p), 6),
            n=n,
            method="chi_square",
            caveat="association in categories does not imply causation",
            sql=(
                f"SELECT {sql_ident(col_a)}, {sql_ident(col_b)}, COUNT(*) AS n "
                f"FROM {table} GROUP BY 1, 2 ORDER BY 3 DESC"
            ),
            datasets=[resource_id],
            score=_score(float(cramers), float(p)),
            details={"dataset_title": dataset_title},
        )
    ]
