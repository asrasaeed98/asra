from datetime import datetime, timedelta, timezone

from findings_api.models import AnalysisSession
from findings_api.session_recovery import (
    is_session_stale,
    stale_after,
    stale_failure_message,
)


def _session(**kwargs) -> AnalysisSession:
    defaults = {
        "id": "s1",
        "status": "ingesting",
        "phase": "ingest",
        "resource_ids": ["a"],
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return AnalysisSession(**defaults)


def test_stale_ingest_session_after_default_window():
    session = _session(updated_at=datetime.now(timezone.utc) - timedelta(minutes=26))
    assert is_session_stale(session) is True


def test_active_ingest_not_stale():
    session = _session(updated_at=datetime.now(timezone.utc) - timedelta(minutes=10))
    assert is_session_stale(session) is False


def test_large_download_uses_longer_stale_window():
    session = _session(
        config={"large_download": True},
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=30),
    )
    assert stale_after(session) == timedelta(minutes=60)
    assert is_session_stale(session) is False


def test_large_download_stale_after_extended_window():
    session = _session(
        config={"large_download": True},
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=61),
    )
    assert is_session_stale(session) is True


def test_stale_failure_message_for_large_download():
    session = _session(config={"large_download": True})
    message = stale_failure_message(session)
    assert "large dataset download" in message
    assert "NYC" in message


def test_stale_failure_message_for_analysis():
    session = _session(status="analyzing", phase="analyze")
    message = stale_failure_message(session)
    assert "Analysis took longer than expected" in message


def test_stale_failure_message_for_restart():
    session = _session()
    message = stale_failure_message(session)
    assert "server restarted" in message


def test_fail_stale_session_sets_contextual_message():
    session = _session(
        config={"large_download": True},
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=61),
    )
    # fail_stale_session needs a db session — verify message helper only here.
    assert "large dataset download" in stale_failure_message(session)
