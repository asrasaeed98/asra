"""Sync World Bank indicators (CC-BY with mandatory attribution)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from findings_api.catalog.quality import apply_probe
from findings_api.catalog.probe import ProbeResult
from findings_api.config import settings
from findings_api.licensing import (
    attribution_required,
    default_attribution,
    is_allowed,
)
from findings_api.models import CatalogResource

logger = logging.getLogger(__name__)

WB_API = "https://api.worldbank.org/v2/indicator"
LICENSE_NORM = "CC_BY"


def _build_search_text(title: str, desc: str, org: str, tags: list[str]) -> str:
    return " ".join(filter(None, [title, desc, org, " ".join(tags)])).lower()


async def sync_worldbank(session: Session, client: httpx.AsyncClient) -> int:
    """Fetch indicators and upsert allowed World Bank rows."""
    count = 0
    page = 1
    per_page = 100
    max_items = settings.wb_sync_max_indicators

    while count < max_items:
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
            if count >= max_items:
                break
            ind_id = row.get("id")
            name = row.get("name") or ind_id
            if not ind_id or not name:
                continue

            if not is_allowed(LICENSE_NORM, "world_bank"):
                continue

            source = row.get("source") or {}
            source_name = source.get("value") if isinstance(source, dict) else str(source)
            org = row.get("sourceOrganization") or source_name or "World Bank"
            topics = row.get("topics") or []
            tags = [t.get("value", "") for t in topics if isinstance(t, dict)]

            source_url = f"https://data.worldbank.org/indicator/{ind_id}"
            resource_url = (
                f"https://api.worldbank.org/v2/country/all/indicator/{ind_id}"
                f"?format=json&per_page=500"
            )
            desc = (row.get("sourceNote") or "")[:2000]
            publisher = "World Bank"
            attr = default_attribution("world_bank", name, org, source_url)

            rid = f"wb:{ind_id}"
            rec = CatalogResource(
                id=rid,
                portal="world_bank",
                title=name,
                description=desc or None,
                organization=org,
                tags=tags,
                format="JSON_WORLDBANK",
                license_normalized=LICENSE_NORM,
                license_raw="CC-BY-4.0 (World Bank Terms of Use)",
                license_display="CC BY 4.0 — attribution required",
                attribution_required=attribution_required(LICENSE_NORM),
                attribution_text=attr,
                publisher=publisher,
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
                updated_at=datetime.now(timezone.utc),
                search_text=_build_search_text(name, desc, org, tags),
                ingestible=True,
                detected_format="JSON_WORLDBANK",
                ingest_block_reason=None,
            )
            apply_probe(
                rec,
                ProbeResult(True, "World Bank API (normalized on ingest)", "JSON_WORLDBANK"),
            )
            session.merge(rec)
            count += 1

        pages = int(meta.get("pages", 1))
        if page >= pages:
            break
        page += 1

    session.commit()
    logger.info("World Bank sync: %s indicators", count)
    return count
