"""Download catalog resources for ingest."""

from __future__ import annotations

import json
import logging

import httpx

from findings_api.config import settings

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    pass


async def fetch_resource_bytes(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    portal: str = "",
) -> tuple[bytes, str]:
    """Return body and a coarse content kind: csv | json | unknown."""
    if portal == "fred" or "api.stlouisfed.org/fred/" in url.lower():
        return await fetch_fred_json(url, client=client), "json"

    if portal == "world_bank" or "api.worldbank.org" in url.lower():
        return await fetch_worldbank_json(url, client=client), "json"

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(follow_redirects=True, trust_env=False)
    try:
        resp = await client.get(url, timeout=120.0)
        resp.raise_for_status()
        data = resp.content
        if len(data) > settings.max_download_bytes:
            raise DownloadError(
                f"Download exceeds {settings.max_download_bytes // 1_000_000}MB cap"
            )
        kind = _guess_kind(url, resp.headers.get("content-type"), data)
        return data, kind
    except httpx.HTTPError as exc:
        raise DownloadError(str(exc)) from exc
    finally:
        if owns_client:
            await client.aclose()


async def fetch_worldbank_json(url: str, *, client: httpx.AsyncClient | None = None) -> bytes:
    """Paginate World Bank indicator API until all rows are fetched (within caps)."""
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(follow_redirects=True, trust_env=False)

    base_url = url.split("?")[0]
    params: dict[str, str | int] = {"format": "json", "per_page": 500}
    if "?" in url:
        for part in url.split("?", 1)[1].split("&"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            if key.lower() in {"format", "page"}:
                continue
            params[key] = value

    all_rows: list[dict] = []
    meta: dict = {}
    page = 1
    max_pages = 80

    try:
        while page <= max_pages:
            params["page"] = page
            resp = await client.get(base_url, params=params, timeout=120.0)
            resp.raise_for_status()
            payload = resp.json()
            if not isinstance(payload, list) or len(payload) < 2:
                break
            meta = payload[0] if isinstance(payload[0], dict) else {}
            rows = payload[1] if isinstance(payload[1], list) else []
            if not rows:
                break
            all_rows.extend(rows)
            total_pages = int(meta.get("pages") or 1)
            if page >= total_pages:
                break
            page += 1

            encoded = json.dumps([meta, all_rows]).encode("utf-8")
            if len(encoded) > settings.max_download_bytes:
                logger.warning(
                    "World Bank download truncated at %s rows due to byte cap",
                    len(all_rows),
                )
                break
    except httpx.HTTPError as exc:
        raise DownloadError(str(exc)) from exc
    finally:
        if owns_client:
            await client.aclose()

    if not all_rows:
        raise DownloadError("World Bank indicator returned no data rows")

    return json.dumps([meta, all_rows]).encode("utf-8")


async def fetch_fred_json(url: str, *, client: httpx.AsyncClient | None = None) -> bytes:
    """Download FRED series observations (single request up to API limit)."""
    from urllib.parse import parse_qs, urlparse

    if not settings.fred_api_key:
        raise DownloadError("FRED_API_KEY not configured")

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(follow_redirects=True, trust_env=False)

    parsed = urlparse(url)
    params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    params["api_key"] = settings.fred_api_key
    params.setdefault("file_type", "json")
    params.setdefault("limit", "100000")

    try:
        resp = await client.get(
            f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
            params=params,
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.content
        if len(data) > settings.max_download_bytes:
            raise DownloadError(
                f"Download exceeds {settings.max_download_bytes // 1_000_000}MB cap"
            )
        payload = json.loads(data.decode("utf-8"))
        if payload.get("error_code"):
            raise DownloadError(payload.get("error_message") or "FRED API error")
        return data
    except httpx.HTTPError as exc:
        raise DownloadError(str(exc)) from exc
    finally:
        if owns_client:
            await client.aclose()


def _guess_kind(url: str, content_type: str | None, data: bytes) -> str:
    low_url = url.lower()
    ct = (content_type or "").lower()
    if "csv" in low_url or "text/csv" in ct or "text/plain" in ct:
        return "csv"
    if "json" in low_url or "application/json" in ct:
        return "json"
    head = data[:200].lstrip()
    if head.startswith(b"{") or head.startswith(b"["):
        return "json"
    if b"," in head and b"\n" in head:
        return "csv"
    return "unknown"
