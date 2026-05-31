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


def test_fetch_socrata_json_paginates(monkeypatch):
    monkeypatch.setattr(settings, "socrata_download_chunk_rows", 2)
    monkeypatch.setattr(settings, "row_cap", 5)

    pages = [
        [{"a": 1}, {"a": 2}],
        [{"a": 3}],
    ]
    call_count = 0

    class FakeClient:
        async def post(self, *_args, **_kwargs):
            nonlocal call_count
            idx = call_count
            call_count += 1
            payload = pages[idx] if idx < len(pages) else []
            resp = MagicMock()
            resp.status_code = 200
            resp.content = json.dumps(payload).encode()
            return resp

    url = (
        "https://data.cityofnewyork.us/api/v3/views/abc/query.json"
        "?socrata_soql=SELECT+a+LIMIT+5"
    )
    data = asyncio.run(fetch_socrata_json(url, client=FakeClient()))
    rows = json.loads(data.decode())
    assert len(rows) == 3
    assert call_count == 2


def test_fetch_socrata_json_respects_byte_cap(monkeypatch):
    monkeypatch.setattr(settings, "socrata_download_chunk_rows", 1)
    monkeypatch.setattr(settings, "row_cap", 10)
    monkeypatch.setattr(settings, "max_download_bytes", 80)

    rows = [[{"payload": "x" * 50}], [{"payload": "y" * 50}]]

    class FakeClient:
        async def post(self, *_args, **_kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.content = json.dumps(rows.pop(0) if rows else []).encode()
            return resp

    url = (
        "https://data.cityofnewyork.us/api/v3/views/abc/query.json"
        "?socrata_soql=SELECT+payload+LIMIT+10"
    )
    data = asyncio.run(fetch_socrata_json(url, client=FakeClient()))
    loaded = json.loads(data.decode())
    assert len(loaded) == 1
