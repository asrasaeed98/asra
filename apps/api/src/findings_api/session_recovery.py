from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from findings_api.models import AnalysisSession

_STALE_AFTER = timedelta(minutes=25)
_ACTIVE = frozenset({"ingesting", "analyzing"})


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
    return clock - updated > _STALE_AFTER


def fail_stale_session(db: Session, session: AnalysisSession) -> bool:
    if not is_session_stale(session):
        return False
    session.status = "failed"
    session.phase = "failed"
    session.message = (
        "Load was interrupted or timed out (often happens if the API restarted). "
        "Go back to search and try again."
    )
    session.error = session.message
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
