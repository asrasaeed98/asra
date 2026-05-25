import asyncio
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

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

    background_tasks.add_task(_run)


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


@router.post("/{session_id}/run")
def run_analysis(session_id: str, db: Session = Depends(get_db)):
    session = db.get(AnalysisSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "ready":
        raise HTTPException(status_code=409, detail="Session not ready for analysis")
    session.status = "analyzing"
    session.phase = "prepare"
    session.message = "Preparing table — analysis engine arrives in slice 4"
    session.percent = 10
    db.add(session)
    db.commit()
    return {"session_id": session_id, "status": session.status, "phase": session.phase}


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
def session_status(session_id: str, db: Session = Depends(get_db)):
    session = db.get(AnalysisSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    estimate = None
    if session.status == "ingesting":
        estimate = 90
    elif session.status == "analyzing":
        estimate = 120
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
    return {
        "session_id": session_id,
        "findings": [],
        "charts": [],
        "ai_summary": None,
        "message": "Run analysis after ingest (slices 4–7).",
        "preview": session.preview,
    }
