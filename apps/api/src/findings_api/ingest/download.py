"""Download catalog resources for ingest."""

from __future__ import annotations

import asyncio
import json
import logging
import re

import httpx

from findings_api.config import settings

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    pass


# Query params that must never appear in logs or user-facing error messages.
_SENSITIVE_PARAMS = {"api_key", "apikey", "key", "token", "access_token"}
_SECRET_PATTERN = re.compile(
    r"(?i)\b(api_key|apikey|key|token|access_token)=[^&\s'\"]+"
)
# Upstream/transient HTTP statuses that are worth retrying.
_RETRY_STATUS = {429, 500, 502, 503, 504}


def redact_secrets(message: str) -> str:
    """Strip API keys / tokens from arbitrary text (URLs, exception strings)."""
    return _SECRET_PATTERN.sub(r"\1=REDACTED", message)


def _friendly_http_error(source: str, status: int) -> str:
    """Map an upstream HTTP status to a clean, secret-free user message."""
    if status in (502, 503, 504):
        return f"{source} is temporarily unavailable (HTTP {status}). Please try again shortly."
    if status == 429:
        return f"{source} rate limit reached (HTTP {status}). Please try again shortly."
    if status == 500:
        return f"{source} had a server error (HTTP {status}). Please try again shortly."
    if 400 <= status < 500:
        return f"{source} rejected the request (HTTP {status})."
    return f"{source} returned an unexpected response (HTTP {status})."


def _backoff_seconds(attempt: int) -> float:
    """Exponential backoff: base, 2*base, 4*base, … for attempt 1, 2, 3…"""
    return settings.download_backoff_base_sec * (2 ** (attempt - 1))


async def _get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    source: str,
    params: dict | None = None,
    timeout: float = 120.0,
) -> httpx.Response:
    """GET with retry/backoff on transient errors.

    Retries network/timeout errors and retryable HTTP statuses (429/5xx).
    Raises a sanitized ``DownloadError`` if every attempt fails at the
    network level. Otherwise returns the final response (the caller decides
    how to handle its status code).
    """
    attempts = max(1, settings.download_max_retries)
    last_exc: Exception | None = None
    resp: httpx.Response | None = None

    for attempt in range(1, attempts + 1):
        try:
            resp = await client.get(url, params=params, timeout=timeout)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
            resp = None
            logger.warning(
                "%s request failed (attempt %s/%s): %s",
                source,
                attempt,
                attempts,
                redact_secrets(str(exc)),
            )
            if attempt < attempts:
                await asyncio.sleep(_backoff_seconds(attempt))
                continue
            break

        if resp.status_code in _RETRY_STATUS and attempt < attempts:
            logger.warning(
                "%s returned HTTP %s (attempt %s/%s); retrying",
                source,
                resp.status_code,
                attempt,
                attempts,
            )
            await asyncio.sleep(_backoff_seconds(attempt))
            continue

        return resp

    if resp is not None:
        return resp
    raise DownloadError(
        f"{source} is temporarily unavailable (network error after {attempts} attempts). "
        "Please try again shortly."
    ) from last_exc


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
        resp = await _get_with_retry(client, url, source="The data source")
        if resp.status_code >= 400:
            raise DownloadError(_friendly_http_error("The data source", resp.status_code))
        data = resp.content
        if len(data) > settings.max_download_bytes:
            raise DownloadError(
                f"Download exceeds {settings.max_download_bytes // 1_000_000}MB cap"
            )
        kind = _guess_kind(url, resp.headers.get("content-type"), data)
        return data, kind
    except httpx.HTTPError as exc:
        raise DownloadError(redact_secrets(str(exc))) from exc
    finally:
        if owns_client:
            await client.aclose()


async def fetch_worldbank_json(url: str, *, client: httpx.AsyncClient | None = None) -> bytes:
    """Paginate World Bank indicator API until all rows are fetched (within caps).

    Resilient pagination: each page is retried on transient failures. If a
    page beyond the first fails after retries (or returns a 4xx, which the WB
    API sometimes does on deep pages) we keep whatever rows we already have
    and return partial data instead of failing the whole download. Only a
    failure on page 1 (or an empty result) is treated as fatal.
    """
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
            try:
                resp = await _get_with_retry(client, base_url, source="World Bank", params=params)
            except DownloadError:
                if all_rows:
                    logger.warning(
                        "World Bank pagination stopped at page %s (network error); "
                        "returning %s partial rows",
                        page,
                        len(all_rows),
                    )
                    break
                raise

            if resp.status_code >= 400:
                if page == 1 or not all_rows:
                    raise DownloadError(_friendly_http_error("World Bank", resp.status_code))
                logger.warning(
                    "World Bank pagination stopped at page %s (HTTP %s); "
                    "returning %s partial rows",
                    page,
                    resp.status_code,
                    len(all_rows),
                )
                break

            try:
                payload = resp.json()
            except (json.JSONDecodeError, ValueError):
                if all_rows:
                    logger.warning(
                        "World Bank page %s returned invalid JSON; returning %s partial rows",
                        page,
                        len(all_rows),
                    )
                    break
                raise DownloadError("World Bank returned an invalid response.")

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
        raise DownloadError(redact_secrets(str(exc))) from exc
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
        resp = await _get_with_retry(
            client,
            f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
            source="FRED",
            params=params,
        )
        if resp.status_code >= 400:
            raise DownloadError(_friendly_http_error("FRED", resp.status_code))
        data = resp.content
        if len(data) > settings.max_download_bytes:
            raise DownloadError(
                f"Download exceeds {settings.max_download_bytes // 1_000_000}MB cap"
            )
        payload = json.loads(data.decode("utf-8"))
        if payload.get("error_code"):
            raise DownloadError(
                redact_secrets(payload.get("error_message") or "FRED API error")
            )
        return data
    except httpx.HTTPError as exc:
        raise DownloadError(redact_secrets(str(exc))) from exc
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
