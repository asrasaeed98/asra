"""Download catalog resources for ingest."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Callable

import httpx

from findings_api.catalog.socrata import (
    is_socrata_query_url,
    page_soql,
    parse_query_url,
    split_soql_limit,
)
from findings_api.config import settings

logger = logging.getLogger(__name__)

DownloadProgressCallback = Callable[[str], None]
HeartbeatCallback = Callable[[], None]


class DownloadError(Exception):
    pass


def _raise_download_too_large(received_bytes: int) -> None:
    cap_mb = settings.max_download_bytes // 1_000_000
    received_mb = received_bytes / 1_000_000
    raise DownloadError(
        f"Download exceeds the {cap_mb}MB safety limit ({received_mb:.1f}MB received). "
        "Try a smaller dataset or fewer columns."
    )


def _check_download_size(data: bytes) -> None:
    if len(data) > settings.max_download_bytes:
        _raise_download_too_large(len(data))


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
    on_heartbeat: HeartbeatCallback | None = None,
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
                if on_heartbeat:
                    on_heartbeat()
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
            if on_heartbeat:
                on_heartbeat()
            await asyncio.sleep(_backoff_seconds(attempt))
            continue

        return resp

    if resp is not None:
        return resp
    raise DownloadError(
        f"{source} is temporarily unavailable (network error after {attempts} attempts). "
        "Please try again shortly."
    ) from last_exc


async def _post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    source: str,
    json_body: dict,
    timeout: float = 120.0,
    on_heartbeat: HeartbeatCallback | None = None,
) -> httpx.Response:
    """POST JSON with retry/backoff on transient errors."""
    attempts = max(1, settings.download_max_retries)
    last_exc: Exception | None = None
    resp: httpx.Response | None = None

    for attempt in range(1, attempts + 1):
        try:
            resp = await client.post(url, json=json_body, timeout=timeout)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
            resp = None
            logger.warning(
                "%s POST failed (attempt %s/%s): %s",
                source,
                attempt,
                attempts,
                redact_secrets(str(exc)),
            )
            if attempt < attempts:
                if on_heartbeat:
                    on_heartbeat()
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
            if on_heartbeat:
                on_heartbeat()
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
    on_progress: DownloadProgressCallback | None = None,
    on_heartbeat: HeartbeatCallback | None = None,
    title: str = "",
    row_count_hint: int | None = None,
) -> tuple[bytes, str]:
    """Return body and a coarse content kind: csv | json | unknown."""
    if portal == "fred" or "api.stlouisfed.org/fred/" in url.lower():
        return await fetch_fred_json(url, client=client), "json"

    if portal == "world_bank" or "api.worldbank.org" in url.lower():
        return await fetch_worldbank_json(
            url,
            client=client,
            on_progress=on_progress,
            on_heartbeat=on_heartbeat,
        ), "json"

    if portal == "nyc_open_data" or is_socrata_query_url(url):
        return await fetch_socrata_json(
            url,
            client=client,
            on_progress=on_progress,
            on_heartbeat=on_heartbeat,
            title=title,
            row_count_hint=row_count_hint,
        ), "json"

    timeout = (
        settings.download_large_timeout_sec
        if row_count_hint and row_count_hint >= settings.download_large_row_hint
        else 120.0
    )
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(follow_redirects=True, trust_env=False)
    try:
        resp = await _get_with_retry(
            client,
            url,
            source="The data source",
            timeout=timeout,
            on_heartbeat=on_heartbeat,
        )
        if resp.status_code >= 400:
            raise DownloadError(_friendly_http_error("The data source", resp.status_code))
        data = resp.content
        _check_download_size(data)
        kind = _guess_kind(url, resp.headers.get("content-type"), data)
        return data, kind
    except httpx.HTTPError as exc:
        raise DownloadError(redact_secrets(str(exc))) from exc
    finally:
        if owns_client:
            await client.aclose()


async def fetch_worldbank_json(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    on_progress: DownloadProgressCallback | None = None,
    on_heartbeat: HeartbeatCallback | None = None,
) -> bytes:
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
    params: dict[str, str | int] = {
        "format": "json",
        "per_page": max(1, settings.wb_download_per_page),
    }
    if "?" in url:
        for part in url.split("?", 1)[1].split("&"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            if key.lower() in {"format", "page", "per_page"}:
                continue
            params[key] = value

    all_rows: list[dict] = []
    meta: dict = {}
    page = 1
    row_target = settings.row_cap
    max_pages = max(1, (row_target + settings.wb_download_per_page - 1) // settings.wb_download_per_page)

    try:
        while page <= max_pages:
            params["page"] = page
            try:
                resp = await _get_with_retry(
                    client,
                    base_url,
                    source="World Bank",
                    params=params,
                    on_heartbeat=on_heartbeat,
                )
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
            total_rows = int(meta.get("total") or len(all_rows))
            row_target = min(settings.row_cap, total_rows)
            total_pages = int(meta.get("pages") or 1)
            if on_progress:
                from findings_api.ingest.download_policy import download_progress_message

                on_progress(
                    download_progress_message(rows_done=len(all_rows), row_target=row_target)
                )
            if len(all_rows) >= row_target:
                all_rows = all_rows[:row_target]
                break
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
        _check_download_size(data)
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


async def fetch_socrata_json(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    on_progress: DownloadProgressCallback | None = None,
    on_heartbeat: HeartbeatCallback | None = None,
    title: str = "",
    row_count_hint: int | None = None,
) -> bytes:
    """Download rows from a SODA3 query URL in paginated chunks (reliable up to byte cap)."""
    _base, _dataset_id, soql = parse_query_url(url)
    endpoint = url.split("?", 1)[0]
    base_query, parsed_limit = split_soql_limit(soql)
    row_target = min(parsed_limit or settings.row_cap, settings.row_cap)
    chunk_size = max(1, settings.socrata_download_chunk_rows)

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(follow_redirects=True, trust_env=False)

    all_rows: list[dict] = []
    offset = 0

    try:
        while len(all_rows) < row_target:
            take = min(chunk_size, row_target - len(all_rows))
            page_query = page_soql(base_query, limit=take, offset=offset)
            resp = await _post_with_retry(
                client,
                endpoint,
                source="NYC Open Data",
                json_body={"query": page_query},
                timeout=settings.download_chunk_timeout_sec,
                on_heartbeat=on_heartbeat,
            )
            if resp.status_code >= 400:
                if all_rows:
                    logger.warning(
                        "Socrata pagination stopped at offset %s (HTTP %s); returning %s rows",
                        offset,
                        resp.status_code,
                        len(all_rows),
                    )
                    break
                raise DownloadError(_friendly_http_error("NYC Open Data", resp.status_code))

            page_data = resp.content
            _check_download_size(page_data)
            page_rows = json.loads(page_data.decode("utf-8", errors="replace"))
            if not isinstance(page_rows, list):
                raise DownloadError("NYC Open Data returned an unexpected response.")
            if not page_rows:
                break

            trial = all_rows + page_rows
            encoded = json.dumps(trial).encode("utf-8")
            if len(encoded) > settings.max_download_bytes:
                logger.warning(
                    "Socrata download truncated at %s rows (byte cap %sMB)",
                    len(all_rows),
                    settings.max_download_bytes // 1_000_000,
                )
                break

            all_rows = trial
            offset += len(page_rows)

            if on_progress:
                from findings_api.ingest.download_policy import download_progress_message

                on_progress(download_progress_message(rows_done=len(all_rows), row_target=row_target))

            if len(page_rows) < take:
                break

        if not all_rows:
            raise DownloadError("NYC Open Data query returned no rows")

        result = json.dumps(all_rows).encode("utf-8")
        _check_download_size(result)
        logger.info(
            "Socrata download complete%s: %s rows, %.1fMB",
            f" ({title})" if title else "",
            len(all_rows),
            len(result) / 1_000_000,
        )
        return result
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
