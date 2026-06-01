"""Sync NYC Open Data (Socrata) into the catalog — separate from data.gov / WB / FRED."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from findings_api.catalog.probe import probe_url
from findings_api.catalog.quality import apply_probe
from findings_api.catalog.socrata import (
    LICENSE_NORM,
    PORTAL_NYC,
    SOCRATA_CATALOG_API,
    build_catalog_resource_url,
    build_scalar_soql,
    fetch_socrata_row_count,
    socrata_domain,
    source_page_url,
)
from findings_api.catalog.sync_limits import (
    PENDING_PROBE_REASON,
    build_search_text,
    clamp_str,
    max_indexed,
    should_probe,
)
from findings_api.config import settings
from findings_api.licensing import attribution_required, default_attribution, is_allowed
from findings_api.models import CatalogResource

logger = logging.getLogger(__name__)

# Reliable tabular datasets for local testing and initial catalog seed.
CURATED_DATASET_IDS = (
    "5uac-w243",  # NYPD Complaint Data Current (YTD)
    "erm2-nwe9",  # 311 Service Requests
    "7ym2-wayt",  # Automated Traffic Volume Counts
    "5ucz-vwe8",  # NYC Restaurant Inspection Results
    "wvxf-dwi5",  # Housing Maintenance Code Violations
    "e5aq-a4j2",  # DOB Job Application Filings
    "43nn-pn8j",  # Parking Violations Issued
)

METADATA_SEARCH_QUERIES = (
    "crime",
    "311",
    "housing",
    "restaurant",
    "traffic",
    "employment",
    "health",
    "education",
    "transit",
    "environment",
    "budget",
    "parks",
    "business",
    "building",
    "violations",
    "demographics",
    "salary",
    "covid",
    "police",
    "fire",
    "permits",
    "inspection",
    "complaint",
    "payroll",
    "election",
    "water",
    "energy",
    "safety",
    "homeless",
    "rent",
    "taxi",
    "bicycle",
    "tree",
    "air quality",
    "waste",
    "flood",
    "noise",
    "rat",
    "shelter",
    "eviction",
    "hospital",
    "overdose",
    "lead",
    "contract",
    "procurement",
    "finance",
    "tax",
    "property",
    "zoning",
    "license",
)

# NYC metadata search honors plain `limit` but ignores `offset` — one page per query.
DISCOVERY_PAGE_SIZE = 150
# Socrata discovery catalog supports scroll_id pagination (up to 1000/page).
CATALOG_PAGE_SIZE = 1000
CATALOG_MAX_PAGES = 3
# Inspect extra candidates because many fail tabular / SoQL filters.
DISCOVERY_POOL_MULTIPLIER = 4
DISCOVERY_POOL_MAX = 1000

SKIP_VIEW_TYPES = frozenset({"blob", "file", "filter", "href", "chart", "map", "story"})
_EPOCH_MIN = datetime.min.replace(tzinfo=timezone.utc)


def _parse_iso_ts(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    normalized = value.replace("Z", "+00:00")
    if normalized.endswith("+0000"):
        normalized = f"{normalized[:-5]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _epoch_ts(value: int | float | str | None) -> datetime | None:
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    if n > 1e12:
        n /= 1000.0
    try:
        return datetime.fromtimestamp(n, tz=timezone.utc)
    except (OSError, ValueError, OverflowError):
        return None


def _search_item_recency(item: dict) -> datetime:
    for key in ("dataUpdatedAt", "updatedAt", "metadataUpdatedAt", "createdAt"):
        if ts := _parse_iso_ts(item.get(key)):
            return ts
    return _EPOCH_MIN


def _catalog_item_recency(item: dict) -> datetime:
    resource = item.get("resource") if isinstance(item.get("resource"), dict) else {}
    for key in ("data_updated_at", "updatedAt", "metadata_updated_at", "createdAt"):
        if ts := _parse_iso_ts(resource.get(key)):
            return ts
    return _EPOCH_MIN


def _view_recency(meta: dict) -> datetime:
    if ts := _epoch_ts(meta.get("rowsUpdatedAt")):
        return ts
    for key in ("viewLastModified", "updatedAt", "createdAt"):
        raw = meta.get(key)
        if ts := _parse_iso_ts(raw if isinstance(raw, str) else None):
            return ts
        if ts := _epoch_ts(raw):
            return ts
    return _EPOCH_MIN


def _is_catalog_visible(*, search_item: dict | None = None, meta: dict | None = None) -> bool:
    for source in (search_item, meta):
        if not source:
            continue
        if source.get("hideFromCatalog") or source.get("hideFromDataJson"):
            return False
    return True


def _is_meaningful_view(meta: dict) -> bool:
    if not _is_catalog_visible(meta=meta):
        return False
    view_type = (meta.get("viewType") or "tabular").lower()
    if view_type in SKIP_VIEW_TYPES:
        return False
    title = meta.get("name") or meta.get("title")
    if not title or not str(title).strip():
        return False
    columns_meta = meta.get("columns") or []
    if not build_scalar_soql(columns_meta):
        return False
    return True


async def _fetch_view_meta(client: httpx.AsyncClient, base: str, dataset_id: str) -> dict | None:
    resp = await client.get(f"{base.rstrip('/')}/api/views/{dataset_id}.json", timeout=60.0)
    if resp.status_code != 200:
        return None
    payload = resp.json()
    return payload if isinstance(payload, dict) else None


async def _fetch_catalog_page(
    client: httpx.AsyncClient,
    domain: str,
    *,
    scroll_id: str,
    limit: int,
) -> list[dict]:
    resp = await client.get(
        SOCRATA_CATALOG_API,
        params={
            "domains": domain,
            "only": "datasets",
            "limit": limit,
            "scroll_id": scroll_id,
        },
        timeout=120.0,
    )
    if resp.status_code != 200:
        logger.warning("Socrata catalog page failed for %s: HTTP %s", domain, resp.status_code)
        return []
    payload = resp.json()
    if not isinstance(payload, dict):
        return []
    batch = payload.get("results")
    if not isinstance(batch, list):
        return []
    return [item for item in batch if isinstance(item, dict)]


async def _discover_from_catalog(
    client: httpx.AsyncClient,
    domain: str,
    note: Callable[[str | None, datetime], None],
    *,
    pool_cap: int,
) -> int:
    """Scroll the Socrata discovery catalog; return number of pages fetched."""
    scroll_id = "0"
    pages = 0
    while pages < CATALOG_MAX_PAGES:
        batch = await _fetch_catalog_page(
            client,
            domain,
            scroll_id=scroll_id,
            limit=CATALOG_PAGE_SIZE,
        )
        if not batch:
            break
        last_id: str | None = None
        for item in batch:
            resource = item.get("resource") if isinstance(item.get("resource"), dict) else {}
            ds_id = resource.get("id")
            if not ds_id:
                continue
            note(ds_id, _catalog_item_recency(item))
            last_id = ds_id
        pages += 1
        if len(batch) < CATALOG_PAGE_SIZE or not last_id:
            break
        scroll_id = last_id
        if pages >= CATALOG_MAX_PAGES:
            break
    logger.info("NYC catalog discovery: fetched %s catalog page(s) (pool cap %s)", pages, pool_cap)
    return pages


async def _fetch_search_batch(
    client: httpx.AsyncClient,
    base: str,
    query: str,
    *,
    limit: int,
) -> list[dict]:
    resp = await client.get(
        f"{base.rstrip('/')}/api/views/metadata/v1",
        params={"q": query, "limit": limit},
        timeout=60.0,
    )
    if resp.status_code != 200:
        logger.warning("NYC metadata search failed for %r: HTTP %s", query, resp.status_code)
        return []
    batch = resp.json()
    if not isinstance(batch, list):
        return []
    return [item for item in batch if isinstance(item, dict)]


async def _discover_candidate_ids(client: httpx.AsyncClient, base: str, *, limit: int) -> list[str]:
    """Collect unique dataset ids from curated seeds and topic searches, newest first."""
    pool_cap = min(max(limit * DISCOVERY_POOL_MULTIPLIER, limit + len(CURATED_DATASET_IDS)), DISCOVERY_POOL_MAX)
    by_id: dict[str, datetime] = {}

    def note(ds_id: str | None, recency: datetime) -> None:
        if not ds_id:
            return
        prev = by_id.get(ds_id)
        if prev is None or recency > prev:
            by_id[ds_id] = recency

    for dataset_id in CURATED_DATASET_IDS:
        note(dataset_id, _EPOCH_MIN)

    for query in METADATA_SEARCH_QUERIES:
        batch = await _fetch_search_batch(
            client,
            base,
            query,
            limit=DISCOVERY_PAGE_SIZE,
        )
        for item in batch:
            if not _is_catalog_visible(search_item=item):
                continue
            note(item.get("id"), _search_item_recency(item))

    ranked = sorted(by_id.items(), key=lambda pair: pair[1], reverse=True)
    selected = [ds_id for ds_id, _ in ranked[:pool_cap]]
    logger.info(
        "NYC discovery: %s unique candidates (%s selected for inspection, target index %s)",
        len(by_id),
        len(selected),
        limit,
    )
    return selected


async def _select_indexable_datasets(
    client: httpx.AsyncClient,
    base: str,
    candidate_ids: list[str],
    *,
    limit: int,
) -> list[tuple[str, dict, datetime]]:
    """Fetch full metadata, keep meaningful tabular datasets, return newest first."""
    indexable: list[tuple[str, dict, datetime]] = []

    for dataset_id in candidate_ids:
        meta = await _fetch_view_meta(client, base, dataset_id)
        if not meta or not _is_meaningful_view(meta):
            continue
        recency = _view_recency(meta)
        indexable.append((dataset_id, meta, recency))

    indexable.sort(key=lambda row: row[2], reverse=True)
    selected = indexable[:limit]
    logger.info(
        "NYC discovery: %s meaningful tabular datasets (indexing %s newest)",
        len(indexable),
        len(selected),
    )
    return selected


async def sync_nyc_open_data(session: Session, client: httpx.AsyncClient) -> int:
    """Index NYC Open Data datasets via Socrata metadata + SODA3 query URLs."""
    base = settings.nyc_open_data_base.rstrip("/")
    max_ingestible = settings.nyc_sync_max_ingestible
    max_rows = max_indexed(max_ingestible, settings.nyc_sync_max_indexed)
    if not is_allowed(LICENSE_NORM, PORTAL_NYC):
        logger.warning("NYC Open Data license %s not allowed for portal %s", LICENSE_NORM, PORTAL_NYC)
        return 0

    candidate_ids = await _discover_candidate_ids(client, base, limit=max_rows)
    datasets = await _select_indexable_datasets(client, base, candidate_ids, limit=max_rows)

    indexed = 0
    ingestible = 0
    seen_ids: set[str] = set()

    for dataset_id, meta, dataset_updated_at in datasets:
        if indexed >= max_rows:
            break

        rid = f"nyc:{dataset_id}"
        if rid in seen_ids:
            continue

        columns_meta = meta.get("columns") or []
        catalog_url = build_catalog_resource_url(base, dataset_id, columns_meta)
        if not catalog_url:
            continue
        resource_url, _soql = catalog_url

        title = clamp_str(meta.get("name") or meta.get("title") or dataset_id, 512) or dataset_id
        desc = clamp_str((meta.get("description") or "")[:4000], 4000)
        category = meta.get("category") or meta.get("attribution") or "NYC Open Data"
        org = clamp_str(str(category), 512) or "NYC Open Data"
        tags = [meta.get("category")] if meta.get("category") else []
        tags = [t for t in tags if t]

        page_url = source_page_url(base, dataset_id)
        row_count_hint = await fetch_socrata_row_count(client, base, dataset_id)
        if row_count_hint == 0:
            logger.debug("Skipping %s — empty dataset", dataset_id)
            continue

        rec = CatalogResource(
            id=rid,
            portal=PORTAL_NYC,
            title=title,
            description=desc,
            organization=org,
            tags=tags,
            format="JSON_SOCRATA",
            license_normalized=LICENSE_NORM,
            license_raw="NYC Open Data Terms of Use",
            license_display="NYC Open Data — US Government Work",
            attribution_required=attribution_required(LICENSE_NORM),
            attribution_text=default_attribution(PORTAL_NYC, title, org, page_url),
            publisher=clamp_str(org, 512) or "NYC Open Data",
            source_url=page_url,
            resource_url=resource_url,
            columns=[{"name": c.get("fieldName") or c.get("name")} for c in columns_meta[:50]],
            row_count_hint=row_count_hint,
            byte_size=None,
            updated_at=dataset_updated_at if dataset_updated_at > _EPOCH_MIN else datetime.now(timezone.utc),
            search_text=build_search_text(title, desc or "", org, tags + [dataset_id, "nyc", "new york"]),
            ingestible=False,
        )

        if not settings.catalog_probe_enabled:
            rec.ingestible = True
            rec.detected_format = "JSON_RECORDS"
        elif should_probe(ingestible=ingestible, ingestible_cap=max_ingestible):
            probe = await probe_url(resource_url, client=client, portal=PORTAL_NYC)
            apply_probe(rec, probe)
        else:
            rec.ingestible = False
            rec.ingest_block_reason = PENDING_PROBE_REASON
            rec.detected_format = "JSON_SOCRATA"

        session.merge(rec)
        seen_ids.add(rid)
        indexed += 1
        if rec.ingestible:
            ingestible += 1
        if indexed % 10 == 0:
            session.commit()

    session.commit()
    logger.info(
        "NYC Open Data sync: %s datasets indexed (%s ingestible)",
        indexed,
        ingestible,
    )
    return indexed
