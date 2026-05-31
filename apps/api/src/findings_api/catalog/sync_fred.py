"""Sync FRED economic series (US public domain / government data)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from findings_api.catalog.quality import apply_probe
from findings_api.catalog.probe import ProbeResult, probe_url
from findings_api.config import settings
from findings_api.licensing import (
    attribution_required,
    default_attribution,
    is_allowed,
)
from findings_api.catalog.sync_limits import (
    PENDING_PROBE_REASON,
    build_search_text,
    max_indexed,
    prune_stale_portal_rows,
    should_prune_after_sync,
    should_probe,
)
from findings_api.models import CatalogResource

logger = logging.getLogger(__name__)

FRED_API = "https://api.stlouisfed.org/fred"
LICENSE_NORM = "US_GOV_WORK"

# High-quality demo series — always attempted first.
CURATED_SERIES = (
    "GDP",
    "UNRATE",
    "CPIAUCSL",
    "FEDFUNDS",
    "DGS10",
    "DGS2",
    "M2SL",
    "HOUST",
    "PAYEMS",
    "INDPRO",
    "PCEPI",
    "RSAFS",
    "UMCSENT",
    "T10Y2Y",
    "DCOILWTICO",
    "DEXUSEU",
    "BOPGSTB",
    "GDPC1",
    "CPILFESL",
    "MORTGAGE30US",
)

SEARCH_QUERIES = (
    "gdp",
    "unemployment",
    "inflation",
    "interest rate",
    "housing starts",
    "consumer price",
    "employment",
    "trade balance",
    "industrial production",
    "retail sales",
)




def _observations_url(series_id: str) -> str:
    params = urlencode({"series_id": series_id, "file_type": "json"})
    return f"{FRED_API}/series/observations?{params}"


def _is_copyrighted(notes: str | None) -> bool:
    return "copyright" in (notes or "").lower()


async def _fetch_series_meta(client: httpx.AsyncClient, series_id: str) -> dict | None:
    params = {
        "series_id": series_id,
        "file_type": "json",
        "api_key": settings.fred_api_key,
    }
    resp = await client.get(f"{FRED_API}/series", params=params, timeout=30.0)
    if resp.status_code != 200:
        return None
    payload = resp.json()
    rows = payload.get("seriess") or payload.get("series") or []
    return rows[0] if rows else None


async def _index_series(
    session: Session,
    client: httpx.AsyncClient,
    series_id: str,
    meta: dict,
    *,
    ingestible_so_far: int,
    ingestible_cap: int,
    seen_ids: set[str],
) -> bool:
    """Upsert one FRED series; return True if ingestible."""
    title = meta.get("title") or series_id
    notes = (meta.get("notes") or "")[:2000]
    if _is_copyrighted(notes):
        return False

    freq = meta.get("frequency_short") or meta.get("frequency") or ""
    units = meta.get("units_short") or meta.get("units") or ""
    tags = [t for t in (freq, units) if t]
    org = "Federal Reserve Bank of St. Louis (FRED)"
    source_url = f"https://fred.stlouisfed.org/series/{series_id}"
    resource_url = _observations_url(series_id)

    rid = f"fred:{series_id}"
    rec = CatalogResource(
        id=rid,
        portal="fred",
        title=title,
        description=notes or None,
        organization=org,
        tags=tags,
        format="JSON_FRED",
        license_normalized=LICENSE_NORM,
        license_raw="US Government Work / public domain (citation requested)",
        license_display="US Government Work — citation requested",
        attribution_required=attribution_required(LICENSE_NORM),
        attribution_text=default_attribution("fred", title, org, source_url),
        publisher=org,
        source_url=source_url,
        resource_url=resource_url,
        columns=[{"name": "date"}, {"name": "value"}, {"name": "series_id"}],
        row_count_hint=None,
        byte_size=None,
        updated_at=datetime.now(timezone.utc),
        search_text=build_search_text(title, notes, org, tags + [series_id]),
        ingestible=False,
    )

    if not settings.catalog_probe_enabled:
        rec.ingestible = True
        rec.detected_format = "JSON_FRED"
    elif should_probe(ingestible=ingestible_so_far, ingestible_cap=ingestible_cap):
        probe = await probe_url(resource_url, client=client, portal="fred")
        apply_probe(rec, probe)
    else:
        rec.ingestible = False
        rec.ingest_block_reason = PENDING_PROBE_REASON
        rec.detected_format = "JSON_FRED"

    session.merge(rec)
    session.flush()
    seen_ids.add(rid)
    return bool(rec.ingestible)


async def sync_fred(session: Session, client: httpx.AsyncClient) -> int:
    """Fetch FRED series and upsert license-safe rows."""
    if not settings.fred_api_key:
        logger.warning("FRED sync skipped — set FRED_API_KEY in .env")
        return 0

    indexed = 0
    ingestible = 0
    seen_series: set[str] = set()
    seen_ids: set[str] = set()
    max_ingestible = settings.fred_sync_max_series
    max_rows = max_indexed(max_ingestible, settings.fred_sync_max_indexed)
    completed = False
    can_prune = False
    hit_row_cap = False
    upstream_exhausted = False

    async def try_series(series_id: str, meta: dict | None = None) -> None:
        nonlocal indexed, ingestible, hit_row_cap
        if indexed >= max_rows:
            hit_row_cap = True
            return
        if series_id in seen_series:
            return
        seen_series.add(series_id)
        row = meta or await _fetch_series_meta(client, series_id)
        if not row or not is_allowed(LICENSE_NORM, "fred"):
            return
        if _is_copyrighted(row.get("notes")):
            return
        ok = await _index_series(
            session,
            client,
            series_id,
            row,
            ingestible_so_far=ingestible,
            ingestible_cap=max_ingestible,
            seen_ids=seen_ids,
        )
        indexed += 1
        if ok:
            ingestible += 1

    try:
        for series_id in CURATED_SERIES:
            if indexed >= max_rows:
                hit_row_cap = True
                break
            await try_series(series_id)

        for query in SEARCH_QUERIES:
            if indexed >= max_rows:
                hit_row_cap = True
                break
            offset = 0
            search_cap = 10000 if max_rows > max_ingestible else 500
            while indexed < max_rows and offset < search_cap:
                params = {
                    "search_text": query,
                    "api_key": settings.fred_api_key,
                    "file_type": "json",
                    "limit": 100,
                    "offset": offset,
                    "order_by": "popularity",
                    "sort_order": "desc",
                }
                resp = await client.get(f"{FRED_API}/series/search", params=params, timeout=60.0)
                if resp.status_code != 200:
                    break
                payload = resp.json()
                series_list = payload.get("seriess") or payload.get("series") or []
                if not series_list:
                    break
                for item in series_list:
                    if indexed >= max_rows:
                        hit_row_cap = True
                        break
                    series_id = item.get("id")
                    if not series_id:
                        continue
                    await try_series(series_id, meta=item)
                offset += len(series_list)
                total = int(payload.get("count") or 0)
                if offset >= total:
                    break

        if indexed < max_rows:
            offset = 0
            while indexed < max_rows:
                params = {
                    "api_key": settings.fred_api_key,
                    "file_type": "json",
                    "limit": 1000,
                    "offset": offset,
                }
                resp = await client.get(f"{FRED_API}/series", params=params, timeout=60.0)
                if resp.status_code != 200:
                    break
                payload = resp.json()
                series_list = payload.get("seriess") or payload.get("series") or []
                if not series_list:
                    upstream_exhausted = True
                    break
                for item in series_list:
                    if indexed >= max_rows:
                        hit_row_cap = True
                        break
                    series_id = item.get("id")
                    if not series_id:
                        continue
                    await try_series(series_id, meta=item)
                offset += len(series_list)
                if len(series_list) < 1000:
                    upstream_exhausted = not hit_row_cap
                    break
                if indexed % 100 == 0:
                    session.commit()

        session.commit()
        completed = True
        can_prune = should_prune_after_sync(
            hit_row_cap=hit_row_cap,
            upstream_exhausted=upstream_exhausted,
            partial_selection=max_rows > max_ingestible,
        )
        logger.info("FRED sync: %s series indexed (%s ingestible)", indexed, ingestible)
        return indexed
    except Exception:
        session.rollback()
        logger.exception(
            "FRED sync failed after %s indexed rows; existing catalog rows kept",
            indexed,
        )
        raise
    finally:
        if completed and can_prune:
            pruned = prune_stale_portal_rows(session, "fred", seen_ids)
            session.commit()
            if pruned:
                logger.info("FRED prune: removed %s stale rows", pruned)
