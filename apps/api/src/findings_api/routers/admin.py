from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from findings_api.catalog.sync_all import run_full_sync
from findings_api.config import settings
from findings_api.db import get_db
from findings_api.models import CatalogResource
from findings_api.schemas import SyncResponse

router = APIRouter(prefix="/admin", tags=["admin"])


class CatalogHealthResponse(BaseModel):
    total: int
    ingestible: int
    blocked: int
    by_portal: dict[str, dict[str, int]]
    top_block_reasons: list[dict[str, int | str]]


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
    """Pull data.gov (strict license) + World Bank (CC-BY, attribution) into catalog."""
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
