"""Assemble rich context for AI key-findings summaries."""

from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from findings_api.analysis.measure_semantics import _sample_rows_for_prompt
from findings_api.analysis.profile import read_table_frame
from findings_api.analysis.types import ChartSpec, Finding, TableProfile
from findings_api.models import CatalogResource


def _serialize_join(join_report: dict[str, Any] | None) -> dict[str, Any] | None:
    if not join_report:
        return None

    def _cross_block() -> dict[str, Any] | None:
        cross = join_report.get("cross_measure")
        if not isinstance(cross, dict):
            return None
        return {
            "success": bool(cross.get("success")),
            "strategy": cross.get("strategy"),
            "matched_pairs": cross.get("matched_pairs"),
            "entities": cross.get("entities"),
            "year_start": cross.get("year_start"),
            "year_end": cross.get("year_end"),
            "reason": cross.get("reason"),
        }

    warning = join_report.get("warning")
    if warning:
        out: dict[str, Any] = {
            "attempted": True,
            "succeeded": False,
            "warning": str(warning),
        }
        cross = _cross_block()
        if cross:
            out["cross_measure"] = cross
        return out
    join_on = join_report.get("join_on") or []
    keys = []
    for pair in join_on:
        if not isinstance(pair, dict):
            continue
        left = pair.get("left") or ""
        right = pair.get("right") or ""
        if left and left == right:
            keys.append(left)
        elif left or right:
            keys.append(f"{left} ↔ {right}")
    matched = join_report.get("matched_rows")
    out: dict[str, Any] = {
        "attempted": True,
        "succeeded": True,
        "join_keys": keys,
        "auto_detected": bool(join_report.get("auto")),
    }
    if isinstance(matched, int):
        out["matched_rows"] = matched
    cross = _cross_block()
    if cross:
        out["cross_measure"] = cross
    return out


def _column_entries(profile: TableProfile) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for col in profile.columns:
        ctx = profile.measure_contexts.get(col.name) or {}
        entry: dict[str, Any] = {
            "name": col.name,
            "kind": col.kind,
            "null_pct": round(col.null_pct, 2),
            "unique_values": col.nunique,
        }
        if ctx.get("label"):
            entry["label"] = ctx["label"]
        if ctx.get("unit"):
            entry["unit"] = ctx["unit"]
        if ctx.get("source"):
            entry["label_source"] = ctx["source"]
        entries.append(entry)
    return entries


def _dataset_entry(
    db: Session,
    profile: TableProfile,
    conn,
    *,
    sample_limit: int = 3,
) -> dict[str, Any]:
    catalog = db.get(CatalogResource, profile.resource_id)
    portal = catalog.portal if catalog else None
    try:
        frame = read_table_frame(conn, profile.table)
        sample_rows = _sample_rows_for_prompt(frame, limit=sample_limit) if not frame.empty else []
    except Exception:
        sample_rows = []

    entry: dict[str, Any] = {
        "resource_id": profile.resource_id,
        "title": profile.title,
        "portal": portal,
        "is_nyc_open_data": portal == "nyc_open_data",
        "n_rows_analyzed": profile.n_rows,
        "columns": _column_entries(profile),
        "analysis_columns": {
            "numeric": profile.analysis_numeric,
            "categorical": profile.analysis_categorical,
            "datetime": profile.analysis_datetime,
        },
        "field_relevance": profile.field_relevance,
        "facts": profile.facts,
        "sample_rows": sample_rows,
    }
    if catalog:
        entry["source"] = {
            "publisher": catalog.publisher,
            "organization": catalog.organization,
            "source_url": catalog.source_url,
            "license": catalog.license_display,
            "attribution": catalog.attribution_text,
        }
    return entry


def build_summary_context(
    db: Session,
    conn,
    *,
    profiles: list[TableProfile],
    all_findings: list[Finding],
    display_finding_ids: list[str],
    user_intent: str | None,
    join_report: dict[str, Any] | None,
    methods_run: list[str],
    analysis_overview: dict[str, Any],
    column_glossary: list[dict[str, Any]],
    charts: list[ChartSpec],
) -> dict[str, Any]:
    """JSON-serializable bundle for the summary model."""
    chart_by_finding = {c.finding_id: c.title for c in charts}
    finding_dicts = []
    for finding in all_findings:
        payload = finding.to_dict()
        chart_title = chart_by_finding.get(finding.id)
        if chart_title:
            payload.setdefault("details", {})
            if isinstance(payload["details"], dict):
                payload["details"] = dict(payload["details"])
                payload["details"]["chart_title"] = chart_title
        finding_dicts.append(payload)

    datasets = [_dataset_entry(db, profile, conn) for profile in profiles]
    both_nyc = len(datasets) == 2 and all(d.get("is_nyc_open_data") for d in datasets)

    return {
        "user_intent": (user_intent or "").strip() or None,
        "datasets": datasets,
        "both_datasets_nyc_open_data": both_nyc,
        "join": _serialize_join(join_report),
        "methods_run": methods_run,
        "analysis_overview": analysis_overview,
        "column_glossary": column_glossary,
        "all_findings": finding_dicts,
        "display_finding_ids": display_finding_ids,
    }
