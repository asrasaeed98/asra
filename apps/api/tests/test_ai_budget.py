"""Monthly AI budget ledger + graceful chat degradation."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from findings_api import models  # noqa: F401 — register tables
from findings_api.analysis import ai_usage
from findings_api.config import settings
from findings_api.db import Base


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_estimate_cost_uses_model_pricing():
    assert round(ai_usage.estimate_cost("claude-sonnet-4-6", 1_000_000, 1_000_000), 4) == 18.0
    assert round(ai_usage.estimate_cost("claude-haiku-4-5", 1_000_000, 1_000_000), 4) == 6.0


def test_record_usage_accumulates_and_budget_trips(monkeypatch):
    db = _session()
    monkeypatch.setattr(settings, "ai_monthly_budget_usd", 0.01)
    assert ai_usage.is_over_budget(db) is False
    ai_usage.record_usage(db, "claude-sonnet-4-6", 2300, 250)  # ~$0.0107
    assert ai_usage.current_month_cost(db) > 0
    assert ai_usage.is_over_budget(db) is True


def test_budget_cap_of_zero_disables_guard(monkeypatch):
    db = _session()
    monkeypatch.setattr(settings, "ai_monthly_budget_usd", 0)
    ai_usage.record_usage(db, "claude-sonnet-4-6", 10_000_000, 10_000_000)
    assert ai_usage.is_over_budget(db) is False


def test_record_usage_ignores_zero_token_calls():
    db = _session()
    ai_usage.record_usage(db, "claude-sonnet-4-6", 0, 0)
    assert ai_usage.current_month_cost(db) == 0.0


def test_chat_endpoint_degrades_gracefully_when_over_budget(client, monkeypatch):
    from findings_api.db import get_session_factory
    from findings_api.models import AnalysisSession

    factory = get_session_factory()
    db = factory()
    db.add(
        AnalysisSession(
            id="sess-budget",
            status="complete",
            phase="done",
            percent=100,
            resource_ids=["test:1"],
            config={},
            preview={"results": {"findings": [], "ai_summary": "Summary text"}},
        )
    )
    db.commit()
    monkeypatch.setattr(settings, "ai_monthly_budget_usd", 0.0001)
    ai_usage.record_usage(db, "claude-sonnet-4-6", 2300, 250)
    db.close()

    res = client.post("/sessions/sess-budget/chat", json={"message": "What's the trend?"})
    assert res.status_code == 200
    body = res.json()
    assert "run out of AI budget" in body["reply"]
    assert body["ai_paused"] is True
    assert body["questions_used"] == 0
    assert body["questions_remaining"] == settings.chat_max_questions
