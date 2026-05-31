"""Tests for catalog sync limit helpers."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from findings_api import models  # noqa: F401
from findings_api.catalog.sync_limits import (
    build_search_text,
    clamp_str,
    max_indexed,
    prune_stale_portal_rows,
    should_probe,
)
from findings_api.config import settings
from findings_api.db import Base
from findings_api.models import CatalogResource


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_max_indexed_defaults_to_ingestible_cap():
    assert max_indexed(200, 0) == 200
    assert max_indexed(200, 500) == 500


def test_should_probe_respects_cap_and_setting(monkeypatch):
    monkeypatch.setattr(settings, "catalog_probe_enabled", True)
    assert should_probe(ingestible=0, ingestible_cap=200) is True
    assert should_probe(ingestible=200, ingestible_cap=200) is False
    monkeypatch.setattr(settings, "catalog_probe_enabled", False)
    assert should_probe(ingestible=0, ingestible_cap=200) is False


def test_build_search_text_caps_index_size():
    long_desc = "word " * 2000
    text = build_search_text("title", long_desc, "org", ["tag"])
    assert len(text.encode("utf-8")) <= 2500


def test_clamp_str_truncates():
    assert clamp_str("x" * 600, 512) == "x" * 512
    assert clamp_str("short", 512) == "short"


def _row(row_id: str, title: str, search_text: str, *, now: datetime) -> CatalogResource:
    return CatalogResource(
        id=row_id,
        portal="data_gov",
        title=title,
        format="CSV",
        license_normalized="CC0",
        license_display="CC0",
        attribution_text="test",
        publisher="test",
        source_url="https://example.com",
        resource_url="https://example.com/data.csv",
        updated_at=now,
        search_text=search_text,
    )


def test_prune_stale_portal_rows_keeps_unseen_prefixes(db_session):
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            _row("datagov:a", "A", "a", now=now),
            _row("datagov:b", "B", "b", now=now),
            _row("ckan:pkg:1", "C", "c", now=now),
        ]
    )
    db_session.commit()

    pruned = prune_stale_portal_rows(
        db_session,
        "data_gov",
        {"datagov:a"},
        id_prefix="datagov:",
    )
    db_session.commit()

    assert pruned == 1
    remaining = {r.id for r in db_session.query(CatalogResource).all()}
    assert remaining == {"datagov:a", "ckan:pkg:1"}
