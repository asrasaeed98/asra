from __future__ import annotations

import math

import pandas as pd
from scipy import stats

from findings_api.analysis.labels import build_column_labels, column_label, measure_label
from findings_api.analysis.measure_semantics import append_measure_note, format_measure_disclosure
from findings_api.analysis.profile import read_table_frame, sql_ident
from findings_api.analysis.types import Finding

_MAX_GROUPS = 12
_MIN_GROUP_SIZE = 3
_MAX_P = 0.05


def _score(effect: float, p_value: float | None) -> float:
    if p_value is None or p_value <= 0:
        return abs(effect)
    return abs(effect) * min(20.0, -math.log10(p_value))


def run_group_comparison(
    conn,
    table: str,
    numeric_col: str,
    group_col: str,
    *,
    resource_id: str,
    dataset_title: str,
    finding_offset: int,
    measure_context: dict[str, str | None] | None = None,
    measure_contexts: dict[str, dict[str, str | None]] | None = None,
) -> list[Finding]:
    df = read_table_frame(conn, table)
    if numeric_col not in df.columns or group_col not in df.columns:
        return []
    if measure_context is None and measure_contexts:
        measure_context = measure_contexts.get(numeric_col)
    work = df[[numeric_col, group_col]].dropna()
    if len(work) < 12:
        return []

    groups = []
    labels = []
    group_sizes = work.groupby(group_col, observed=True).size().sort_values(ascending=False)
    if len(group_sizes) > _MAX_GROUPS:
        keep = set(group_sizes.head(_MAX_GROUPS).index)
        work = work[work[group_col].isin(keep)]

    for label, chunk in work.groupby(group_col, observed=True):
        if len(chunk) < _MIN_GROUP_SIZE:
            continue
        groups.append(chunk[numeric_col].astype(float).tolist())
        labels.append(str(label))
    if len(groups) < 2 or len(groups) > _MAX_GROUPS:
        return []

    if len(groups) == 2:
        stat, p = stats.ttest_ind(groups[0], groups[1], equal_var=False)
        method = "welch_t"
        means = {labels[i]: float(pd.Series(groups[i]).mean()) for i in range(len(labels))}
        effect = abs(means[labels[0]] - means[labels[1]])
    else:
        stat, p = stats.kruskal(*groups)
        method = "kruskal"
        means = {labels[i]: float(pd.Series(groups[i]).mean()) for i in range(len(labels))}
        spread = max(means.values()) - min(means.values()) if means else 0.0
        effect = spread

    if pd.isna(p) or float(p) >= _MAX_P:
        return []

    idx = finding_offset + 1
    top = max(means, key=means.get)
    bottom = min(means, key=means.get)
    column_labels = build_column_labels(
        [numeric_col, group_col],
        dataset_title=dataset_title,
        measure_contexts=measure_contexts or ({numeric_col: measure_context} if measure_context else None),
    )
    return [
        Finding(
            id=f"f_{idx}",
            type="group_comparison",
            title=f"{measure_label(numeric_col, dataset_title=dataset_title, measure_context=measure_context)} differs across {column_label(group_col)}",
            columns=[numeric_col, group_col],
            value=round(float(effect), 4),
            p_value=round(float(p), 6),
            n=len(work),
            method=method,
            caveat=append_measure_note(
                "group differences may reflect confounding",
                measure_context,
            ),
            sql=(
                f"SELECT {sql_ident(group_col)}, AVG({sql_ident(numeric_col)}) AS mean_value "
                f"FROM {table} GROUP BY 1 ORDER BY 2 DESC"
            ),
            datasets=[resource_id],
            score=_score(float(effect), float(p)),
            details={
                "dataset_title": dataset_title,
                "measure_context": measure_context,
                "measure_disclosure": (
                    format_measure_disclosure(measure_context)
                    if measure_context
                    else None
                ),
                "column_labels": column_labels,
                "group_means": means,
                "highest_group": top,
                "lowest_group": bottom,
            },
        )
    ]
