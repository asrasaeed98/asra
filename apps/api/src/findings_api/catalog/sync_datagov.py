"""Sync data.gov via the Catalog API with distribution ranking + URL probes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import delete
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
from findings_api.models import CatalogResource

logger = logging.getLogger(__name__)

CC0_MARKERS = ("creativecommons.org/publicdomain/zero", "cc0", "cc-zero")

# Rotate queries — sorting by last_harvested_date mostly surfaces broken inventory JSON.
SEARCH_QUERIES = (
    ".csv",
    "NEH csv",
    "statistics csv",
    "population csv",
    "unemployment csv",
    "health csv",
    "csv OR json",
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


def _build_search_text(title: str, desc: str, org: str, tags: list[str]) -> str:
    return " ".join(filter(None, [title, desc, org, " ".join(tags)])).lower()


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
    count = 0
    ingestible = 0
    per_page = min(settings.ckan_sync_rows, 25)
    max_items = settings.ckan_sync_max_packages
    seen_slugs: set[str] = set()

    # Drop stale data.gov rows from older sync strategies (e.g. package-level ZIP links).
    session.execute(delete(CatalogResource).where(CatalogResource.portal == "data_gov"))
    session.commit()

    for query in SEARCH_QUERIES:
        if count >= max_items:
            break
        after: str | None = None
        pages = 0
        while count < max_items and pages < 4:
            params: dict = {"q": query, "per_page": per_page}
            if after:
                params["after"] = after
            resp = await client.get(f"{base}/search", params=params, timeout=60.0)
            resp.raise_for_status()
            payload = resp.json()
            results = payload.get("results") or []
            if not results:
                break

            for item in results:
                if count >= max_items:
                    break
                dcat = item.get("dcat") or {}
                access = (dcat.get("accessLevel") or "").lower()
                if access and access != "public":
                    continue

                slug = item.get("slug") or item.get("identifier")
                if not slug or slug in seen_slugs:
                    continue

                title = item.get("title") or dcat.get("title") or "Dataset"
                desc = (item.get("description") or dcat.get("description") or "")[:4000]
                lic_norm, lic_raw = _resolve_license(dcat, desc)
                if not lic_norm:
                    continue

                seen_slugs.add(slug)
                org_obj = item.get("organization") or {}
                org = org_obj.get("name") if isinstance(org_obj, dict) else str(org_obj)
                org = org or item.get("publisher") or "data.gov"
                tags = item.get("keyword") or dcat.get("keyword") or []
                pkg_url = f"https://catalog.data.gov/dataset/{slug}"
                lic_display = {
                    "CC0": "CC0 1.0 — public domain dedication",
                    "US_PD": "US Public Domain",
                    "US_GOV_WORK": "US Government Work",
                    "PDDL": "Public Domain Dedication",
                }.get(lic_norm, lic_raw or lic_norm)

                rec = CatalogResource(
                    id=f"datagov:{slug}",
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
                    byte_size=None,
                    updated_at=datetime.now(timezone.utc),
                    search_text=_build_search_text(title, desc, org, tags if isinstance(tags, list) else []),
                    ingestible=False,
                )

                if settings.catalog_probe_enabled:
                    resource_url, fmt, probe = await _probe_best_url(client, dcat)
                    if resource_url:
                        rec.resource_url = resource_url
                        rec.format = probe.detected_format or fmt or "UNKNOWN"
                        apply_probe(rec, probe)
                    else:
                        apply_probe(rec, probe)
                else:
                    ranked = ranked_distributions(dcat)
                    if ranked:
                        resource_url, fmt, _ = ranked[0]
                        rec.resource_url = resource_url
                        rec.format = fmt
                        rec.ingestible = True

                if rec.ingestible:
                    ingestible += 1
                session.merge(rec)
                count += 1

            after = payload.get("after")
            pages += 1
            if not after:
                break

    session.commit()
    logger.info("data.gov Catalog API sync: %s datasets (%s ingestible)", count, ingestible)
    return count
