"""Fallback findings when strict statistical tests return nothing."""

from __future__ import annotations

import pandas as pd

from findings_api.analysis.labels import column_label
from findings_api.analysis.profile import read_table_frame, sql_ident
from findings_api.analysis.types import Finding, TableProfile

_ID_LIKE = ("id", "uuid", "key", "code", "iso", "fips", "zip")


def _is_metric_column(name: str, series: pd.Series) -> bool:
    low = name.lower()
    if any(token in low for token in _ID_LIKE):
        return False
    nums = pd.to_numeric(series, errors="coerce").dropna()
    if len(nums) < 8:
        return False
    return float(nums.nunique()) > 1


def descriptive_findings(
    profile: TableProfile,
    conn,
    *,
    finding_offset: int = 0,
) -> list[Finding]:
    """Summarize the dataset so results are useful even without p < 0.05 hits."""
    df = read_table_frame(conn, profile.table)
    if df.empty:
        return []

    findings: list[Finding] = []
    idx = finding_offset

    idx += 1
    findings.append(
        Finding(
            id=f"f_{idx}",
            type="descriptive",
            title=f"{profile.title}: {profile.n_rows:,} rows across {len(df.columns)} columns",
            columns=[],
            value=float(profile.n_rows),
            p_value=None,
            n=profile.n_rows,
            method="profile",
            caveat="summary of loaded data — not a significance test",
            sql=f"SELECT COUNT(*) AS n FROM {profile.table}",
            datasets=[profile.resource_id],
            score=0.5,
            details={
                "dataset_title": profile.title,
                "numeric_columns": profile.numeric,
                "categorical_columns": profile.categorical,
                "datetime_columns": profile.datetime,
            },
        )
    )

    for col in profile.numeric:
        if not _is_metric_column(col, df[col]):
            continue
        nums = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(nums) < 8:
            continue
        idx += 1
        findings.append(
            Finding(
                id=f"f_{idx}",
                type="descriptive",
                title=f"{column_label(col)}: typical value {float(nums.median()):,.2f}",
                columns=[col],
                value=round(float(nums.median()), 4),
                p_value=None,
                n=len(nums),
                method="summary_stats",
                caveat="descriptive statistics only",
                sql=(
                    f"SELECT MIN({sql_ident(col)}) AS min_val, MAX({sql_ident(col)}) AS max_val, "
                    f"AVG({sql_ident(col)}) AS mean_val, MEDIAN({sql_ident(col)}) AS median_val "
                    f"FROM {profile.table} WHERE {sql_ident(col)} IS NOT NULL"
                ),
                datasets=[profile.resource_id],
                score=0.4,
                details={
                    "dataset_title": profile.title,
                    "min": float(nums.min()),
                    "max": float(nums.max()),
                    "mean": float(nums.mean()),
                    "median": float(nums.median()),
                },
            )
        )
        break

    for col in profile.categorical[:2]:
        counts = df[col].astype(str).value_counts().head(5)
        if counts.empty:
            continue
        top = counts.index[0]
        idx += 1
        findings.append(
            Finding(
                id=f"f_{idx}",
                type="descriptive",
                title=f"Top {col}: {top} ({int(counts.iloc[0]):,} rows, {profile.n_rows:,} total)",
                columns=[col],
                value=float(counts.iloc[0]),
                p_value=None,
                n=profile.n_rows,
                method="value_counts",
                caveat="descriptive counts only",
                sql=(
                    f"SELECT {sql_ident(col)}, COUNT(*) AS n FROM {profile.table} "
                    f"GROUP BY 1 ORDER BY 2 DESC LIMIT 5"
                ),
                datasets=[profile.resource_id],
                score=0.35,
                details={
                    "dataset_title": profile.title,
                    "top_values": {str(k): int(v) for k, v in counts.items()},
                },
            )
        )
        break

    return findings[:4]


def analysis_notes(profiles: list[TableProfile], *, tests_planned: int, statistical: int) -> list[str]:
    notes: list[str] = []
    if statistical == 0 and tests_planned > 0:
        notes.append(
            f"Ran {tests_planned} statistical test plan(s); none met significance thresholds (p < 0.05)."
        )
    for profile in profiles:
        if profile.n_rows < 20:
            notes.append(f"{profile.title}: only {profile.n_rows} rows — most tests need more data.")
        if len(profile.numeric) < 2:
            notes.append(
                f"{profile.title}: found {len(profile.numeric)} numeric column(s) — "
                "correlation needs at least 2."
            )
        value_cols = [c.name for c in profile.columns if c.name.lower() == "value"]
        if value_cols:
            notes.append(
                f"{profile.title}: includes a 'value' column — typical for indicator APIs; "
                "try population or GDP indicators, or a multi-column CSV from data.gov."
            )
    if not notes and statistical == 0:
        notes.append("Try a CSV dataset with several numeric columns (e.g. NEH grants).")
    return notes[:5]
