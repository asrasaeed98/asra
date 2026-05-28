"""Probe catalog URLs for ingestible tabular formats before indexing."""

from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import dataclass

import httpx

from findings_api.catalog.column_quality import score_columns
from findings_api.config import settings

logger = logging.getLogger(__name__)

INGESTIBLE_FORMATS = frozenset({"CSV", "JSON_RECORDS", "JSON_WORLDBANK", "JSON_API"})


@dataclass(frozen=True)
class ProbeResult:
    ingestible: bool
    reason: str
    detected_format: str | None = None
    columns: list[str] | None = None
    row_count: int | None = None


def _reject_if_bad_columns(columns: list[str], *, fmt: str, row_count: int | None) -> ProbeResult | None:
    ok, reason, _stats = score_columns(columns)
    if ok:
        return None
    return ProbeResult(False, reason, fmt, columns, row_count=row_count)


def _min_rows() -> int:
    return settings.catalog_min_rows


def _reject_if_too_few(row_count: int | None, *, context: str) -> ProbeResult | None:
    if row_count is None:
        return None
    if row_count < _min_rows():
        return ProbeResult(
            False,
            f"{context} has {row_count} row(s) — need at least {_min_rows()}",
            row_count=row_count,
        )
    return None


def probe_bytes(data: bytes, *, url: str = "", portal: str = "") -> ProbeResult:
    """Classify downloaded bytes without hitting the network."""
    if not data:
        return ProbeResult(False, "empty file", "EMPTY")

    if portal == "world_bank" or "api.worldbank.org" in url.lower():
        return _probe_worldbank_bytes(data)

    if portal == "fred" or "api.stlouisfed.org/fred/" in url.lower():
        return _probe_fred_bytes(data)

    head = data[:512].lstrip().lower()
    if head.startswith(b"<!doctype") or head.startswith(b"<html") or b"<head" in head[:200]:
        return ProbeResult(False, "HTML page, not a data file", "HTML")
    if data[:2] == b"PK":
        return ProbeResult(False, "ZIP archive — unpack not supported yet", "ZIP")

    kind = _guess_payload_kind(data, url)
    if kind == "json":
        return _probe_json(data)
    if kind == "csv":
        return _probe_csv(data)
    return ProbeResult(False, "unsupported or unrecognized format", "UNKNOWN")


async def probe_url(
    url: str,
    *,
    client: httpx.AsyncClient,
    portal: str = "",
) -> ProbeResult:
    """Download a sample and classify whether ingest can handle this URL."""
    if portal == "fred" or "api.stlouisfed.org/fred/" in url.lower():
        return await _probe_fred_url(url, client=client)

    if portal == "world_bank" or "api.worldbank.org" in url.lower():
        return await _probe_worldbank_url(url, client=client)

    max_bytes = settings.catalog_probe_max_bytes
    timeout = settings.catalog_probe_timeout_sec
    headers = {"Range": f"bytes=0-{max_bytes - 1}"}

    data: bytes | None = None
    for attempt, use_range in enumerate((True, False)):
        try:
            req_headers = headers if use_range else {}
            resp = await client.get(url, timeout=timeout, headers=req_headers)
            if resp.status_code not in (200, 206):
                if attempt == 0 and resp.status_code in (403, 404, 416, 501):
                    continue
                return ProbeResult(False, f"HTTP {resp.status_code}", "HTTP_ERROR")
            data = resp.content[:max_bytes]
            if len(resp.content) >= settings.max_download_bytes:
                return ProbeResult(False, "file exceeds download cap", "TOO_LARGE")
            break
        except httpx.HTTPError as exc:
            if attempt == 0:
                continue
            logger.debug("Probe failed for %s: %s", url, exc)
            return ProbeResult(False, f"download failed: {exc}", "HTTP_ERROR")

    if data is None:
        return ProbeResult(False, "download failed", "HTTP_ERROR")

    return probe_bytes(data, url=url, portal=portal)


