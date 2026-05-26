import asyncio
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from findings_api.analysis.runner import run_analysis_pipeline
from findings_api.background import run_in_background
from findings_api.db import get_db, get_session_factory
from findings_api.ingest.pipeline import apply_session_config, run_ingest
from findings_api.models import AnalysisSession, CatalogResource
from findings_api.routers.search import _to_result
from findings_api.schemas import (
    CreateSessionRequest,
    SessionConfigUpdate,
    SessionDetail,
    SessionResponse,
    SessionStatusResponse,
)
from findings_api.session_recovery import fail_stale_session, recover_stale_sessions

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _session_detail(db: Session, session: AnalysisSession) -> SessionDetail:
    catalogs = []
    for rid in session.resource_ids:
        row = db.get(CatalogResource, rid)
        if row:
            catalogs.append(_to_result(row))
    return SessionDetail(
        id=session.id,
        status=session.status,
        phase=session.phase,
        message=session.message,
        percent=session.percent,
        resource_ids=session.resource_ids,
        user_intent=session.user_intent,
        config=session.config or {},
        row_counts=session.row_counts,
        preview=session.preview,
        error=session.error,
        catalogs=catalogs,
    )


def _schedule_ingest(background_tasks: BackgroundTasks, session_id: str) -> None:
    def _run():
        factory = get_session_factory()
        db = factory()
        try:
            asyncio.run(run_ingest(db, session_id))
        finally:
            db.close()

    background_tasks.add_task(lambda: run_in_background(_run))


@router.post("", response_model=SessionResponse)
def create_session(
    body: CreateSessionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    for rid in body.resource_ids:
        row = db.get(CatalogResource, rid)
        if not row:
            raise HTTPException(status_code=404, detail=f"Unknown resource: {rid}")

    session_id = str(uuid4())
    session = AnalysisSession(
        id=session_id,
        status="ingesting",
        phase="ingest",
        message="Starting download…",
        percent=0,
        resource_ids=body.resource_ids,
        user_intent=body.user_intent,
        config={"ml_enabled": body.ml_enabled, "filters": {}, "join_keys": []},
    )
    db.add(session)
    db.commit()
    _schedule_ingest(background_tasks, session_id)
    return SessionResponse(id=session_id, status=session.status, resource_ids=body.resource_ids)


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.get(AnalysisSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_detail(db, session)


@router.patch("/{session_id}", response_model=SessionDetail)
def update_session(
    session_id: str,
    body: SessionConfigUpdate,
    db: Session = Depends(get_db),
):
    session = db.get(AnalysisSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status not in ("ready", "created"):
        raise HTTPException(status_code=409, detail=f"Cannot update session in status {session.status}")

    config = dict(session.config or {})
    if body.user_intent is not None:
        session.user_intent = body.user_intent
    if body.ml_enabled is not None:
        config["ml_enabled"] = body.ml_enabled
    if body.filters is not None:
        config["filters"] = body.filters
    if body.join_keys is not None:
        config["join_keys"] = body.join_keys
    session.config = config
    db.add(session)
    db.commit()

    if session.duckdb_path and session.preview:
        try:
            apply_session_config(db, session_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        session = db.get(AnalysisSession, session_id)

    return _session_detail(db, session)


def _schedule_analysis(background_tasks: BackgroundTasks, session_id: str) -> None:
    def _run():
        factory = get_session_factory()
        db = factory()
        try:
            asyncio.run(run_analysis_pipeline(db, session_id))
        finally:
            db.close()

    background_tasks.add_task(lambda: run_in_background(_run))


@router.post("/{session_id}/run")
def run_analysis(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    session = db.get(AnalysisSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "ready":
        raise HTTPException(status_code=409, detail="Session not ready for analysis")
    session.status = "analyzing"
    session.phase = "prepare"
    session.message = "Preparing analysis…"
    session.percent = 5
    db.add(session)
    db.commit()
    _schedule_analysis(background_tasks, session_id)
    return {"session_id": session_id, "status": session.status, "phase": session.phase}


def _ingest_estimate(session) -> int | None:
    if session.status != "ingesting":
        return None
    pct = session.percent or 0
    if pct >= 100:
        return 0
    if pct <= 0:
        return 120
    # Rough linear estimate from progress so far
    return max(15, int((100 - pct) * 1.5))


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
def session_status(session_id: str, db: Session = Depends(get_db)):
    session = db.get(AnalysisSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if fail_stale_session(db, session):
        session = db.get(AnalysisSession, session_id)
    estimate = None
    if session.status == "ingesting":
        estimate = _ingest_estimate(session)
    elif session.status == "analyzing":
        pct = session.percent or 0
        estimate = max(10, int((100 - pct) * 1.2)) if pct < 100 else 0
    elif session.status == "complete":
        estimate = 0
    return SessionStatusResponse(
        session_id=session_id,
        status=session.status,
        phase=session.phase,
        message=session.message,
        percent=session.percent,
        row_counts=session.row_counts,
        estimate_remaining_sec=estimate,
    )


@router.get("/{session_id}/results")
def session_results(session_id: str, db: Session = Depends(get_db)):
    session = db.get(AnalysisSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    preview = session.preview or {}
    results = preview.get("results") or {}
    return {
        "session_id": session_id,
        "status": session.status,
        "findings": results.get("findings", []),
        "display_finding_ids": results.get("display_finding_ids", []),
        "charts": results.get("charts", []),
        "join_report": results.get("join_report"),
        "analysis_report": results.get("analysis_report"),
        "column_glossary": results.get("column_glossary", []),
        "ai_summary": results.get("ai_summary"),
        "ai_summary_blocks": results.get("ai_summary_blocks"),
        "ai_summary_source": results.get("ai_summary_source"),
        "message": session.message,
        "preview": session.preview,
    }
