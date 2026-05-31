"""Apply probe results to catalog rows."""

from __future__ import annotations

from datetime import datetime, timezone

from findings_api.catalog.probe import ProbeResult
from findings_api.models import CatalogResource


def apply_probe(rec: CatalogResource, result: ProbeResult) -> None:
    rec.ingestible = result.ingestible
    rec.ingest_block_reason = None if result.ingestible else result.reason
    rec.detected_format = result.detected_format
    rec.probed_at = datetime.now(timezone.utc)
    if result.row_count is not None:
        rec.row_count_hint = result.row_count
    if result.columns:
        rec.columns = [{"name": name} for name in result.columns[:50]]
