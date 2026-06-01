from __future__ import annotations

import json
import logging
from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from findings_api.analysis.ai_summary import generate_ai_summary
from findings_api.analysis.ai_usage import is_over_budget, record_usage
from findings_api.analysis.charts import charts_for_findings
from findings_api.analysis.cross_measure import run_cross_measure_analysis
from findings_api.analysis.descriptive import analysis_notes, descriptive_findings
from findings_api.analysis.mode import resolve_analysis_mode, table_sets_for_mode
from findings_api.analysis.join import (
    assess_join_on,
    auto_join_selection,
    build_joined_table_on,
    normalize_join_on,
    suggest_joins,
)
from findings_api.analysis.ml.clustering import run_ml_suite
from findings_api.analysis.profile import profile_table
from findings_api.analysis.labels import glossary_for_columns
from findings_api.analysis.methods import summarize_methods_run
from findings_api.analysis.narrative import enrich_findings
from findings_api.analysis.ranker import DISPLAY_TOP, apply_ranking_context, rank_findings, select_display_findings
from findings_api.analysis.selector import plans_for_table
from findings_api.analysis.summary_context import build_summary_context
from findings_api.analysis.tests.chi_square import run_chi_square
from findings_api.analysis.tests.correlation import run_correlation
from findings_api.analysis.tests.group_comparison import run_group_comparison
from findings_api.analysis.tests.trend import run_trend
from findings_api.analysis.types import Finding
from findings_api.ingest.duckdb_store import connect
from findings_api.models import AnalysisSession

logger = logging.getLogger(__name__)


def _set_progress(
    db: Session,
    session: AnalysisSession,
    *,
    phase: str,
    message: str,
    percent: int,
    status: str | None = None,
) -> None:
    session.phase = phase
    session.message = message
    session.percent = percent
    session.updated_at = datetime.now(timezone.utc)
    if status:
        session.status = status
    db.add(session)
    db.commit()


def _execute_plan(
    conn,
    plan,
    finding_offset: int,
    measure_contexts: dict[str, dict[str, str | None]] | None = None,
) -> list[Finding]:
    extra = plan.extra or {}
    measure_context = extra.get("measure_context")
    if plan.kind == "correlation":
        return run_correlation(
            conn,
            plan.table,
            plan.columns,
            resource_id=plan.resource_id,
            dataset_title=plan.title,
            finding_offset=finding_offset,
            measure_contexts=measure_contexts,
        )
    if plan.kind == "group_comparison" and len(plan.columns) == 2:
        num, cat = plan.columns
        return run_group_comparison(
            conn,
            plan.table,
            num,
            cat,
            resource_id=plan.resource_id,
            dataset_title=plan.title,
            finding_offset=finding_offset,
            measure_context=measure_context,
            measure_contexts=measure_contexts,
        )
    if plan.kind == "chi_square" and len(plan.columns) == 2:
        return run_chi_square(
            conn,
            plan.table,
            plan.columns[0],
            plan.columns[1],
            resource_id=plan.resource_id,
            dataset_title=plan.title,
            finding_offset=finding_offset,
        )
    if plan.kind == "trend" and len(plan.columns) == 2:
        val, dt = plan.columns
        return run_trend(
            conn,
            plan.table,
            val,
            dt,
            resource_id=plan.resource_id,
            dataset_title=plan.title,
            finding_offset=finding_offset,
            aggregate_by_time=bool(extra.get("aggregate_by_time")),
            measure_context=measure_context,
            measure_contexts=measure_contexts,
        )
    return []


def _resolve_source_measures(
    conn, table: str, title: str
) -> dict[str, dict[str, str | None]]:
    """Resolve measure labels for a table's generic measure columns (pre-join)."""
    from findings_api.analysis.measure_semantics import (
        MEASURE_COLUMN_NAMES,
        resolve_measure_label,
    )
    from findings_api.analysis.profile import read_table_frame

    df = read_table_frame(conn, table)
    out: dict[str, dict[str, str | None]] = {}
    for col in df.columns:
        if str(col).lower() in MEASURE_COLUMN_NAMES:
            out[str(col)] = resolve_measure_label(
                conn, table, str(col), catalog_title=title, use_ai=True
            )
    return out


