from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from findings_api.analysis.ai_summary import generate_ai_summary
from findings_api.analysis.charts import charts_for_findings
from findings_api.analysis.descriptive import analysis_notes, descriptive_findings
from findings_api.analysis.join import assess_join, build_joined_table
from findings_api.analysis.ml.clustering import run_anomaly, run_clustering
from findings_api.analysis.profile import profile_table
from findings_api.analysis.labels import glossary_for_columns
from findings_api.analysis.narrative import EXCLUDE_FROM_RANKING, enrich_findings
from findings_api.analysis.ranker import DISPLAY_TOP, rank_findings, select_display_findings
from findings_api.analysis.selector import plans_for_table
from findings_api.analysis.tests.chi_square import run_chi_square
from findings_api.analysis.tests.correlation import run_correlation
from findings_api.analysis.tests.group_comparison import run_group_comparison
from findings_api.analysis.tests.trend import run_trend
from findings_api.analysis.types import Finding
from findings_api.ingest.duckdb_store import connect
from findings_api.ingest.pipeline import apply_session_config
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
    if status:
        session.status = status
    db.add(session)
    db.commit()


def _execute_plan(conn, plan, finding_offset: int) -> list[Finding]:
    if plan.kind == "correlation":
        return run_correlation(
            conn,
            plan.table,
            plan.columns,
            resource_id=plan.resource_id,
            dataset_title=plan.title,
            finding_offset=finding_offset,
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
        )
    return []


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
            apply_session_config(db, session_id)
            session = db.get(AnalysisSession, session_id)
            if not session:
                return
            preview = dict(session.preview or {})
            datasets = preview.get("datasets") or []

        config = session.config or {}
        ml_enabled = bool(config.get("ml_enabled", True))
        join_keys = config.get("join_keys") or []

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

        table_meta = {table: (rid, title) for table, rid, title in tables}
        target_table = tables[0][0]
        join_report = None
        if len(tables) == 2 and join_keys:
            _set_progress(db, session, phase="join", message="Combining datasets", percent=30)
            join_key = join_keys[0]
            ok, matched, warning = assess_join(conn, tables[0][0], tables[1][0], join_key)
            if ok:
                build_joined_table(conn, tables[0][0], tables[1][0], join_key)
                target_table = "analysis_joined"
                rid_a, title_a = table_meta[tables[0][0]]
                rid_b, title_b = table_meta[tables[1][0]]
                table_meta["analysis_joined"] = (f"{rid_a}+{rid_b}", f"{title_a} + {title_b}")
                join_report = {"join_key": join_key, "matched_rows": matched}
            else:
                join_report = {
                    "join_key": join_key,
                    "matched_rows": matched,
                    "warning": warning,
                }

        analyze_tables = (
            [target_table]
            if target_table == "analysis_joined" and not (join_report and join_report.get("warning"))
            else [t[0] for t in tables]
        )

        profiles = []
        for table in analyze_tables:
            rid, title = table_meta.get(table, ("", "Dataset"))
            profiles.append(profile_table(conn, table, resource_id=rid, title=title))

        _set_progress(db, session, phase="analyze", message="Running statistical tests", percent=55)
        findings: list[Finding] = []
        tests_planned = 0
        offset = 0
        for profile in profiles:
            plans = plans_for_table(profile)
            tests_planned += len(plans)
            for plan in plans:
                findings.extend(_execute_plan(conn, plan, offset))
                offset = len(findings)

            if ml_enabled:
                ml_n = profile.n_rows
                findings.extend(
                    run_clustering(
                        conn,
                        profile.table,
                        profile.numeric,
                        resource_id=profile.resource_id,
                        dataset_title=profile.title,
                        n_rows=ml_n,
                        finding_offset=offset,
                    )
                )
                offset = len(findings)
                findings.extend(
                    run_anomaly(
                        conn,
                        profile.table,
                        profile.numeric,
                        resource_id=profile.resource_id,
                        dataset_title=profile.title,
                        n_rows=ml_n,
                        finding_offset=offset,
                    )
                )
                offset = len(findings)

        statistical = [
            f for f in findings if f.type != "descriptive" and f.type not in EXCLUDE_FROM_RANKING
        ]
        ranked_all = enrich_findings(rank_findings(statistical))
        display = select_display_findings(ranked_all, DISPLAY_TOP)
        if not ranked_all:
            desc_offset = 0
            for profile in profiles:
                ranked_all.extend(descriptive_findings(profile, conn, finding_offset=desc_offset))
                desc_offset = len(ranked_all)
            ranked_all = enrich_findings(rank_findings(ranked_all))
            display = select_display_findings(ranked_all, min(DISPLAY_TOP, len(ranked_all)))

        charts = charts_for_findings(display)
        notes = analysis_notes(profiles, tests_planned=tests_planned, statistical=len(ranked_all))

        column_glossary = glossary_for_columns(
            [c.name for p in profiles for c in p.columns]
        )

        _set_progress(db, session, phase="finalize", message="Writing summary", percent=92)
        display_dicts = [f.to_dict() for f in display]
        dataset_titles = [p.title for p in profiles]
        ai_summary, ai_summary_source, ai_summary_blocks = generate_ai_summary(
            display_dicts,
            user_intent=session.user_intent,
            dataset_titles=dataset_titles,
        )

        _set_progress(db, session, phase="finalize", message="Building results", percent=96)
        preview["results"] = {
            "findings": [f.to_dict() for f in ranked_all],
            "display_finding_ids": [f.id for f in display],
            "charts": [c.to_dict() for c in charts],
            "join_report": join_report,
            "analysis_tables": analyze_tables,
            "column_glossary": column_glossary,
            "ai_summary": ai_summary,
            "ai_summary_blocks": ai_summary_blocks,
            "ai_summary_source": ai_summary_source,
            "analysis_report": {
                "tests_planned": tests_planned,
                "statistical_findings": len(ranked_all),
                "display_limit": DISPLAY_TOP,
                "display_count": len(display),
                "total_findings": len(ranked_all),
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
