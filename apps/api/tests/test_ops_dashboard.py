from datetime import datetime, timedelta, timezone

from findings_api.db import Base, get_engine, get_session_factory
from findings_api.models import AnalysisSession, ApiUsage, CatalogResource
from findings_api.ops_dashboard import build_ops_dashboard


def _session(db, **kwargs):
    defaults = {
        "id": "sess-1",
        "status": "complete",
        "phase": "finalize",
        "resource_ids": ["wb:NY.GDP.MKTP.CD"],
        "user_intent": "Explore GDP",
        "created_at": datetime.now(timezone.utc) - timedelta(days=1),
        "updated_at": datetime.now(timezone.utc) - timedelta(days=1) + timedelta(seconds=42),
    }
    defaults.update(kwargs)
    row = AnalysisSession(**defaults)
    db.add(row)
    db.commit()
    return row


def test_build_ops_dashboard_aggregates():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    factory = get_session_factory()
    db = factory()
    try:
        db.add(
            CatalogResource(
                id="wb:NY.GDP.MKTP.CD",
                portal="worldbank",
                title="GDP",
                license_normalized="open",
                license_display="Open",
                attribution_required=False,
                attribution_text="WB",
                publisher="WB",
                source_url="https://example.com",
                search_text="gdp",
                ingestible=True,
            )
        )
        _session(db, id="s1")
        _session(
            db,
            id="s2",
            status="failed",
            error="timeout",
            resource_ids=["wb:NY.GDP.MKTP.CD", "wb:SP.POP.TOTL"],
            user_intent=None,
        )
        db.add(
            ApiUsage(
                month="2026-06",
                tokens_in=100,
                tokens_out=10,
                cost_usd=0.01,
                calls=1,
            )
        )
        db.commit()

        out = build_ops_dashboard(db, limit=10, days=30)
        assert out["sessions"]["total_all_time"] == 2
        assert out["sessions"]["by_status"]["complete"] == 1
        assert out["sessions"]["by_status"]["failed"] == 1
        assert out["top_datasets"][0]["uses"] >= 2
        assert out["api_usage"][0]["month"] == "2026-06"
        assert out["limitations"]["users"]
    finally:
        db.close()
