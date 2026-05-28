"""Optional in-process catalog sync + daily probe schedulers."""

from __future__ import annotations

import asyncio
import logging

from findings_api.catalog.probe_batch import run_probe_batch
from findings_api.catalog.sync_all import run_full_sync
from findings_api.config import settings
from findings_api.db import get_session_factory

logger = logging.getLogger(__name__)


async def catalog_sync_loop() -> None:
    """Run full sync on an interval when catalog_sync_interval_hours > 0."""
    hours = settings.catalog_sync_interval_hours
    if hours <= 0:
        return

    interval = hours * 3600
    logger.info("Catalog sync scheduler enabled (every %s hours)", hours)

    while True:
        await asyncio.sleep(interval)
        db = get_session_factory()()
        try:
            logger.info("Scheduled catalog sync starting")
            counts = await run_full_sync(db)
            logger.info("Scheduled catalog sync complete: %s", counts)
        except Exception:
            logger.exception("Scheduled catalog sync failed")
        finally:
            db.close()


async def catalog_probe_loop() -> None:
    """Probe pending rows daily to gradually grow searchable ingestible count."""
    hours = settings.catalog_probe_interval_hours
    if hours <= 0:
        return

    interval = hours * 3600
    batch = settings.catalog_probe_batch_size
    logger.info("Catalog probe scheduler enabled (every %s hours, batch=%s)", hours, batch)

    while True:
        await asyncio.sleep(interval)
        db = get_session_factory()()
        try:
            logger.info("Scheduled probe batch starting")
            result = await run_probe_batch(db, limit=batch)
            logger.info("Scheduled probe batch complete: %s", result)
        except Exception:
            logger.exception("Scheduled probe batch failed")
        finally:
            db.close()


def start_catalog_scheduler() -> list[asyncio.Task]:
    tasks: list[asyncio.Task] = []
    if settings.catalog_sync_interval_hours > 0:
        tasks.append(asyncio.create_task(catalog_sync_loop()))
    if settings.catalog_probe_interval_hours > 0:
        tasks.append(asyncio.create_task(catalog_probe_loop()))
    return tasks
