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


def _column_list(names: list[str], *, limit: int = 4) -> str:
    if not names:
        return ""
    shown = names[:limit]
    text = ", ".join(shown)
    if len(names) > limit:
        text += f", +{len(names) - limit} more"
    return text


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


def analysis_notes(
    profiles: list[TableProfile],
    *,
    tests_planned: int,
    statistical_hits: int,
    total_findings: int,
) -> list[str]:
    """Factual coverage notes for the analysis report (not dataset recommendations)."""
    notes: list[str] = []

    if tests_planned > 0:
        notes.append(
            f"Planned {tests_planned} statistical test(s) on the loaded sample "
            f"({statistical_hits} significant at p < 0.05, {total_findings} total ranked result(s))."
        )
    elif total_findings > 0:
        notes.append(f"Produced {total_findings} descriptive summary result(s) from the loaded sample.")

    for profile in profiles:
        parts: list[str] = []
        if profile.numeric:
            parts.append(f"numeric: {_column_list(profile.numeric)}")
        if profile.categorical:
            parts.append(f"categories: {_column_list(profile.categorical)}")
        if profile.datetime:
            parts.append(f"dates: {_column_list(profile.datetime)}")

        field_summary = "; ".join(parts) if parts else "no typed columns detected"
        notes.append(f"{profile.title} — {profile.n_rows:,} rows analyzed ({field_summary}).")

        if profile.n_rows < 20:
            notes.append(f"{profile.title} — small sample ({profile.n_rows} rows); many tests need more data.")

        has_date = bool(profile.datetime) or any(
            c.name.lower() in ("date", "year") for c in profile.columns
        )
        if len(profile.numeric) == 1 and has_date:
            notes.append(
                f"{profile.title} — time-series shape (date + numeric value); "
                "trend tests ran, correlation skipped (needs 2+ numeric fields)."
            )
        elif len(profile.numeric) < 2:
            notes.append(
                f"{profile.title} — only {len(profile.numeric)} numeric field(s); "
                "correlation/regression tests were not applicable."
            )

    return notes[:6]
