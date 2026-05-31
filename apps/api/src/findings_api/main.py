import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from findings_api import __version__
from findings_api.catalog.scheduler import start_catalog_scheduler
from findings_api.catalog.sync_all import run_full_sync
from findings_api.config import settings
from findings_api.db import get_session_factory, init_db
from findings_api.models import CatalogResource
from findings_api.routers import admin, datasets, guided, health, search, sessions
from findings_api.session_recovery import recover_stale_sessions

logger = logging.getLogger(__name__)
_display = settings.app_display_name


async def _sync_catalog_if_empty() -> None:
    """Populate search index when the DB has no datasets yet (local dev)."""
    if settings.admin_sync_token and not settings.catalog_sync_run_on_startup:
        return

    factory = get_session_factory()
    db = factory()
    try:
        count = int(db.scalar(select(func.count()).select_from(CatalogResource)) or 0)
        if count > 0:
            return
        logger.info("Catalog empty — syncing data.gov + World Bank (local dev)")
        counts = await run_full_sync(db)
        logger.info("Catalog sync complete: %s", counts)
    except Exception:
        logger.exception("Background catalog sync failed")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    factory = get_session_factory()
    db = factory()
    try:
        n = recover_stale_sessions(db)
        if n:
            logger.warning("Marked %s stale session(s) as failed on startup", n)
    finally:
        db.close()
    asyncio.create_task(_sync_catalog_if_empty())
    start_catalog_scheduler()
    yield


app = FastAPI(
    title=f"{_display} API",
    description="Open data search, trustworthy analysis, grounded chat",
    version=__version__,
    lifespan=lifespan,
)

_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["http://localhost:3000"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(search.router)
app.include_router(guided.router)
app.include_router(datasets.router)
app.include_router(sessions.router)
app.include_router(admin.router)
