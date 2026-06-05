"""Tests for resilient downloads: retry/backoff, partial WB pagination, secret redaction."""

import asyncio
import json

import httpx
import pytest

from findings_api.config import settings
from findings_api.ingest.download import (
    DownloadError,
    fetch_fred_json,
    fetch_worldbank_json,
    redact_secrets,
)

FRED_KEY = "8c4080208e08e69b851ef78ee8617931"


@pytest.fixture(autouse=True)
def _fast_backoff(monkeypatch):
    """Avoid real sleeping during retry tests."""
    monkeypatch.setattr(settings, "download_backoff_base_sec", 0.0)
    monkeypatch.setattr(settings, "download_max_retries", 3)


def _run(coro):
    return asyncio.run(coro)


async def _with_client(handler, fn):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return await fn(client)


# --- redaction -------------------------------------------------------------


def test_redact_secrets_strips_keys_and_tokens():
    raw = (
        "Server error '502' for url "
        "'https://api.stlouisfed.org/fred/series/observations?"
        f"series_id=HOUST&api_key={FRED_KEY}&token=abc123'"
    )
    cleaned = redact_secrets(raw)
    assert FRED_KEY not in cleaned
    assert "abc123" not in cleaned
    assert "api_key=REDACTED" in cleaned
    assert "token=REDACTED" in cleaned
    assert "series_id=HOUST" in cleaned


# --- FRED resilience -------------------------------------------------------


def test_fred_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(settings, "fred_api_key", FRED_KEY)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(502, text="Bad Gateway")
        return httpx.Response(200, json={"observations": [{"date": "2020-01-01", "value": "1.0"}]})

    data = _run(
        _with_client(
            handler,
            lambda c: fetch_fred_json(
                "https://api.stlouisfed.org/fred/series/observations?series_id=HOUST",
                client=c,
            ),
        )
    )
    assert calls["n"] == 2
    assert json.loads(data)["observations"]


def test_fred_persistent_5xx_gives_friendly_error_without_key(monkeypatch):
    monkeypatch.setattr(settings, "fred_api_key", FRED_KEY)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(504, text="Gateway Timeout")

    with pytest.raises(DownloadError) as exc:
        _run(
            _with_client(
                handler,
                lambda c: fetch_fred_json(
                    "https://api.stlouisfed.org/fred/series/observations?series_id=HOUST",
                    client=c,
                ),
            )
        )
    message = str(exc.value)
    assert FRED_KEY not in message
    assert "temporarily unavailable" in message
    assert "504" in message


def test_fred_network_error_retried_then_friendly(monkeypatch):
    monkeypatch.setattr(settings, "fred_api_key", FRED_KEY)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectTimeout("connection timed out", request=request)

    with pytest.raises(DownloadError) as exc:
        _run(
            _with_client(
                handler,
                lambda c: fetch_fred_json(
                    "https://api.stlouisfed.org/fred/series/observations?series_id=HOUST",
                    client=c,
                ),
            )
        )
    assert calls["n"] == settings.download_max_retries
    assert FRED_KEY not in str(exc.value)
    assert "temporarily unavailable" in str(exc.value)


# --- World Bank pagination -------------------------------------------------


def _wb_handler(page_responses):
    """Return a handler that maps the ``page`` query param to a response."""

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        return page_responses(page)

    return handler


def test_worldbank_partial_data_on_deep_page_400():
    def responses(page: int) -> httpx.Response:
        if page == 1:
            return httpx.Response(200, json=[{"pages": 3, "page": 1}, [{"value": 1}, {"value": 2}]])
        return httpx.Response(400, text="Bad Request")

    data = _run(
        _with_client(
            _wb_handler(responses),
            lambda c: fetch_worldbank_json(
                "https://api.worldbank.org/v2/country/all/indicator/EG.CFT.ACCS.RU.ZS",
                client=c,
            ),
        )
    )
    meta, rows = json.loads(data)
    assert len(rows) == 2  # page 1 retained, deep-page 400 tolerated


