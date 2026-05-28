"""Shared helpers for catalog sync caps (indexed vs ingestible)."""

from __future__ import annotations

from findings_api.config import settings

PENDING_PROBE_REASON = "pending probe"


def max_indexed(ingestible_cap: int, indexed_cap: int) -> int:
    """Total metadata rows to store; defaults to ingestible cap when indexed cap is 0."""
    return indexed_cap if indexed_cap > 0 else ingestible_cap


def should_probe(*, ingestible: int, ingestible_cap: int) -> bool:
    """Probe downloads only while under the ingestible target and probing is enabled."""
    return settings.catalog_probe_enabled and ingestible < ingestible_cap
