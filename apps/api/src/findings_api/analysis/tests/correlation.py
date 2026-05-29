from __future__ import annotations

import itertools
import math

import pandas as pd
from scipy import stats

from findings_api.analysis.labels import build_column_labels, label_from_details
from findings_api.analysis.profile import read_table_frame, sql_ident
from findings_api.analysis.types import Finding

_MIN_R = 0.3
_MAX_P = 0.05


def _score(effect: float, p_value: float | None) -> float:
    if p_value is None or p_value <= 0:
        return abs(effect)
    return abs(effect) * min(20.0, -math.log10(p_value))


def run_correlation(
    conn,
    table: str,
    columns: list[str],
    *,
    resource_id: str,
    dataset_title: str,
    finding_offset: int,
    measure_contexts: dict[str, dict[str, str | None]] | None = None,
) -> list[Finding]:
    df = read_table_frame(conn, table)
    column_labels = build_column_labels(
        list(columns), dataset_title=dataset_title, measure_contexts=measure_contexts
    )
    findings: list[Finding] = []
    idx = finding_offset
    for a, b in itertools.combinations(columns, 2):
        if a not in df.columns or b not in df.columns:
            continue
        pair = df[[a, b]].dropna()
        if len(pair) < 8:
            continue
        r, p = stats.spearmanr(pair[a], pair[b])
        if pd.isna(r) or pd.isna(p):
            continue
        if abs(float(r)) < _MIN_R or float(p) >= _MAX_P:
            continue
        idx += 1
        direction = "positive" if r > 0 else "negative"
        pair_labels = {c: column_labels[c] for c in (a, b) if c in column_labels}
        label_a = label_from_details({"column_labels": column_labels}, a)
        label_b = label_from_details({"column_labels": column_labels}, b)
        findings.append(
            Finding(
                id=f"f_{idx}",
                type="spearman_correlation",
                title=(
                    f"{label_a} and {label_b} "
                    f"{'move in opposite directions' if r < 0 else 'tend to move together'}"
                ),
                columns=[a, b],
                value=round(float(r), 4),
                p_value=round(float(p), 6),
                n=len(pair),
                method="spearman",
                caveat="correlation is not causation",
                sql=(
                    f"SELECT {sql_ident(a)}, {sql_ident(b)} FROM {table} "
                    f"WHERE {sql_ident(a)} IS NOT NULL AND {sql_ident(b)} IS NOT NULL"
                ),
                datasets=[resource_id],
                score=_score(float(r), float(p)),
                details={
                    "dataset_title": dataset_title,
                    "direction": direction,
                    "column_labels": pair_labels,
                },
            )
        )
    findings.sort(key=lambda x: x.score, reverse=True)
    return findings[:6]
