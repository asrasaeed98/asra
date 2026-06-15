from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from findings_api.catalog.sync_all import run_full_sync
from findings_api.catalog.probe_batch import run_probe_batch
from findings_api.config import settings
from findings_api.db import get_db
from findings_api.models import AnalysisSession, ApiUsage, CatalogResource
from findings_api.ops_dashboard import build_ops_dashboard
from findings_api.schemas import SyncResponse

router = APIRouter(prefix="/admin", tags=["admin"])


class CatalogHealthResponse(BaseModel):
    total: int
    ingestible: int
    blocked: int
    by_portal: dict[str, dict[str, int]]
    top_block_reasons: list[dict[str, int | str]]


class ProbeBatchResponse(BaseModel):
    probed: int
    newly_ingestible: int


class RunSnapshotSession(BaseModel):
    id: str
    status: str
    phase: str
    message: str | None = None
    percent: int
    error: str | None = None
    resource_count: int
    created_at: str
    updated_at: str
    duration_sec: float | None = None


class RunSnapshotUsage(BaseModel):
    month: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    calls: int


class RunSnapshotResponse(BaseModel):
    fetched_at: str
    summary: dict[str, int | dict[str, int]]
    sessions: list[RunSnapshotSession]
    api_usage: list[RunSnapshotUsage]


def _check_admin(authorization: str | None = Header(default=None)) -> None:
    token = settings.admin_sync_token
    if not token:
        return
    if not authorization or authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")


@router.post("/sync", response_model=SyncResponse)
async def sync_catalog(
    db: Session = Depends(get_db),
    _: None = Depends(_check_admin),
):
    """Pull data.gov Catalog API + World Bank + FRED into catalog."""
    try:
        counts = await run_full_sync(db)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Catalog sync failed: {exc}") from exc
    total = sum(counts.values())
    return SyncResponse(
        indexed=counts,
        message=(
            f"Indexed {total} resources. Search shows ingestible datasets only — "
            f"see GET /admin/catalog/health for probe results."
        ),
    )


@router.post("/catalog/probe-batch", response_model=ProbeBatchResponse)
async def probe_catalog_batch(
    limit: int = settings.catalog_probe_batch_size,
    db: Session = Depends(get_db),
    _: None = Depends(_check_admin),
):
    """Probe pending catalog rows (metadata indexed without download verification)."""
    if limit < 1 or limit > 5000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 5000")
    try:
        result = await run_probe_batch(db, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Probe batch failed: {exc}") from exc
    return ProbeBatchResponse(**result)


@router.get("/runs/snapshot", response_model=RunSnapshotResponse)
def runs_snapshot(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: None = Depends(_check_admin),
):
    """Recent analysis sessions and AI usage for ops dashboards."""
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200")

    rows = (
        db.execute(
            select(AnalysisSession).order_by(AnalysisSession.created_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )
    by_status: dict[str, int] = {}
    sessions: list[RunSnapshotSession] = []
    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1
        duration = None
        if row.created_at and row.updated_at:
            duration = (row.updated_at - row.created_at).total_seconds()
        sessions.append(
            RunSnapshotSession(
                id=row.id,
                status=row.status,
                phase=row.phase,
                message=row.message,
                percent=row.percent,
                error=row.error,
                resource_count=len(row.resource_ids or []),
                created_at=row.created_at.isoformat() if row.created_at else "",
                updated_at=row.updated_at.isoformat() if row.updated_at else "",
                duration_sec=duration,
            )
        )

    usage_rows = (
        db.execute(select(ApiUsage).order_by(ApiUsage.month.desc()).limit(6)).scalars().all()
    )
    api_usage = [
        RunSnapshotUsage(
            month=u.month,
            tokens_in=u.tokens_in,
            tokens_out=u.tokens_out,
            cost_usd=u.cost_usd,
            calls=u.calls,
        )
        for u in usage_rows
    ]

    return RunSnapshotResponse(
        fetched_at=datetime.now(timezone.utc).isoformat(),
        summary={
            "total_recent": len(sessions),
            "by_status": by_status,
        },
        sessions=sessions,
        api_usage=api_usage,
    )


@router.get("/ops/dashboard")
def ops_dashboard(
    limit: int = 200,
    days: int = 30,
    db: Session = Depends(get_db),
    _: None = Depends(_check_admin),
):
    """Rich ops metrics for Cursor Canvas and admin tooling."""
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")
    return build_ops_dashboard(db, limit=limit, days=days)


@router.get("/catalog/health", response_model=CatalogHealthResponse)
def catalog_health(
    db: Session = Depends(get_db),
    _: None = Depends(_check_admin),
):
    """Summarize catalog quality after sync probes."""
    rows = db.execute(select(CatalogResource)).scalars().all()
    by_portal: dict[str, dict[str, int]] = {}
    reasons: dict[str, int] = {}
    ingestible = 0
    for row in rows:
        portal_stats = by_portal.setdefault(
            row.portal, {"total": 0, "ingestible": 0, "blocked": 0}
        )
        portal_stats["total"] += 1
        if row.ingestible:
            ingestible += 1
            portal_stats["ingestible"] += 1
        else:
            portal_stats["blocked"] += 1
            reason = row.ingest_block_reason or "unknown"
            reasons[reason] = reasons.get(reason, 0) + 1

    top_block_reasons = [
        {"reason": reason, "count": count}
        for reason, count in sorted(reasons.items(), key=lambda item: item[1], reverse=True)[:10]
    ]
    return CatalogHealthResponse(
        total=len(rows),
        ingestible=ingestible,
        blocked=len(rows) - ingestible,
        by_portal=by_portal,
        top_block_reasons=top_block_reasons,
    )
