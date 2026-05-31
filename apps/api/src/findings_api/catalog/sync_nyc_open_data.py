"""Sync NYC Open Data (Socrata) into the catalog — separate from data.gov / WB / FRED."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from findings_api.catalog.probe import probe_url
from findings_api.catalog.quality import apply_probe
from findings_api.catalog.socrata import (
    LICENSE_NORM,
    PORTAL_NYC,
    build_scalar_soql,
    fetch_socrata_row_count,
    query_url,
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
)

SKIP_VIEW_TYPES = frozenset({"blob", "file", "filter", "href", "chart", "map"})


async def _fetch_view_meta(client: httpx.AsyncClient, base: str, dataset_id: str) -> dict | None:
    resp = await client.get(f"{base.rstrip('/')}/api/views/{dataset_id}.json", timeout=60.0)
    if resp.status_code != 200:
        return None
    return resp.json()


async def _discover_ids(client: httpx.AsyncClient, base: str, *, limit: int) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for dataset_id in CURATED_DATASET_IDS:
        if len(ordered) >= limit:
            break
        if dataset_id not in seen:
            seen.add(dataset_id)
            ordered.append(dataset_id)

    for q in METADATA_SEARCH_QUERIES:
        if len(ordered) >= limit:
            break
        resp = await client.get(
            f"{base.rstrip('/')}/api/views/metadata/v1",
            params={"q": q, "$limit": min(25, limit)},
            timeout=60.0,
        )
        if resp.status_code != 200:
            continue
        for item in resp.json():
            if len(ordered) >= limit:
                break
            ds_id = item.get("id")
            if ds_id and ds_id not in seen:
                seen.add(ds_id)
                ordered.append(ds_id)
    return ordered


async def sync_nyc_open_data(session: Session, client: httpx.AsyncClient) -> int:
    """Index NYC Open Data datasets via Socrata metadata + SODA3 query URLs."""
    base = settings.nyc_open_data_base.rstrip("/")
    max_ingestible = settings.nyc_sync_max_ingestible
    max_rows = max_indexed(max_ingestible, settings.nyc_sync_max_indexed)
    if not is_allowed(LICENSE_NORM, PORTAL_NYC):
        logger.warning("NYC Open Data license %s not allowed for portal %s", LICENSE_NORM, PORTAL_NYC)
        return 0

    indexed = 0
    ingestible = 0
    seen_ids: set[str] = set()
    dataset_ids = await _discover_ids(client, base, limit=max_rows)

    for dataset_id in dataset_ids:
        if indexed >= max_rows:
            break
        meta = await _fetch_view_meta(client, base, dataset_id)
        if not meta:
            continue
        view_type = (meta.get("viewType") or "tabular").lower()
        if view_type in SKIP_VIEW_TYPES:
            continue

        title = clamp_str(meta.get("name") or meta.get("title") or dataset_id, 512) or dataset_id
        desc = clamp_str((meta.get("description") or "")[:4000], 4000)
        category = meta.get("category") or meta.get("attribution") or "NYC Open Data"
        org = clamp_str(str(category), 512) or "NYC Open Data"
        tags = [meta.get("category")] if meta.get("category") else []
        tags = [t for t in tags if t]

        columns_meta = meta.get("columns") or []
        soql = build_scalar_soql(columns_meta)
        if not soql:
            logger.debug("Skipping %s — no scalar columns for SoQL", dataset_id)
            continue

        resource_url = query_url(base, dataset_id, soql)
        page_url = source_page_url(base, dataset_id)
        rid = f"nyc:{dataset_id}"

        row_count_hint = await fetch_socrata_row_count(client, base, dataset_id)

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
            updated_at=datetime.now(timezone.utc),
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
