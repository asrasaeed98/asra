"""Download policy and chunked Socrata ingest."""

import asyncio
import json
from unittest.mock import MagicMock

import pytest

from findings_api.catalog.socrata import page_soql, split_soql_limit
from findings_api.config import settings
from findings_api.ingest.download import DownloadError, fetch_socrata_json
from findings_api.ingest.download_policy import (
    is_large_download,
    large_download_start_message,
    resource_is_large,
)
from findings_api.models import CatalogResource


def test_split_soql_limit():
    base, lim = split_soql_limit("SELECT a, b LIMIT 100000")
    assert base == "SELECT a, b"
    assert lim == 100_000
    assert page_soql(base, limit=5000, offset=10000) == "SELECT a, b LIMIT 5000 OFFSET 10000"


def test_is_large_download_nyc():
    assert is_large_download(portal="nyc_open_data", row_count_hint=296_393) is True
    assert is_large_download(portal="nyc_open_data", row_count_hint=5_000) is False


def test_large_download_start_message():
    msg = large_download_start_message(
        title="Restaurant Inspections",
        row_count_hint=296_393,
        portal="nyc_open_data",
    )
    assert "2–5 minutes" in msg
    assert "100" in msg
    assert "296,393" in msg


def test_resource_is_large():
    rec = CatalogResource(
        id="nyc:x",
        portal="nyc_open_data",
        title="Test",
        license_normalized="US_GOV_WORK",
        license_display="",
        attribution_required=False,
        attribution_text="",
        publisher="NYC",
        source_url="https://example.com",
        search_text="test",
        row_count_hint=80_000,
    )
    assert resource_is_large(rec) is True


def _make_offset_client(data_by_offset: dict[int, list], *, calls: list | None = None):
    """FakeClient that dispatches by $offset so parallel chunks work correctly."""

    class _FakeClient:
        async def get(self, url, *, params=None, timeout=None, headers=None):
            offset = int((params or {}).get("$offset", 0))
            if calls is not None:
                calls.append({"url": url, "params": dict(params or {})})
            payload = data_by_offset.get(offset, [])
            resp = MagicMock()
            resp.status_code = 200
            resp.content = json.dumps(payload).encode()
            return resp

    return _FakeClient()


def test_fetch_socrata_json_paginates(monkeypatch):
    monkeypatch.setattr(settings, "socrata_download_chunk_rows", 2)
    monkeypatch.setattr(settings, "row_cap", 5)
    monkeypatch.setattr(settings, "socrata_concurrent_chunks", 3)

    data_by_offset = {
        0: [{"a": 1}, {"a": 2}],
        2: [{"a": 3}],
        4: [],  # end-of-data sentinel
    }
    calls: list[dict] = []

    url = (
        "https://data.cityofnewyork.us/api/v3/views/abc/query.json"
        "?socrata_soql=SELECT+a+LIMIT+5"
    )
    data = asyncio.run(fetch_socrata_json(url, client=_make_offset_client(data_by_offset, calls=calls)))
    rows = json.loads(data.decode())
    assert len(rows) == 3
    # All planned offsets (0, 2, 4) are fetched in one parallel wave.
    offsets_seen = {c["params"]["$offset"] for c in calls}
    assert 0 in offsets_seen
    assert 2 in offsets_seen
    # SODA2 GET endpoint and $select forwarded.
    assert all(c["url"] == "https://data.cityofnewyork.us/resource/abc.json" for c in calls)
    assert all(c["params"].get("$select") == "a" for c in calls)


def test_fetch_socrata_json_respects_byte_cap(monkeypatch):
    monkeypatch.setattr(settings, "socrata_download_chunk_rows", 1)
    monkeypatch.setattr(settings, "row_cap", 3)
    monkeypatch.setattr(settings, "max_download_bytes", 80)
    monkeypatch.setattr(settings, "socrata_concurrent_chunks", 3)

    # Each row is ~55 bytes serialised; 3 rows together exceed the 80-byte cap.
    data_by_offset = {
        0: [{"payload": "x" * 40}],
        1: [{"payload": "y" * 40}],
        2: [{"payload": "z" * 40}],
    }

    url = (
        "https://data.cityofnewyork.us/api/v3/views/abc/query.json"
        "?socrata_soql=SELECT+payload+LIMIT+3"
    )
    data = asyncio.run(fetch_socrata_json(url, client=_make_offset_client(data_by_offset)))
    loaded = json.loads(data.decode())
    assert len(loaded) < 3
    assert len(json.dumps(loaded).encode()) <= 80


def test_fetch_socrata_json_partial_on_chunk_failure(monkeypatch):
    """Later-chunk failure returns partial rows instead of raising."""
    monkeypatch.setattr(settings, "socrata_download_chunk_rows", 2)
    monkeypatch.setattr(settings, "row_cap", 6)
    monkeypatch.setattr(settings, "socrata_concurrent_chunks", 3)

    class FailingClient:
        async def get(self, url, *, params=None, timeout=None, headers=None):
            offset = int((params or {}).get("$offset", 0))
            resp = MagicMock()
            if offset == 0:
                resp.status_code = 200
                resp.content = json.dumps([{"a": 1}, {"a": 2}]).encode()
            else:
                resp.status_code = 500
                resp.content = b"error"
            return resp

    url = (
        "https://data.cityofnewyork.us/api/v3/views/abc/query.json"
        "?socrata_soql=SELECT+a+LIMIT+6"
    )
    data = asyncio.run(fetch_socrata_json(url, client=FailingClient()))
    rows = json.loads(data.decode())
    # First chunk succeeded, later ones failed — partial result returned.
    assert len(rows) == 2
