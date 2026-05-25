"""Sync data.gov CKAN packages (strict CC0 / public domain only)."""

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


def _build_search_text(title: str, desc: str, org: str, tags: list[str]) -> str:
    return " ".join(filter(None, [title, desc, org, " ".join(tags)])).lower()


def _package_license(pkg: dict) -> str | None:
    for key in ("license_title", "license_id", "license"):
        val = pkg.get(key)
        if val:
            return str(val)
    for extra in pkg.get("extras") or []:
        if extra.get("key") in ("license", "license_id", "license_title"):
            return str(extra.get("value") or "")
    return None


def _allowed_formats(fmt: str | None) -> bool:
    if not fmt:
        return False
    f = fmt.upper()
    return f in ("CSV", "JSON", "XLS", "XLSX", "TEXT/CSV", "APPLICATION/JSON")


async def sync_ckan(session: Session, client: httpx.AsyncClient) -> int:
    """Search CKAN and upsert strict-license resources."""
    base = settings.data_gov_ckan_api.rstrip("/")
    count = 0
    rows = min(settings.ckan_sync_rows, 100)
    max_packages = settings.ckan_sync_max_packages

    # Bias toward open licenses in query
    search_url = f"{base}/package_search"
    params = {
        "q": "license_id:cc-zero OR license_id:cc0 OR license_id:us-pd",
        "rows": rows,
        "start": 0,
    }
    resp = await client.get(search_url, params=params, timeout=60.0)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("result", {}).get("results", [])[:max_packages]

    for pkg in results:
        pkg_id = pkg.get("id") or pkg.get("name")
        if not pkg_id:
            continue

        show_url = f"{base}/package_show"
        show_resp = await client.get(show_url, params={"id": pkg_id}, timeout=60.0)
        if show_resp.status_code != 200:
            continue
        full = show_resp.json().get("result", {})
        lic_raw = _package_license(full)
        lic_norm = normalize_license(lic_raw)
        if not is_allowed(lic_norm, "data_gov"):
            continue

        org = (full.get("organization") or {}).get("title") or "data.gov"
        title = full.get("title") or pkg_id
        desc = (full.get("notes") or "")[:4000]
        tags = [t.get("name", "") for t in full.get("tags") or [] if t.get("name")]
        pkg_url = f"https://catalog.data.gov/dataset/{full.get('name') or pkg_id}"

        for res in full.get("resources") or []:
            fmt = res.get("format") or ""
            if not _allowed_formats(fmt):
                continue
            url = res.get("url")
            if not url:
                continue

            res_id = res.get("id") or url
            rid = f"ckan:{pkg_id}:{res_id}"
            lic_display = {
                "CC0": "CC0 1.0 — public domain dedication",
                "US_PD": "US Public Domain",
                "US_GOV_WORK": "US Government Work",
                "PDDL": "Public Domain Dedication",
            }.get(lic_norm or "", lic_raw or "Open")

            attr = default_attribution("data_gov", title, org, pkg_url)
            rec = CatalogResource(
                id=rid,
                portal="data_gov",
                title=f"{title} ({fmt})",
                description=desc or None,
                organization=org,
                tags=tags,
                format=fmt.upper()[:32],
                license_normalized=lic_norm or "CC0",
                license_raw=lic_raw,
                license_display=lic_display,
                attribution_required=attribution_required(lic_norm),
                attribution_text=attr,
                publisher=org,
                source_url=pkg_url,
                resource_url=url,
                columns=None,
                byte_size=res.get("size"),
                updated_at=datetime.now(timezone.utc),
                search_text=_build_search_text(title, desc, org, tags),
            )
            session.merge(rec)
            count += 1

    session.commit()
    logger.info("CKAN sync: %s resources", count)
    return count
