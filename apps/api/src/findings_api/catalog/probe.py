"""Probe catalog URLs for ingestible tabular formats before indexing."""

from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import dataclass

import httpx

from findings_api.config import settings

logger = logging.getLogger(__name__)

INGESTIBLE_FORMATS = frozenset({"CSV", "JSON_RECORDS", "JSON_WORLDBANK", "JSON_API"})


@dataclass(frozen=True)
class ProbeResult:
    ingestible: bool
    reason: str
    detected_format: str | None = None
    columns: list[str] | None = None


def probe_bytes(data: bytes, *, url: str = "", portal: str = "") -> ProbeResult:
    """Classify downloaded bytes without hitting the network."""
    if not data:
        return ProbeResult(False, "empty file", "EMPTY")

    if portal == "world_bank" or "api.worldbank.org" in url.lower():
        return ProbeResult(True, "World Bank API (normalized on ingest)", "JSON_WORLDBANK")

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
    if portal == "world_bank" or "api.worldbank.org" in url.lower():
        return ProbeResult(True, "World Bank API (normalized on ingest)", "JSON_WORLDBANK")

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
    elif isinstance(payload, list):
        rows = payload
        fmt = "JSON_RECORDS"
    elif isinstance(payload, dict):
        if payload.get("type") == "FeatureCollection":
            return ProbeResult(False, "GeoJSON not supported yet", "GEOJSON")
        rows = [payload]
        fmt = "JSON_RECORDS"
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
            return ProbeResult(
                True,
                "nested JSON — flattened on ingest",
                "JSON_WORLDBANK",
                columns,
            )
        return ProbeResult(False, "nested JSON objects need a source adapter", "JSON_NESTED")

    if len(columns) < 2:
        return ProbeResult(False, "need at least 2 columns for analysis", "JSON_NESTED")

    return ProbeResult(True, "flat JSON records", fmt, columns)


def _probe_csv(data: bytes) -> ProbeResult:
    text = data.decode("utf-8", errors="replace")
    if not text.strip():
        return ProbeResult(False, "empty CSV", "EMPTY")

    try:
        reader = csv.reader(io.StringIO(text))
        header = next(reader, None)
        if not header or len(header) < 2:
            return ProbeResult(False, "CSV needs a header with 2+ columns", "CSV")
        row = next(reader, None)
        if not row:
            return ProbeResult(False, "CSV has no data rows", "EMPTY")
    except csv.Error:
        return ProbeResult(False, "invalid CSV", "CSV")

    return ProbeResult(True, "CSV tabular file", "CSV", header)


def _has_nested_cells(row: dict) -> bool:
    for value in row.values():
        if isinstance(value, (dict, list)):
            return True
    return False
