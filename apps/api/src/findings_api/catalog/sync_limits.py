"""Shared helpers for catalog sync caps (indexed vs ingestible)."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from findings_api.config import settings
from findings_api.models import CatalogResource

PENDING_PROBE_REASON = "pending probe"

# Postgres btree index row limit is ~2704 bytes; keep indexed search_text under that.
SEARCH_TEXT_MAX_BYTES = 2500


def build_search_text(title: str, desc: str, org: str, tags: list[str]) -> str:
    """Lowercase search blob for ILIKE-style queries; capped for index size."""
    text = " ".join(filter(None, [title, desc, org, " ".join(tags)])).lower()
    encoded = text.encode("utf-8")
    if len(encoded) <= SEARCH_TEXT_MAX_BYTES:
        return text
    return encoded[:SEARCH_TEXT_MAX_BYTES].decode("utf-8", errors="ignore").rstrip()


def clamp_str(value: str | None, max_len: int) -> str | None:
    """Truncate strings to fit VARCHAR columns."""
    if not value or len(value) <= max_len:
        return value
    return value[:max_len]


def max_indexed(ingestible_cap: int, indexed_cap: int) -> int:
    """Total metadata rows to store; defaults to ingestible cap when indexed cap is 0."""
    return indexed_cap if indexed_cap > 0 else ingestible_cap


def should_probe(*, ingestible: int, ingestible_cap: int) -> bool:
    """Probe downloads only while under the ingestible target and probing is enabled."""
    return settings.catalog_probe_enabled and ingestible < ingestible_cap


def prune_stale_portal_rows(
    session: Session,
    portal: str,
    seen_ids: set[str],
    *,
    id_prefix: str | None = None,
) -> int:
    """Drop portal rows missing from a completed sync pass (removed upstream)."""
    if not seen_ids:
        return 0
    conditions = [
        CatalogResource.portal == portal,
        CatalogResource.id.not_in(seen_ids),
    ]
    if id_prefix:
        conditions.append(CatalogResource.id.startswith(id_prefix))
    result = session.execute(delete(CatalogResource).where(*conditions))
    return int(result.rowcount or 0)
