"""Fallback findings when strict statistical tests return nothing."""

from __future__ import annotations

import pandas as pd

from findings_api.analysis.labels import column_label, measure_label
from findings_api.analysis.measure_semantics import append_measure_note, format_measure_disclosure
from findings_api.analysis.profile import (
    is_panel_table,
    preferred_geo_column,
    preferred_measure_column,
    preferred_time_column,
    read_table_frame,
    sql_ident,
)
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
        col_label = measure_label(
            col,
            dataset_title=profile.title,
            measure_context=profile.measure_context(col),
        )
        ctx = profile.measure_context(col)
        findings.append(
            Finding(
                id=f"f_{idx}",
                type="descriptive",
                title=f"{col_label}: typical value {float(nums.median()):,.2f}",
                columns=[col],
                value=round(float(nums.median()), 4),
                p_value=None,
                n=len(nums),
                method="summary_stats",
                caveat=append_measure_note("descriptive statistics only", ctx),
                sql=(
                    f"SELECT MIN({sql_ident(col)}) AS min_val, MAX({sql_ident(col)}) AS max_val, "
                    f"AVG({sql_ident(col)}) AS mean_val, MEDIAN({sql_ident(col)}) AS median_val "
                    f"FROM {profile.table} WHERE {sql_ident(col)} IS NOT NULL"
                ),
                datasets=[profile.resource_id],
                score=0.4,
                details={
                    "dataset_title": profile.title,
                    "measure_context": ctx,
                    "measure_disclosure": format_measure_disclosure(ctx) if ctx else None,
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

    if is_panel_table(profile):
        measure = preferred_measure_column(profile)
        geo = preferred_geo_column(profile)
        time_col = preferred_time_column(profile)
        measure_name = measure_label(
            measure or "value",
            dataset_title=profile.title,
            measure_context=profile.measure_context(measure or "value") if measure else None,
        )

        measure_ctx = profile.measure_context(measure or "value") if measure else None

        if measure and geo and measure in df.columns and geo in df.columns:
            by_geo = (
                df[[geo, measure]]
                .dropna()
                .groupby(geo, observed=True)[measure]
                .mean()
                .sort_values(ascending=False)
            )
            if len(by_geo) >= 2:
                top_geo = str(by_geo.index[0])
                top_val = float(by_geo.iloc[0])
                bottom_geo = str(by_geo.index[-1])
                bottom_val = float(by_geo.iloc[-1])
                idx += 1
                findings.append(
                    Finding(
                        id=f"f_{idx}",
                        type="descriptive",
                        title=(
                            f"{measure_name}: highest in {top_geo} ({top_val:,.2f}), "
                            f"lowest in {bottom_geo} ({bottom_val:,.2f})"
                        ),
                        columns=[measure, geo],
                        value=round(top_val, 4),
                        p_value=None,
                        n=len(by_geo),
                        method="panel_summary",
                        caveat=append_measure_note(
                            "country averages across all years in the loaded sample",
                            measure_ctx,
                        ),
                        sql=(
                            f"SELECT {sql_ident(geo)}, AVG({sql_ident(measure)}) AS mean_value "
                            f"FROM {profile.table} WHERE {sql_ident(measure)} IS NOT NULL "
                            f"GROUP BY 1 ORDER BY 2 DESC LIMIT 12"
                        ),
                        datasets=[profile.resource_id],
                        score=0.45,
                        details={
                            "dataset_title": profile.title,
                            "measure_context": measure_ctx,
                            "measure_disclosure": (
                                format_measure_disclosure(measure_ctx) if measure_ctx else None
                            ),
                            "chart_type": "group_comparison",
                            "top_geo": top_geo,
                            "bottom_geo": bottom_geo,
                        },
                    )
                )

        if measure and time_col and measure in df.columns and time_col in df.columns:
            ts = df[[time_col, measure]].dropna()
            if not pd.api.types.is_datetime64_any_dtype(ts[time_col]):
                ts[time_col] = pd.to_datetime(ts[time_col], errors="coerce", utc=True)
            ts = ts.dropna()
            if len(ts) >= 8:
                yearly = ts.groupby(time_col, observed=True)[measure].mean().sort_index()
                if len(yearly) >= 2:
                    first_year = yearly.index[0]
                    last_year = yearly.index[-1]
                    first_val = float(yearly.iloc[0])
                    last_val = float(yearly.iloc[-1])
                    if first_val != 0:
                        pct = ((last_val - first_val) / abs(first_val)) * 100.0
                    else:
                        pct = 0.0
                    idx += 1
                    findings.append(
                        Finding(
                            id=f"f_{idx}",
                            type="descriptive",
                            title=(
                                f"{measure_name}: global average moved from {first_val:,.2f} "
                                f"({getattr(first_year, 'year', first_year)}) to {last_val:,.2f} "
                                f"({getattr(last_year, 'year', last_year)})"
                            ),
                            columns=[measure, time_col],
                            value=round(pct, 2),
                            p_value=None,
                            n=len(yearly),
                            method="panel_trend_summary",
                            caveat=append_measure_note(
                                "global average by year across countries — descriptive, not a significance test",
                                measure_ctx,
                            ),
                            sql=(
                                f"SELECT {sql_ident(time_col)}, AVG({sql_ident(measure)}) AS {sql_ident(measure)} "
                                f"FROM {profile.table} WHERE {sql_ident(measure)} IS NOT NULL "
                                f"GROUP BY 1 ORDER BY 1"
                            ),
                            datasets=[profile.resource_id],
                            score=0.42,
                            details={
                                "dataset_title": profile.title,
                                "measure_context": measure_ctx,
                                "measure_disclosure": (
                                    format_measure_disclosure(measure_ctx) if measure_ctx else None
                                ),
                                "chart_type": "time_trend",
                                "pct_change": pct,
                            },
                        )
                    )

    return findings[:6]


def analysis_notes(
    profiles: list[TableProfile],
    *,
    tests_planned: int,
    statistical_hits: int,
    total_findings: int,
    cross_measure_report: dict | None = None,
    analysis_mode: str = "explore",
) -> list[str]:
    """Factual coverage notes for the analysis report (not dataset recommendations)."""
    notes: list[str] = []
    cross_ok = bool(cross_measure_report and cross_measure_report.get("success"))
    compare = analysis_mode == "compare"

    if compare and not cross_ok and not statistical_hits:
        notes.append(
            "Compare mode: no significant cross-dataset relationship found in overlapping country-years."
        )

    if tests_planned > 0:
        notes.append(
            f"Planned {tests_planned} statistical test(s) on the loaded sample "
            f"({statistical_hits} significant at p < 0.05, {total_findings} total ranked result(s))."
        )
    elif total_findings > 0:
        notes.append(f"Produced {total_findings} descriptive summary result(s) from the loaded sample.")

    if cross_measure_report:
        if cross_ok:
            summary = cross_measure_report.get("summary_note")
            if summary:
                notes.append(str(summary))
        elif cross_measure_report.get("reason"):
            notes.append(f"Cross-dataset correlation: {cross_measure_report['reason']}")

    for profile in profiles:
        if profile.n_rows < 20:
            notes.append(f"{profile.title} — small sample ({profile.n_rows} rows); many tests need more data.")

        has_date = bool(profile.datetime) or any(
            c.name.lower() in ("date", "year") for c in profile.columns
        )
        if len(profile.numeric) == 1 and has_date:
            if cross_ok:
                continue
            notes.append(
                f"{profile.title} — time-series shape (date + numeric value); "
                "trend tests ran, correlation skipped (needs 2+ numeric fields)."
            )
        elif len(profile.numeric) < 2:
            if cross_ok:
                continue
            notes.append(
                f"{profile.title} — only {len(profile.numeric)} numeric field(s); "
                "correlation/regression tests were not applicable."
            )

    return notes[:8]
