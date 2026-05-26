from datetime import datetime, timedelta, timezone

from findings_api.models import AnalysisSession
from findings_api.session_recovery import fail_stale_session, is_session_stale


def test_stale_ingest_session():
    session = AnalysisSession(
        id="s1",
        status="ingesting",
        phase="ingest",
        resource_ids=["a"],
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    assert is_session_stale(session) is True


def test_active_ingest_not_stale():
    session = AnalysisSession(
        id="s2",
        status="ingesting",
        phase="ingest",
        resource_ids=["a"],
        updated_at=datetime.now(timezone.utc),
    )
    assert is_session_stale(session) is False
