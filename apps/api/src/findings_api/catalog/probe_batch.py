"""Batch-probe catalog rows that were indexed without a download probe."""

from __future__ import annotations

import logging

import httpx
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from findings_api.catalog.probe import probe_url
from findings_api.catalog.quality import apply_probe
from findings_api.catalog.sync_limits import PENDING_PROBE_REASON
from findings_api.config import settings
from findings_api.models import CatalogResource

logger = logging.getLogger(__name__)

RETRYABLE_REASONS = (
    PENDING_PROBE_REASON,
    "no distribution URL",
)


async def run_probe_batch(session: Session, *, limit: int | None = None) -> dict[str, int]:
    """Probe up to `limit` catalog rows waiting for verification."""
    batch = limit if limit is not None else settings.catalog_probe_batch_size
    stmt = (
        select(CatalogResource)
        .where(
            CatalogResource.ingestible.is_(False),
            or_(
                CatalogResource.ingest_block_reason == PENDING_PROBE_REASON,
                CatalogResource.ingest_block_reason.in_(RETRYABLE_REASONS),
            ),
        )
        .order_by(CatalogResource.updated_at.asc())
        .limit(batch)
    )
    rows = session.execute(stmt).scalars().all()
    probed = 0
    newly_ingestible = 0

    async with httpx.AsyncClient(follow_redirects=True, trust_env=False) as client:
        for row in rows:
            if not row.resource_url:
                row.ingest_block_reason = "no distribution URL"
                session.merge(row)
                probed += 1
                continue
            result = await probe_url(row.resource_url, client=client, portal=row.portal)
            apply_probe(row, result)
            session.merge(row)
            session.flush()
            probed += 1
            if row.ingestible:
                newly_ingestible += 1

    session.commit()
    logger.info(
        "Probe batch: %s checked (%s newly ingestible)",
        probed,
        newly_ingestible,
    )
    return {"probed": probed, "newly_ingestible": newly_ingestible}