def test_worldbank_page1_400_is_fatal():
    def responses(page: int) -> httpx.Response:
        return httpx.Response(400, text="Bad Request")

    with pytest.raises(DownloadError) as exc:
        _run(
            _with_client(
                _wb_handler(responses),
                lambda c: fetch_worldbank_json(
                    "https://api.worldbank.org/v2/country/all/indicator/BAD",
                    client=c,
                ),
            )
        )
    assert "World Bank" in str(exc.value)
    assert "400" in str(exc.value)


def test_worldbank_stops_at_row_cap(monkeypatch):
    monkeypatch.setattr(settings, "row_cap", 3)
    monkeypatch.setattr(settings, "wb_download_per_page", 2)

    def responses(page: int) -> httpx.Response:
        return httpx.Response(
            200,
            json=[{"pages": 5, "page": page, "total": 10}, [{"value": page}, {"value": page + 1}]],
        )

    data = _run(
        _with_client(
            _wb_handler(responses),
            lambda c: fetch_worldbank_json(
                "https://api.worldbank.org/v2/country/all/indicator/CAP",
                client=c,
            ),
        )
    )
    _meta, rows = json.loads(data)
    assert len(rows) == 3


def test_worldbank_uses_settings_per_page_param():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params.get("per_page", ""))
        return httpx.Response(200, json=[{"pages": 1, "page": 1, "total": 1}, [{"value": 1}]])

    _run(
        _with_client(
            handler,
            lambda c: fetch_worldbank_json(
                "https://api.worldbank.org/v2/country/all/indicator/OK",
                client=c,
            ),
        )
    )
    assert seen == [str(settings.wb_download_per_page)]


def test_worldbank_ignores_per_page_in_catalog_url(monkeypatch):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params.get("per_page", ""))
        return httpx.Response(200, json=[{"pages": 1, "page": 1, "total": 1}, [{"value": 1}]])

    monkeypatch.setattr(settings, "wb_download_per_page", 500)
    _run(
        _with_client(
            handler,
            lambda c: fetch_worldbank_json(
                "https://api.worldbank.org/v2/country/all/indicator/OK?format=json&per_page=10000",
                client=c,
            ),
        )
    )
    assert seen == ["500"]


def test_worldbank_falls_back_to_smaller_per_page_on_page1_502(monkeypatch):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        per_page = request.url.params.get("per_page", "")
        seen.append(per_page)
        if per_page == "20000":
            return httpx.Response(502, text="Bad Gateway")
        return httpx.Response(200, json=[{"pages": 1, "page": 1, "total": 1}, [{"value": 1}]])

    monkeypatch.setattr(settings, "wb_download_per_page", 20000)
    monkeypatch.setattr(settings, "wb_download_max_retries", 1)
    data = _run(
        _with_client(
            handler,
            lambda c: fetch_worldbank_json(
                "https://api.worldbank.org/v2/country/all/indicator/OK",
                client=c,
            ),
        )
    )
    _meta, rows = json.loads(data)
    assert len(rows) == 1
    assert seen[0] == "20000"
    assert "10000" in seen


def test_worldbank_transient_5xx_retried_then_paginates():
    calls = {"n": 0}

    def responses(page: int) -> httpx.Response:
        if page == 1:
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(503, text="Service Unavailable")
            return httpx.Response(200, json=[{"pages": 1, "page": 1}, [{"value": 1}]])
        return httpx.Response(200, json=[{"pages": 1}, []])

    data = _run(
        _with_client(
            _wb_handler(responses),
            lambda c: fetch_worldbank_json(
                "https://api.worldbank.org/v2/country/all/indicator/OK",
                client=c,
            ),
        )
    )
    meta, rows = json.loads(data)
    assert calls["n"] == 2
    assert len(rows) == 1
