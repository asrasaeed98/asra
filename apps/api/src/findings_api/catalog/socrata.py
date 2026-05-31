"""Shared helpers for Socrata / NYC Open Data APIs."""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from findings_api.config import settings

PORTAL_NYC = "nyc_open_data"
LICENSE_NORM = "US_GOV_WORK"
SOQL_QUERY_PARAM = "socrata_soql"

# Socrata column types we treat as flat scalars in SoQL SELECT lists.
SCALAR_DATA_TYPES = frozenset({
    "text",
    "number",
    "calendar_date",
    "checkbox",
    "url",
    "email",
    "phone",
    "money",
    "floating_timestamp",
})

SKIP_DATA_TYPES = frozenset({
    "point",
    "polygon",
    "multipolygon",
    "line",
    "location",
    "photo",
    "document",
    "blob",
})


def analysis_row_cap(*, limit: int | None = None) -> int:
    """Max rows pulled into analysis for Socrata datasets."""
    cap = limit if limit is not None else settings.row_cap
    return min(cap, 100_000)


def query_url(base: str, dataset_id: str, soql: str) -> str:
    """Build a SODA3 query URL with embedded SoQL (for catalog resource_url)."""
    path = f"{base.rstrip('/')}/api/v3/views/{dataset_id}/query.json"
    return f"{path}?{urlencode({SOQL_QUERY_PARAM: soql})}"


def parse_query_url(url: str) -> tuple[str, str, str]:
    """Return (base, dataset_id, soql) from a catalog resource_url."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    parts = parsed.path.strip("/").split("/")
    # .../api/v3/views/{id}/query.json
    dataset_id = ""
    for idx, part in enumerate(parts):
        if part == "views" and idx + 1 < len(parts):
            dataset_id = parts[idx + 1]
            break
    if not dataset_id:
        raise ValueError(f"Not a Socrata query URL: {url}")
    params = parse_qs(parsed.query)
    soql = (params.get(SOQL_QUERY_PARAM) or [default_soql()])[0]
    return base, dataset_id, soql


def split_soql_limit(soql: str) -> tuple[str, int | None]:
    """Return (query without trailing LIMIT, limit value or None)."""
    import re

    stripped = soql.strip().rstrip(";")
    match = re.search(r"\blimit\s+(\d+)\s*$", stripped, flags=re.IGNORECASE)
    if not match:
        return stripped, None
    base = stripped[: match.start()].strip()
    return base, int(match.group(1))


def page_soql(base: str, *, limit: int, offset: int) -> str:
    return f"{base} LIMIT {limit} OFFSET {offset}"


def default_soql(*, limit: int | None = None) -> str:
    cap = limit if limit is not None else settings.row_cap
    return f"SELECT * LIMIT {cap}"


def build_scalar_soql(columns: list[dict], *, limit: int | None = None) -> str | None:
    """Build a flat SoQL query excluding geo / nested Socrata column types."""
    names: list[str] = []
    for col in columns:
        field = col.get("fieldName") or col.get("name")
        if not field or field.startswith(":"):
            continue
        dtype = (col.get("dataTypeName") or "text").lower()
        if dtype in SKIP_DATA_TYPES:
            continue
        if dtype in SCALAR_DATA_TYPES or dtype.startswith("text"):
            names.append(field)
    if len(names) < 2:
        return None
    cap = limit if limit is not None else analysis_row_cap()
    select = ", ".join(names[:40])
    return f"SELECT {select} LIMIT {cap}"


def source_page_url(base: str, dataset_id: str) -> str:
    return f"{base.rstrip('/')}/d/{dataset_id}"


def is_socrata_query_url(url: str) -> bool:
    return "/query.json" in url.lower() and "views/" in url.lower()


async def fetch_socrata_row_count(
    client: httpx.AsyncClient,
    base: str,
    dataset_id: str,
) -> int | None:
    """Return total row count for a Socrata dataset via SODA3 count query."""
    endpoint = f"{base.rstrip('/')}/api/v3/views/{dataset_id}/query.json"
    try:
        resp = await client.post(
            endpoint,
            json={"query": "SELECT count(*) AS cnt"},
            timeout=60.0,
        )
        if resp.status_code != 200:
            return None
        rows = resp.json()
        if not isinstance(rows, list) or not rows:
            return None
        cnt = rows[0].get("cnt")
        return int(cnt) if cnt is not None else None
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return None
