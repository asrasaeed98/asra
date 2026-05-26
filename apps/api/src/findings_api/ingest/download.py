"""Download catalog resources for ingest."""

from __future__ import annotations

import logging

import httpx

from findings_api.config import settings

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    pass


async def fetch_resource_bytes(url: str, *, client: httpx.AsyncClient | None = None) -> tuple[bytes, str]:
    """Return body and a coarse content kind: csv | json | unknown."""
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
