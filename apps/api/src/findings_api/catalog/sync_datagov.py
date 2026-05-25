"""Sync data.gov via the Catalog API (replaces legacy CKAN package_search)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

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


def _license_from_dcat(dcat: dict) -> str | None:
    lic = dcat.get("license") or ""
    if isinstance(lic, str) and lic:
        return lic
    return None


def _is_cc0_license(license_url: str | None) -> bool:
    if not license_url:
        return False
    low = license_url.lower()
    return any(m in low for m in CC0_MARKERS)


def _pick_distribution_url(dcat: dict) -> str | None:
    dists = dcat.get("distribution") or []
    if not dists:
        return None
    first = dists[0]
    if isinstance(first, dict):
        return first.get("accessURL") or first.get("downloadURL")
    if isinstance(first, str):
        return first
    return None


def _build_search_text(title: str, desc: str, org: str, tags: list[str]) -> str:
    return " ".join(filter(None, [title, desc, org, " ".join(tags)])).lower()


async def sync_datagov(session: Session, client: httpx.AsyncClient) -> int:
    base = settings.catalog_api_base.rstrip("/")
    count = 0
    per_page = min(settings.ckan_sync_rows, 25)
    max_items = settings.ckan_sync_max_packages
    after: str | None = None
    pages = 0

    while count < max_items and pages < 10:
        params: dict = {"q": "", "per_page": per_page, "sort": "last_harvested_date"}
        if after:
            params["after"] = after
        url = f"{base}/search"
        resp = await client.get(url, params=params, timeout=60.0)
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

            lic_raw = _license_from_dcat(dcat)
            if not _is_cc0_license(lic_raw):
                lic_norm = normalize_license(lic_raw)
                if not lic_norm or not is_allowed(lic_norm, "data_gov"):
                    continue
            else:
                lic_norm = "CC0"

            slug = item.get("slug") or item.get("identifier")
            if not slug:
                continue
            title = item.get("title") or dcat.get("title") or "Dataset"
            desc = (item.get("description") or dcat.get("description") or "")[:4000]
            org_obj = item.get("organization") or {}
            org = org_obj.get("name") if isinstance(org_obj, dict) else str(org_obj)
            org = org or item.get("publisher") or "data.gov"
            tags = item.get("keyword") or dcat.get("keyword") or []
            pkg_url = f"https://catalog.data.gov/dataset/{slug}"
            resource_url = _pick_distribution_url(dcat) or dcat.get("landingPage") or pkg_url

            rid = f"datagov:{slug}"
            lic_display = "CC0 1.0 — public domain dedication"
            rec = CatalogResource(
                id=rid,
                portal="data_gov",
                title=title,
                description=desc or None,
                organization=org,
                tags=tags if isinstance(tags, list) else [],
                format="DCAT",
                license_normalized=lic_norm,
                license_raw=lic_raw or lic_display,
                license_display=lic_display,
                attribution_required=attribution_required(lic_norm),
                attribution_text=default_attribution("data_gov", title, org, pkg_url),
                publisher=org,
                source_url=pkg_url,
                resource_url=resource_url,
                columns=None,
                byte_size=None,
                updated_at=datetime.now(timezone.utc),
                search_text=_build_search_text(title, desc, org, tags if isinstance(tags, list) else []),
            )
            session.merge(rec)
            count += 1

        after = payload.get("after")
        pages += 1
        if not after:
            break

    session.commit()
    logger.info("data.gov Catalog API sync: %s datasets", count)
    return count
