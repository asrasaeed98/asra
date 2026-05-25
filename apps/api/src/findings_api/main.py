from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from findings_api.config import settings
from findings_api.routers import health, search, sessions

app = FastAPI(
    title="Findings.ai API",
    description="Phase 1 — open data search, analysis, and grounded chat",
    version="0.1.0",
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
