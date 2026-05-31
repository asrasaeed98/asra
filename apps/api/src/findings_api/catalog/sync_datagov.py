"""Sync data.gov via the Catalog API with distribution ranking + URL probes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from findings_api.catalog.distributions import ranked_distributions
from findings_api.catalog.probe import ProbeResult, probe_url
from findings_api.catalog.quality import apply_probe
from findings_api.config import settings
from findings_api.licensing import (
    attribution_required,
    default_attribution,
    is_allowed,
    normalize_license,
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

CC0_MARKERS = ("creativecommons.org/publicdomain/zero", "cc0", "cc-zero")

# Bias toward tabular CSV/JSON with open licenses.
SEARCH_QUERIES: tuple[dict[str, str], ...] = (
    {"q": "csv", "data_type": "non-geospatial"},
    {"q": "statistics csv"},
    {"q": "population csv"},
    {"q": "unemployment csv"},
    {"q": "health csv"},
    {"q": "economy csv"},
    {"q": "education csv"},
    {"org_slug": "census-bureau", "q": "csv"},
    {"org_slug": "department-of-labor", "q": "csv"},
    {"org_slug": "department-of-health-and-human-services", "q": "csv"},
)


def _license_from_dcat(dcat: dict, desc: str) -> str | None:
    lic = dcat.get("license") or ""
    if isinstance(lic, str) and lic.strip():
        return lic.strip()
    low_desc = desc.lower()
    if "cc0" in low_desc or "creative commons zero" in low_desc:
        return "https://creativecommons.org/publicdomain/zero/1.0/"
    if "public domain" in low_desc and "17 usc" in low_desc.replace(" ", ""):
        return "https://www.usa.gov/publicdomain/label/1.0/"
    return None


def _resolve_license(dcat: dict, desc: str) -> tuple[str | None, str | None]:
    """Return (license_normalized, license_raw) if dataset is allowed for data.gov."""
    lic_raw = _license_from_dcat(dcat, desc)
    if lic_raw and any(m in lic_raw.lower() for m in CC0_MARKERS):
        return "CC0", lic_raw
    lic_norm = normalize_license(lic_raw)
    if lic_norm and is_allowed(lic_norm, "data_gov"):
        return lic_norm, lic_raw
    return None, lic_raw


async def _probe_best_url(
    client: httpx.AsyncClient,
    dcat: dict,
    *,
    max_attempts: int = 5,
):
    """Try top-ranked distribution URLs until one probes ingestible."""
    last: ProbeResult | None = None
    last_url = ""
    last_fmt = "UNKNOWN"
    for url, fmt_hint, _score in ranked_distributions(dcat)[:max_attempts]:
        last_url = url
        last_fmt = fmt_hint
        result = await probe_url(url, client=client, portal="data_gov")
        last = result
        if result.ingestible:
            return url, fmt_hint, result
    if last is not None:
        return last_url, last_fmt, last
    return None, None, ProbeResult(False, "no distribution URL", "EMPTY")


async def sync_datagov(session: Session, client: httpx.AsyncClient) -> int:
    base = settings.catalog_api_base.rstrip("/")
    indexed = 0
    ingestible = 0
    per_page = min(settings.ckan_sync_rows, 25)
    max_ingestible = settings.ckan_sync_max_packages
    max_rows = max_indexed(max_ingestible, settings.ckan_sync_max_indexed)
    seen_ids: set[str] = set()
    completed = False
    can_prune = False
    hit_row_cap = False
    upstream_exhausted = True

    try:
        query_list: tuple[dict[str, str], ...] = SEARCH_QUERIES
        if max_rows > max_ingestible:
            query_list = (*SEARCH_QUERIES, {"q": "dataset"})

        for query_params in query_list:
            if indexed >= max_rows:
                hit_row_cap = True
                break
            after: str | None = None
            pages = 0
            max_pages = settings.ckan_sync_max_pages
            if max_rows > max_ingestible:
                max_pages = max(max_pages, 500)
            while indexed < max_rows and pages < max_pages:
                params: dict = {"per_page": per_page, **query_params}
                if after:
                    params["after"] = after
                resp = await client.get(f"{base}/search", params=params, timeout=60.0)
                resp.raise_for_status()
                payload = resp.json()
                results = payload.get("results") or []
                if not results:
                    break

                for item in results:
                    if indexed >= max_rows:
                        hit_row_cap = True
                        break
                    dcat = item.get("dcat") or {}
                    access = (dcat.get("accessLevel") or item.get("accessLevel") or "").lower()
                    if access and access != "public":
                        continue

                    slug = item.get("slug") or item.get("identifier") or dcat.get("identifier")
                    if not slug:
                        continue
                    rec_id = f"datagov:{slug}"
                    if rec_id in seen_ids:
                        continue

                    title = item.get("title") or dcat.get("title") or "Dataset"
                    desc = (item.get("description") or dcat.get("description") or "")[:4000]
                    lic_norm, lic_raw = _resolve_license(dcat, desc)
                    if not lic_norm:
                        continue

                    seen_ids.add(rec_id)
                    org_obj = item.get("organization") or {}
                    org = org_obj.get("name") if isinstance(org_obj, dict) else str(org_obj)
                    org = org or item.get("publisher") or dcat.get("publisher", {}).get("name") or "data.gov"
                    tags = item.get("keyword") or dcat.get("keyword") or []
                    pkg_url = item.get("landingPage") or dcat.get("landingPage") or f"https://catalog.data.gov/dataset/{slug}"
                    lic_display = {
                        "CC0": "CC0 1.0 — public domain dedication",
                        "US_PD": "US Public Domain",
                        "US_GOV_WORK": "US Government Work",
                        "PDDL": "Public Domain Dedication",
                    }.get(lic_norm, lic_raw or lic_norm)

                    rec = CatalogResource(
                        id=rec_id,
                        portal="data_gov",
                        title=title,
                        description=desc or None,
                        organization=org,
                        tags=tags if isinstance(tags, list) else [],
                        format="UNKNOWN",
                        license_normalized=lic_norm,
                        license_raw=lic_raw or lic_display,
                        license_display=lic_display,
                        attribution_required=attribution_required(lic_norm),
                        attribution_text=default_attribution("data_gov", title, org, pkg_url),
                        publisher=org,
                        source_url=pkg_url,
                        resource_url=pkg_url,
                        columns=None,
                        row_count_hint=None,
                        byte_size=None,
                        updated_at=datetime.now(timezone.utc),
                        search_text=build_search_text(title, desc, org, tags if isinstance(tags, list) else []),
                        ingestible=False,
                    )

                    ranked = ranked_distributions(dcat)
                    if ranked:
                        resource_url, fmt, _ = ranked[0]
                        rec.resource_url = resource_url
                        rec.format = fmt or "UNKNOWN"

                    if not settings.catalog_probe_enabled:
                        if ranked:
                            rec.ingestible = True
                        else:
                            rec.ingestible = False
                            rec.ingest_block_reason = "no distribution URL"
                    elif should_probe(ingestible=ingestible, ingestible_cap=max_ingestible):
                        resource_url, fmt, probe = await _probe_best_url(client, dcat)
                        if resource_url:
                            rec.resource_url = resource_url
                            rec.format = probe.detected_format or fmt or "UNKNOWN"
                            apply_probe(rec, probe)
                        else:
                            apply_probe(rec, ProbeResult(False, "no distribution URL", "EMPTY"))
                    elif ranked:
                        rec.ingestible = False
                        rec.ingest_block_reason = PENDING_PROBE_REASON
                    else:
                        rec.ingestible = False
                        rec.ingest_block_reason = "no distribution URL"

                    session.merge(rec)
                    session.flush()
                    indexed += 1
                    if rec.ingestible:
                        ingestible += 1
                    if indexed % 25 == 0:
                        session.commit()

                after = payload.get("after")
                pages += 1
                if not after:
                    break
            if after and pages >= max_pages:
                upstream_exhausted = False

        session.commit()
        completed = True
        can_prune = should_prune_after_sync(
            hit_row_cap=hit_row_cap,
            upstream_exhausted=upstream_exhausted,
        )
        logger.info("data.gov Catalog API sync: %s indexed (%s ingestible)", indexed, ingestible)
        return indexed
    except Exception:
        session.rollback()
        logger.exception(
            "data.gov sync failed after %s indexed rows; existing catalog rows kept",
            indexed,
        )
        raise
    finally:
        if completed and can_prune:
            pruned = prune_stale_portal_rows(session, "data_gov", seen_ids, id_prefix="datagov:")
            session.commit()
            if pruned:
                logger.info("data.gov prune: removed %s stale rows", pruned)
