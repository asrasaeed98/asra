"""CLI entry point for scheduled catalog sync (cron, Railway, GitHub Actions)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

import httpx

from findings_api.catalog.probe_batch import run_probe_batch
from findings_api.catalog.sync_all import run_full_sync
from findings_api.catalog.sync_nyc_open_data import sync_nyc_open_data
from findings_api.config import settings
from findings_api.db import get_session_factory, init_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def _run_sync() -> dict[str, int]:
    init_db()
    db = get_session_factory()()
    try:
        return await run_full_sync(db)
    finally:
        db.close()


async def _run_sync_nyc() -> int:
    init_db()
    db = get_session_factory()()
    try:
        async with httpx.AsyncClient(follow_redirects=True, trust_env=False) as client:
            return await sync_nyc_open_data(db, client)
    finally:
        db.close()


async def _run_probe(limit: int) -> dict[str, int]:
    init_db()
    db = get_session_factory()()
    try:
        return await run_probe_batch(db, limit=limit)
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Findings catalog sync utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("sync", help="Full catalog sync (data.gov + World Bank + FRED)")

    sub.add_parser("sync-nyc", help="NYC Open Data sync only (Socrata, separate from main sync)")

    probe_p = sub.add_parser("probe", help="Probe a batch of pending catalog rows")
    probe_p.add_argument(
        "--limit",
        type=int,
        default=settings.catalog_probe_batch_size,
        help="Max rows to probe this run",
    )

    grow_p = sub.add_parser(
        "grow",
        help="Daily growth: probe pending rows (alias for probe with daily defaults)",
    )
    grow_p.add_argument(
        "--limit",
        type=int,
        default=settings.catalog_probe_batch_size,
        help="Max rows to probe this run",
    )

    args = parser.parse_args(argv)

    if args.command == "sync":
        logger.info("Starting full catalog sync")
        counts = asyncio.run(_run_sync())
        logger.info("Sync complete: %s", counts)
        print("SYNC_DONE", counts)
        return 0

    if args.command == "sync-nyc":
        logger.info("Starting NYC Open Data catalog sync")
        count = asyncio.run(_run_sync_nyc())
        logger.info("NYC sync complete: %s datasets indexed", count)
        print("NYC_SYNC_DONE", count)
        return 0

    if args.command == "probe":
        logger.info("Starting probe batch (limit=%s)", args.limit)
        result = asyncio.run(_run_probe(args.limit))
        logger.info("Probe batch complete: %s", result)
        print("PROBE_DONE", result)
        return 0

    if args.command == "grow":
        logger.info("Daily catalog grow — probing up to %s pending rows", args.limit)
        result = asyncio.run(_run_probe(args.limit))
        logger.info("Grow complete: %s", result)
        print("GROW_DONE", result)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
