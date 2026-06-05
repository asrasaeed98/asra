"""Shared helpers for Socrata / NYC Open Data APIs."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from findings_api.config import settings

PORTAL_NYC = "nyc_open_data"
LICENSE_NORM = "US_GOV_WORK"
SOQL_QUERY_PARAM = "socrata_soql"
# Matches CatalogResource.resource_url VARCHAR(1024).
CATALOG_RESOURCE_URL_MAX_LEN = 1024
SOCRATA_CATALOG_API = "https://api.us.socrata.com/api/catalog/v1"

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


def soda2_resource_url(base: str, dataset_id: str) -> str:
    """Classic SODA2 resource endpoint (public, no auth required).

    The SODA3 ``/api/v3/views/{id}/query.json`` endpoint now returns
    ``403 authentication_required``; the SODA2 ``/resource/{id}.json`` GET
    endpoint still serves public datasets without a token.
    """
    return f"{base.rstrip('/')}/resource/{dataset_id}.json"


def soql_select_columns(soql: str) -> str | None:
    """Column list for a SODA2 ``$select`` param, or None for ``SELECT *``."""
    base, _ = split_soql_limit(soql)
    match = re.match(r"(?is)^\s*select\s+(.*)$", base)
    if not match:
        return None
    cols = match.group(1).strip()
    if not cols or cols == "*":
        return None
    return cols


def socrata_headers() -> dict[str, str]:
    """Auth headers for Socrata requests. App token is optional but raises limits."""
    token = settings.socrata_app_token.strip()
    return {"X-App-Token": token} if token else {}


def split_soql_limit(soql: str) -> tuple[str, int | None]:
    """Return (query without trailing LIMIT, limit value or None)."""
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


def _socrata_column_kind(dtype: str) -> str:
    if dtype in ("number", "money"):
        return "numeric"
    if dtype in ("calendar_date", "floating_timestamp"):
        return "datetime"
    return "categorical"


def _rank_scalar_columns(columns: list[dict], *, portal: str | None = PORTAL_NYC) -> list[str]:
    """Return scalar column names ordered by analytical relevance."""
    from findings_api.analysis.field_relevance import _category_score, _is_coordinate_field, classify_field

    scored: list[tuple[int, str]] = []
    has_preferred_geo = False
    for col in columns:
        field = col.get("fieldName") or col.get("name")
        if not field:
            continue
        kind = _socrata_column_kind((col.get("dataTypeName") or "text").lower())
        if classify_field(field, kind=kind) == "geographic" and not _is_coordinate_field(field):
            has_preferred_geo = True

    for col in columns:
        field = col.get("fieldName") or col.get("name")
        if not field or field.startswith(":"):
            continue
        dtype = (col.get("dataTypeName") or "text").lower()
        if dtype in SKIP_DATA_TYPES:
            continue
        if dtype not in SCALAR_DATA_TYPES and not dtype.startswith("text"):
            continue
        kind = _socrata_column_kind(dtype)
        category = classify_field(field, kind=kind)
        is_coord = _is_coordinate_field(field)
        if is_coord and has_preferred_geo:
            continue
        score = _category_score(
            category,
            kind=kind,
            has_preferred_geo=has_preferred_geo,
            is_coordinate=is_coord,
        )
        if category in ("metadata", "administrative_identifier") and score < 40:
            continue
        scored.append((score, field))

    if not scored:
        return []
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [name for _, name in scored]


def scalar_field_names(columns: list[dict], *, max_names: int | None = None) -> list[str]:
    """Flat scalar column names suitable for SoQL SELECT lists."""
    names = _rank_scalar_columns(columns)
    if max_names is not None:
        return names[:max_names]
    return names


def build_scalar_soql(columns: list[dict], *, limit: int | None = None) -> str | None:
    """Build a flat SoQL query excluding geo / nested Socrata column types."""
    names = scalar_field_names(columns, max_names=40)
    if len(names) < 2:
        return None
    cap = limit if limit is not None else analysis_row_cap()
    return f"SELECT {', '.join(names)} LIMIT {cap}"


def build_catalog_resource_url(
    base: str,
    dataset_id: str,
    columns: list[dict],
    *,
    max_len: int = CATALOG_RESOURCE_URL_MAX_LEN,
) -> tuple[str, str] | None:
    """Return (resource_url, soql) that fits the catalog URL column; fall back to SELECT *."""
    names = scalar_field_names(columns)
    if len(names) < 2:
        return None

    cap = analysis_row_cap()
    soql_candidates: list[str] = []
    for count in range(min(40, len(names)), 1, -1):
        soql_candidates.append(f"SELECT {', '.join(names[:count])} LIMIT {cap}")
    soql_candidates.append(default_soql(limit=cap))

    seen: set[str] = set()
    for soql in soql_candidates:
        if soql in seen:
            continue
        seen.add(soql)
        url = query_url(base, dataset_id, soql)
        if len(url) <= max_len:
            return url, soql
    return None


def socrata_domain(base: str) -> str:
    """Return the Socrata domain host for a portal base URL."""
    return urlparse(base.rstrip("/")).netloc


def source_page_url(base: str, dataset_id: str) -> str:
    return f"{base.rstrip('/')}/d/{dataset_id}"


def is_socrata_query_url(url: str) -> bool:
    return "/query.json" in url.lower() and "views/" in url.lower()


async def fetch_socrata_row_count(
    client: httpx.AsyncClient,
    base: str,
    dataset_id: str,
) -> int | None:
    """Return total row count for a Socrata dataset via a SODA2 count query."""
    endpoint = soda2_resource_url(base, dataset_id)
    try:
        resp = await client.get(
            endpoint,
            params={"$select": "count(*)"},
            headers=socrata_headers(),
            timeout=60.0,
        )
        if resp.status_code != 200:
            return None
        rows = resp.json()
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            return None
        # SODA2 returns e.g. [{"count": "123"}] — the alias varies, take the first value.
        value = next(iter(rows[0].values()), None)
        return int(value) if value is not None else None
    except (httpx.HTTPError, ValueError, TypeError, KeyError, StopIteration):
        return None
