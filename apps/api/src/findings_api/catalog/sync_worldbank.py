"""Sync World Bank indicators (CC-BY with mandatory attribution)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import delete
from sqlalchemy.orm import Session

from findings_api.catalog.quality import apply_probe
from findings_api.catalog.probe import probe_url
from findings_api.catalog.worldbank_diversity import (
    CURATED_INDICATORS,
    indicator_family,
    primary_topic,
)
from findings_api.config import settings
from findings_api.licensing import (
    attribution_required,
    default_attribution,
    is_allowed,
)
from findings_api.catalog.sync_limits import PENDING_PROBE_REASON, max_indexed, should_probe
from findings_api.models import CatalogResource

logger = logging.getLogger(__name__)

WB_API = "https://api.worldbank.org/v2/indicator"
LICENSE_NORM = "CC_BY"


def _build_search_text(title: str, desc: str, org: str, tags: list[str]) -> str:
    return " ".join(filter(None, [title, desc, org, " ".join(tags)])).lower()


async def _fetch_indicator_meta(client: httpx.AsyncClient, ind_id: str) -> dict | None:
    resp = await client.get(f"{WB_API}/{ind_id}", params={"format": "json"}, timeout=30.0)
    if resp.status_code != 200:
        return None
    payload = resp.json()
    if not isinstance(payload, list) or len(payload) < 2:
        return None
    rows = payload[1]
    return rows[0] if rows else None


def _diversity_allows(
    row: dict,
    *,
    family_counts: dict[str, int],
    topic_counts: dict[str, int],
    skip_family_cap: bool = False,
) -> bool:
    if skip_family_cap:
        return True
    fam = indicator_family(row.get("id") or "", row.get("name") or "")
    if family_counts.get(fam, 0) >= settings.wb_sync_max_per_family:
        return False
    topic = primary_topic(row.get("topics"))
    if topic_counts.get(topic, 0) >= settings.wb_sync_max_per_topic:
        return False
    return True


def _record_diversity(row: dict, *, family_counts: dict[str, int], topic_counts: dict[str, int]) -> None:
    fam = indicator_family(row.get("id") or "", row.get("name") or "")
    topic = primary_topic(row.get("topics"))
    family_counts[fam] = family_counts.get(fam, 0) + 1
    topic_counts[topic] = topic_counts.get(topic, 0) + 1


async def _index_indicator(
    session: Session,
    client: httpx.AsyncClient,
    row: dict,
    *,
    ingestible_so_far: int,
    ingestible_cap: int,
) -> bool:
    """Upsert one indicator; return True if ingestible."""
    ind_id = row.get("id")
    name = row.get("name") or ind_id
    if not ind_id or not name or not is_allowed(LICENSE_NORM, "world_bank"):
        return False

    source = row.get("source") or {}
    source_name = source.get("value") if isinstance(source, dict) else str(source)
    org = row.get("sourceOrganization") or source_name or "World Bank"
    topics = row.get("topics") or []
    tags = [t.get("value", "") for t in topics if isinstance(t, dict) and t.get("value")]

    source_url = f"https://data.worldbank.org/indicator/{ind_id}"
    resource_url = (
        f"https://api.worldbank.org/v2/country/all/indicator/{ind_id}?format=json&per_page=500"
    )
    desc = (row.get("sourceNote") or "")[:2000]
    attr = default_attribution("world_bank", name, org, source_url)

    rec = CatalogResource(
        id=f"wb:{ind_id}",
        portal="world_bank",
        title=name.strip(),
        description=desc or None,
        organization=org,
        tags=tags,
        format="JSON_WORLDBANK",
        license_normalized=LICENSE_NORM,
        license_raw="CC-BY-4.0 (World Bank Terms of Use)",
        license_display="CC BY 4.0 — attribution required",
        attribution_required=attribution_required(LICENSE_NORM),
        attribution_text=attr,
        publisher="World Bank",
        source_url=source_url,
        resource_url=resource_url,
        columns=[
            {"name": "countryiso3code"},
            {"name": "country"},
            {"name": "indicator_id"},
            {"name": "indicator"},
            {"name": "date"},
            {"name": "value"},
        ],
        byte_size=None,
        row_count_hint=None,
        updated_at=datetime.now(timezone.utc),
        search_text=_build_search_text(name, desc, org, tags),
        ingestible=False,
    )
    if not settings.catalog_probe_enabled:
        rec.ingestible = True
        rec.detected_format = "JSON_WORLDBANK"
    elif should_probe(ingestible=ingestible_so_far, ingestible_cap=ingestible_cap):
        probe = await probe_url(resource_url, client=client, portal="world_bank")
        apply_probe(rec, probe)
    else:
        rec.ingestible = False
        rec.ingest_block_reason = PENDING_PROBE_REASON
        rec.detected_format = "JSON_WORLDBANK"

    session.merge(rec)
    session.flush()
    return bool(rec.ingestible)


async def sync_worldbank(session: Session, client: httpx.AsyncClient) -> int:
    """Fetch indicators and upsert allowed World Bank rows with diversity caps."""
    max_ingestible = settings.wb_sync_max_indicators
    max_rows = max_indexed(max_ingestible, settings.wb_sync_max_indexed)
    family_counts: dict[str, int] = {}
    topic_counts: dict[str, int] = {}
    indexed = 0
    ingestible = 0
    skipped_duplicate = 0

    session.execute(delete(CatalogResource).where(CatalogResource.portal == "world_bank"))
    session.commit()

    # Phase 1 — curated macro indicators (always attempt, no family cap).
    for ind_id in CURATED_INDICATORS:
        if indexed >= max_rows:
            break
        row = await _fetch_indicator_meta(client, ind_id)
        if not row:
            continue
        ok = await _index_indicator(
            session, client, row, ingestible_so_far=ingestible, ingestible_cap=max_ingestible
        )
        indexed += 1
        if ok:
            ingestible += 1
            _record_diversity(row, family_counts=family_counts, topic_counts=topic_counts)
        if indexed % 25 == 0:
            session.commit()

    # Phase 2 — walk catalog with per-family and per-topic caps.
    page = 1
    per_page = 100
    while indexed < max_rows:
        url = f"{WB_API}?format=json&per_page={per_page}&page={page}"
        resp = await client.get(url, timeout=60.0)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, list) or len(payload) < 2:
            break
        meta, rows = payload[0], payload[1]
        if not rows:
            break

        for row in rows:
            if indexed >= max_rows:
                break
            ind_id = row.get("id")
            if not ind_id or ind_id in CURATED_INDICATORS:
                continue
            if ingestible < max_ingestible and not _diversity_allows(
                row, family_counts=family_counts, topic_counts=topic_counts
            ):
                skipped_duplicate += 1
                continue

            ok = await _index_indicator(
                session, client, row, ingestible_so_far=ingestible, ingestible_cap=max_ingestible
            )
            indexed += 1
            if ok:
                ingestible += 1
                _record_diversity(row, family_counts=family_counts, topic_counts=topic_counts)
            if indexed % 25 == 0:
                session.commit()

        pages = int(meta.get("pages", 1))
        if page >= pages:
            break
        page += 1

    session.commit()
    logger.info(
        "World Bank sync: %s indexed (%s ingestible, %s skipped as near-duplicates)",
        indexed,
        ingestible,
        skipped_duplicate,
    )
    return indexed
