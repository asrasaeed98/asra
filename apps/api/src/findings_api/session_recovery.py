from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from findings_api.models import AnalysisSession

_STALE_AFTER = timedelta(minutes=25)
_STALE_AFTER_LARGE = timedelta(minutes=60)
_ACTIVE = frozenset({"ingesting", "analyzing"})


def stale_after(session: AnalysisSession) -> timedelta:
    """How long without a progress heartbeat before an active session is marked failed."""
    if (session.config or {}).get("large_download"):
        return _STALE_AFTER_LARGE
    return _STALE_AFTER


def stale_failure_message(session: AnalysisSession) -> str:
    """User-facing copy when stale recovery marks a session failed."""
    large = bool((session.config or {}).get("large_download"))
    if session.status == "ingesting" or session.phase == "ingest":
        if large:
            return (
                "This large dataset download took longer than expected and was stopped. "
                "Go back to search and try again — large NYC downloads can take several minutes."
            )
        return (
            "Download was interrupted — this can happen if the server restarted while your "
            "data was loading. Go back to search and try again."
        )
    return (
        "Analysis took longer than expected and was stopped. "
        "Go back to search and try again."
    )


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_session_stale(session: AnalysisSession, *, now: datetime | None = None) -> bool:
    if session.status not in _ACTIVE:
        return False
    updated = _as_utc(session.updated_at)
    if updated is None:
        return False
    clock = now or datetime.now(timezone.utc)
    return clock - updated > stale_after(session)


def fail_stale_session(db: Session, session: AnalysisSession) -> bool:
    if not is_session_stale(session):
        return False
    session.status = "failed"
    session.phase = "failed"
    message = stale_failure_message(session)
    session.message = message
    session.error = message
    session.percent = 0
    db.add(session)
    db.commit()
    return True


def recover_stale_sessions(db: Session) -> int:
    rows = db.query(AnalysisSession).filter(AnalysisSession.status.in_(_ACTIVE)).all()
    n = 0
    for row in rows:
        if fail_stale_session(db, row):
            n += 1
    return n