async def run_analysis_pipeline(db: Session, session_id: str) -> None:
    session = db.get(AnalysisSession, session_id)
    if not session:
        return

    try:
        preview = dict(session.preview or {})
        datasets = preview.get("datasets") or []
        if not datasets:
            raise ValueError("No ingested datasets to analyze")

        if session.duckdb_path:
            from findings_api.ingest.pipeline import apply_session_config

            apply_session_config(db, session_id)
            session = db.get(AnalysisSession, session_id)
            if not session:
                return
            preview = dict(session.preview or {})
            datasets = preview.get("datasets") or []

        config = session.config or {}
        ml_enabled = bool(config.get("ml_enabled", True))
        join_keys = config.get("join_keys") or []
        join_on = config.get("join_on") or []
        join_pairs = normalize_join_on(join_keys=join_keys, join_on=join_on)

        _set_progress(db, session, phase="prepare", message="Preparing analysis tables", percent=15)
        conn = connect(session_id)

        tables: list[tuple[str, str, str]] = []
        for item in datasets:
            analysis_table = item.get("analysis_table") or item.get("raw_table")
            if not analysis_table:
                raise ValueError("Missing analysis table — re-run ingest")
            tables.append(
                (
                    analysis_table,
                    item.get("resource_id", ""),
                    item.get("title", "Dataset"),
                )
            )

        analysis_mode = resolve_analysis_mode(len(tables))

        auto_joined = False
        if analysis_mode == "compare" and not join_pairs:
            ingest_profiles: list[dict] = []
            for table, _, _ in tables:
                for item in datasets:
                    item_table = item.get("analysis_table") or item.get("raw_table")
                    if item_table == table:
                        ingest_profiles.append(item)
                        break
            if len(ingest_profiles) == 2:
                suggestions = suggest_joins(conn, ingest_profiles)
                picked = auto_join_selection(suggestions)
                if picked:
                    join_pairs = list(zip(picked.left_keys, picked.right_keys, strict=True))
                    auto_joined = True
                    logger.info("Auto-selected join for analysis: %s", picked.label)

        table_meta = {table: (rid, title) for table, rid, title in tables}
        target_table = tables[0][0]
        join_report = None
        joined_measure_contexts: dict[str, dict[str, str | None]] = {}
        if analysis_mode == "compare" and join_pairs:
            _set_progress(db, session, phase="join", message="Combining datasets", percent=30)
            left_t, right_t = tables[0][0], tables[1][0]
            ok, matched, warning, overlap_left, overlap_right = assess_join_on(
                conn, left_t, right_t, join_pairs
            )
            if ok:
                from findings_api.analysis.measure_semantics import (
                    format_measure_disclosure,
                    measure_slug,
                )

                # Resolve each dataset's measure label while columns are still
                # unambiguous, then alias the generic measure columns to unique,
                # meaningful names so they never collapse into value/value_1.
                used_slugs: set[str] = set()
                left_renames: dict[str, str] = {}
                right_renames: dict[str, str] = {}
                join_key_cols = {c.lower() for pair in join_pairs for c in pair}
                for src_table, renames, side in (
                    (left_t, left_renames, "left"),
                    (right_t, right_renames, "right"),
                ):
                    _, src_title = table_meta[src_table]
                    for col, ctx in _resolve_source_measures(conn, src_table, src_title).items():
                        if col.lower() in join_key_cols:
                            continue
                        slug = measure_slug(
                            str(ctx.get("label") or col),
                            fallback=f"{side}_{col}",
                            used=used_slugs,
                        )
                        renames[col] = slug
                        new_ctx = dict(ctx)
                        new_ctx["column"] = slug
                        new_ctx["disclosure"] = format_measure_disclosure(new_ctx)
                        joined_measure_contexts[slug] = new_ctx
                build_joined_table_on(
                    conn,
                    left_t,
                    right_t,
                    join_pairs,
                    left_renames=left_renames or None,
                    right_renames=right_renames or None,
                )
                target_table = "analysis_joined"
                rid_a, title_a = table_meta[tables[0][0]]
                rid_b, title_b = table_meta[tables[1][0]]
                table_meta["analysis_joined"] = (f"{rid_a}+{rid_b}", f"{title_a} + {title_b}")
                join_report = {
                    "join_on": [{"left": l, "right": r} for l, r in join_pairs],
                    "join_key": join_pairs[0][0] if len(join_pairs) == 1 else None,
                    "matched_rows": matched,
                    "overlap_left_pct": round(overlap_left, 4),
                    "overlap_right_pct": round(overlap_right, 4),
                    "auto": auto_joined,
                }
            else:
                join_report = {
                    "join_on": [{"left": l, "right": r} for l, r in join_pairs],
                    "join_key": join_pairs[0][0] if len(join_pairs) == 1 else None,
                    "matched_rows": matched,
                    "overlap_left_pct": round(overlap_left, 4),
                    "overlap_right_pct": round(overlap_right, 4),
                    "warning": warning,
                    "auto": auto_joined,
                }

        joined_ok = bool(
            analysis_mode == "compare"
            and join_report
            and int(join_report.get("matched_rows") or 0) >= 8
            and not join_report.get("warning")
        )

        joined_table = "analysis_joined" if joined_ok else None
        table_names = [t[0] for t in tables]
        context_tables, test_tables = table_sets_for_mode(
            mode=analysis_mode,
            table_names=table_names,
            joined_table=joined_table,
            joined_ok=joined_ok,
        )

        profiles = []
        test_table_set = set(test_tables)
        for table in context_tables:
            rid, title = table_meta.get(table, ("", "Dataset"))
            extra_contexts = (
                joined_measure_contexts if table == "analysis_joined" else None
            )
            profile = profile_table(
                conn,
                table,
                resource_id=rid,
                title=title,
                extra_measure_contexts=extra_contexts,
            )
            profiles.append(profile)

        _set_progress(db, session, phase="analyze", message="Running statistical tests", percent=50)
        findings: list[Finding] = []
        tests_planned = 0
        offset = 0
        for profile in profiles:
            if profile.table not in test_table_set:
                continue
            table_joined = joined_ok and profile.table == "analysis_joined"
            plans = plans_for_table(profile, joined=table_joined)
            primary_plans = [
                p for p in plans if (p.extra or {}).get("tier") != "derived"
            ]
            derived_plans = [
                p for p in plans if (p.extra or {}).get("tier") == "derived"
            ]
            tests_planned += len(plans)

            for plan in primary_plans:
                extra = dict(plan.extra or {})
                if plan.columns:
                    ctx = profile.measure_context(plan.columns[0])
                    if ctx:
                        extra["measure_context"] = ctx
                        plan = replace(plan, extra=extra)
                findings.extend(
                    _execute_plan(conn, plan, offset, measure_contexts=profile.measure_contexts)
                )
                offset = len(findings)

            if derived_plans:
                _set_progress(
                    db,
                    session,
                    phase="analyze",
                    message="Running derived summaries (e.g. year averages)",
                    percent=62,
                )
                for plan in derived_plans:
                    extra = dict(plan.extra or {})
                    if plan.columns:
                        ctx = profile.measure_context(plan.columns[0])
                        if ctx:
                            extra["measure_context"] = ctx
                            plan = replace(plan, extra=extra)
                    findings.extend(
                        _execute_plan(conn, plan, offset, measure_contexts=profile.measure_contexts)
                    )
                    offset = len(findings)

            if ml_enabled:
                _set_progress(
                    db,
                    session,
                    phase="analyze",
                    message="Running ML models",
                    percent=72,
                )

                def _ml_progress(step: str) -> None:
                    _set_progress(
                        db,
                        session,
                        phase="analyze",
                        message=f"Running ML — {step}",
                        percent=72,
                    )

                findings.extend(
                    run_ml_suite(conn, profile, finding_offset=offset, on_step=_ml_progress)
                )
                offset = len(findings)

        cross_measure_result = None
        if analysis_mode == "compare":
            left_t, right_t = tables[0][0], tables[1][0]
            rid_a, title_a = table_meta[left_t]
            rid_b, title_b = table_meta[right_t]
            cross_measure_result = run_cross_measure_analysis(
                conn,
                left_t,
                right_t,
                left_resource_id=rid_a,
                right_resource_id=rid_b,
                left_title=title_a,
                right_title=title_b,
                finding_offset=offset,
            )
            findings.extend(cross_measure_result.findings)
            if join_report is None:
                join_report = {}
            join_report["cross_measure"] = cross_measure_result.report

        relationship_ok = analysis_mode == "compare" and (
            joined_ok
            or bool(cross_measure_result and cross_measure_result.paired_ok)
        )

        if joined_ok:
            for finding in findings:
                if finding.type == "spearman_correlation" and not (finding.details or {}).get(
                    "cross_measure"
                ):
                    finding.details = dict(finding.details or {})
                    finding.details["primary"] = True

        ranked_candidates = [f for f in findings if f.type != "descriptive"]
        apply_ranking_context(
            ranked_candidates,
            compare_mode=relationship_ok,
        )
        ranked_all = enrich_findings(rank_findings(ranked_candidates))
        display = select_display_findings(
            ranked_all,
            DISPLAY_TOP,
            compare_mode=relationship_ok,
        )
        if not ranked_all:
            desc_offset = 0
            for profile in profiles:
                ranked_all.extend(descriptive_findings(profile, conn, finding_offset=desc_offset))
                desc_offset = len(ranked_all)
            ranked_all = enrich_findings(rank_findings(ranked_all))
            display = select_display_findings(ranked_all, min(DISPLAY_TOP, len(ranked_all)))

        charts = charts_for_findings(conn, display, joined=relationship_ok)
        statistical_hits = len([f for f in ranked_all if f.type != "descriptive"])
        cross_measure_report = (
            cross_measure_result.report if cross_measure_result else None
        )
        notes = analysis_notes(
            profiles,
            tests_planned=tests_planned,
            statistical_hits=statistical_hits,
            total_findings=len(ranked_all),
            cross_measure_report=cross_measure_report,
            analysis_mode=analysis_mode,
        )

        column_glossary = glossary_for_columns(
            [c.name for p in profiles for c in p.columns],
            measure_contexts={
                col: ctx
                for p in profiles
                for col, ctx in p.measure_contexts.items()
            },
        )

        _set_progress(db, session, phase="finalize", message="Writing summary", percent=92)
        methods_run = summarize_methods_run(
            profiles,
            ml_enabled=ml_enabled,
            analysis_mode=analysis_mode,
            joined_ok=joined_ok,
            cross_measure_ran=analysis_mode == "compare",
        )
        analysis_overview = {
            "analysis_mode": analysis_mode,
            "tests_planned": tests_planned,
            "statistical_findings": len(ranked_all),
            "total_findings": len(ranked_all),
            "display_count": len(display),
            "ml_enabled": ml_enabled,
            "notes": notes,
        }
        summary_context = build_summary_context(
            db,
            conn,
            profiles=profiles,
            all_findings=ranked_all,
            display_finding_ids=[f.id for f in display],
            user_intent=session.user_intent,
            join_report=join_report,
            methods_run=methods_run,
            analysis_overview=analysis_overview,
            column_glossary=column_glossary,
            charts=charts,
        )
        ai_summary, ai_summary_source, ai_summary_blocks, ai_summary_fallback_reason = generate_ai_summary(
            summary_context,
            allow_ai=not is_over_budget(db),
            on_usage=lambda model, tin, tout: record_usage(db, model, tin, tout),
        )

        measure_notes = [
            ctx
            for p in profiles
            for ctx in p.measure_contexts.values()
            if ctx.get("disclosure")
        ]

        _set_progress(db, session, phase="finalize", message="Building results", percent=96)
        preview["results"] = {
            "findings": [f.to_dict() for f in ranked_all],
            "display_finding_ids": [f.id for f in display],
            "charts": [c.to_dict() for c in charts],
            "join_report": join_report,
            "analysis_mode": analysis_mode,
            "analysis_tables": context_tables,
            "column_glossary": column_glossary,
            "ai_summary": ai_summary,
            "ai_summary_blocks": ai_summary_blocks,
            "ai_summary_source": ai_summary_source,
            "ai_summary_fallback_reason": ai_summary_fallback_reason,
            "dataset_facts": [p.facts for p in profiles if p.facts],
            "analysis_report": {
                "analysis_mode": analysis_mode,
                "tests_planned": tests_planned,
                "statistical_findings": len(ranked_all),
                "display_limit": DISPLAY_TOP,
                "display_count": len(display),
                "total_findings": len(ranked_all),
                "methods_run": methods_run,
                "ml_enabled": ml_enabled,
                "datasets": [
                    {
                        "title": p.title,
                        "n_rows": p.n_rows,
                        "numeric_columns": p.numeric,
                        "categorical_columns": p.categorical,
                        "datetime_columns": p.datetime,
                    }
                    for p in profiles
                ],
                "notes": notes,
                "measure_notes": measure_notes,
            },
        }
        session.preview = preview
        session.status = "complete"
        session.phase = "finalize"
        if ranked_all and any(f.type != "descriptive" for f in ranked_all):
            session.message = (
                f"Found {len(ranked_all)} significant result(s) — showing top {len(display)}"
            )
        elif ranked_all:
            session.message = "Analysis complete — descriptive summary (no significant tests)"
        else:
            session.message = "Analysis complete — no significant findings"
        session.percent = 100
        db.add(session)
        db.commit()
        conn.close()
    except Exception as exc:
        logger.exception("Analysis failed for %s", session_id)
        session = db.get(AnalysisSession, session_id)
        if session:
            session.status = "failed"
            session.phase = "failed"
            session.message = str(exc)
            session.error = str(exc)
            session.percent = 0
            db.add(session)
            db.commit()
