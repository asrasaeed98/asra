from datetime import datetime, timedelta, timezone

from findings_api.db import Base, get_engine, get_session_factory
from findings_api.models import AnalysisSession, AppVisit
from findings_api.visitor_metrics import build_visitor_metrics


def test_build_visitor_metrics_counts_unique_visitors():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    factory = get_session_factory()
    db = factory()
    try:
        now = datetime.now(timezone.utc)
        db.add_all(
            [
                AppVisit(visitor_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", path="/"),
                AppVisit(visitor_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", path="/search"),
                AppVisit(visitor_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", path="/explore"),
            ]
        )
        db.add(
            AnalysisSession(
                id="sess-1",
                visitor_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                status="created",
                phase="pending",
                resource_ids=["wb:1"],
                created_at=now - timedelta(days=1),
                updated_at=now - timedelta(days=1),
            )
        )
        db.commit()

        out = build_visitor_metrics(db, days=30)
        assert out["total_page_views"] == 3
        assert out["unique_visitors_all_time"] == 2
        assert out["unique_visitors_in_window"] == 2
        assert out["unique_visitors_with_analysis"] == 1
        assert len(out["daily_unique_visitors"]) >= 1
    finally:
        db.close()
