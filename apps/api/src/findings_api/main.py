from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from findings_api import __version__
from findings_api.config import settings
from findings_api.db import init_db
from findings_api.routers import admin, health, search, sessions

_display = settings.app_display_name


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(search.router)
app.include_router(sessions.router)
app.include_router(admin.router)