def _probe_worldbank_bytes(data: bytes) -> ProbeResult:
    try:
        payload = json.loads(data.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return ProbeResult(False, "invalid World Bank JSON", "JSON_INVALID")

    if not isinstance(payload, list) or len(payload) < 2:
        return ProbeResult(False, "unsupported World Bank JSON shape", "JSON_NESTED")

    meta = payload[0] if isinstance(payload[0], dict) else {}
    rows = payload[1] if isinstance(payload[1], list) else []
    total = int(meta.get("total") or len(rows))
    too_few = _reject_if_too_few(total, context="World Bank indicator")
    if too_few:
        return too_few

    columns = [
        "countryiso3code",
        "country",
        "indicator_id",
        "indicator",
        "date",
        "value",
    ]
    return ProbeResult(
        True,
        f"World Bank API ({total} observations)",
        "JSON_WORLDBANK",
        columns,
        row_count=total,
    )


def _probe_fred_bytes(data: bytes) -> ProbeResult:
    try:
        payload = json.loads(data.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return ProbeResult(False, "invalid FRED JSON", "JSON_INVALID")

    if not isinstance(payload, dict):
        return ProbeResult(False, "unsupported FRED JSON shape", "JSON_NESTED")

    if payload.get("error_code"):
        return ProbeResult(False, payload.get("error_message") or "FRED API error", "HTTP_ERROR")

    total = int(payload.get("count") or 0)
    too_few = _reject_if_too_few(total, context="FRED series")
    if too_few:
        return too_few

    columns = ["date", "value", "series_id"]
    return ProbeResult(
        True,
        f"FRED observations ({total} points)",
        "JSON_FRED",
        columns,
        row_count=total,
    )


async def _probe_fred_url(url: str, *, client: httpx.AsyncClient) -> ProbeResult:
    from urllib.parse import parse_qs, urlparse

    from findings_api.config import settings

    if not settings.fred_api_key:
        return ProbeResult(False, "FRED_API_KEY not configured", "HTTP_ERROR")

    parsed = urlparse(url)
    params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    params["api_key"] = settings.fred_api_key
    params.setdefault("file_type", "json")
    params.setdefault("limit", "1000")

    try:
        resp = await client.get(
            f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
            params=params,
            timeout=settings.catalog_probe_timeout_sec,
        )
    except httpx.HTTPError as exc:
        return ProbeResult(False, f"FRED probe failed: {exc}", "HTTP_ERROR")

    if resp.status_code != 200:
        return ProbeResult(False, f"HTTP {resp.status_code}", "HTTP_ERROR")

    return _probe_fred_bytes(resp.content)


async def _probe_worldbank_url(url: str, *, client: httpx.AsyncClient) -> ProbeResult:
    probe_url_str = url
    if "page=" not in probe_url_str.lower():
        sep = "&" if "?" in probe_url_str else "?"
        probe_url_str = f"{probe_url_str}{sep}page=1"
    if "per_page=" not in probe_url_str.lower():
        sep = "&" if "?" in probe_url_str else "?"
        probe_url_str = f"{probe_url_str}{sep}per_page=500"

    try:
        resp = await client.get(probe_url_str, timeout=settings.catalog_probe_timeout_sec)
    except httpx.HTTPError as exc:
        return ProbeResult(False, f"World Bank probe failed: {exc}", "HTTP_ERROR")

    if resp.status_code != 200:
        return ProbeResult(False, f"HTTP {resp.status_code}", "HTTP_ERROR")

    return _probe_worldbank_bytes(resp.content)


def _guess_payload_kind(data: bytes, url: str) -> str:
    low_url = url.lower()
    head = data[:200].lstrip()
    if "json" in low_url or head.startswith((b"{", b"[")):
        return "json"
    if "csv" in low_url or (b"," in head and b"\n" in head):
        return "csv"
    if head.startswith((b"{", b"[")):
        return "json"
    if b"," in head and b"\n" in head:
        return "csv"
    return "unknown"


def _probe_json(data: bytes) -> ProbeResult:
    try:
        payload = json.loads(data.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return ProbeResult(False, "invalid JSON", "JSON_INVALID")

    if isinstance(payload, list) and len(payload) >= 2 and isinstance(payload[1], list):
        rows = payload[1]
        fmt = "JSON_WORLDBANK"
        row_count = len(rows)
    elif isinstance(payload, list):
        rows = payload
        fmt = "JSON_RECORDS"
        row_count = len(rows)
    elif isinstance(payload, dict):
        if payload.get("type") == "FeatureCollection":
            return ProbeResult(False, "GeoJSON not supported yet", "GEOJSON")
        rows = [payload]
        fmt = "JSON_RECORDS"
        row_count = 1
    else:
        return ProbeResult(False, "unsupported JSON shape", "JSON_NESTED")

    if not rows:
        return ProbeResult(False, "JSON has no rows", "EMPTY")

    first = rows[0]
    if not isinstance(first, dict):
        return ProbeResult(False, "JSON rows are not objects", "JSON_NESTED")

    columns = list(first.keys())
    if _has_nested_cells(first):
        if fmt == "JSON_WORLDBANK" or "indicator" in first or "country" in first:
            too_few = _reject_if_too_few(row_count, context="JSON dataset")
            if too_few:
                return too_few
            return ProbeResult(
                True,
                "nested JSON — flattened on ingest",
                "JSON_WORLDBANK",
                columns,
                row_count=row_count,
            )
        return ProbeResult(False, "nested JSON objects need a source adapter", "JSON_NESTED")

    if len(columns) < 2:
        return ProbeResult(False, "need at least 2 columns for analysis", "JSON_NESTED")

    too_few = _reject_if_too_few(row_count, context="JSON dataset")
    if too_few:
        return too_few

    bad_cols = _reject_if_bad_columns(columns, fmt=fmt, row_count=row_count)
    if bad_cols:
        return bad_cols

    return ProbeResult(True, "flat JSON records", fmt, columns, row_count=row_count)


def _probe_csv(data: bytes) -> ProbeResult:
    text = data.decode("utf-8", errors="replace")
    if not text.strip():
        return ProbeResult(False, "empty CSV", "EMPTY")

    try:
        reader = csv.reader(io.StringIO(text))
        header = next(reader, None)
        if not header or len(header) < 2:
            return ProbeResult(False, "CSV needs a header with 2+ columns", "CSV")
        row_count = sum(1 for _ in reader)
        if row_count == 0:
            return ProbeResult(False, "CSV has no data rows", "EMPTY")
    except csv.Error:
        return ProbeResult(False, "invalid CSV", "CSV")

    too_few = _reject_if_too_few(row_count, context="CSV sample")
    if too_few:
        if len(data) >= settings.catalog_probe_max_bytes - 1024:
            return ProbeResult(
                True,
                f"CSV tabular file (≥{row_count} rows in sample)",
                "CSV",
                header,
                row_count=row_count,
            )
        return too_few

    bad_cols = _reject_if_bad_columns(header, fmt="CSV", row_count=row_count)
    if bad_cols:
        return bad_cols

    return ProbeResult(True, "CSV tabular file", "CSV", header, row_count=row_count)


def _has_nested_cells(row: dict) -> bool:
    for value in row.values():
        if isinstance(value, (dict, list)):
            return True
    return False
