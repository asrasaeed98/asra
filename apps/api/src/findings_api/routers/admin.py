from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from findings_api.catalog.sync_all import run_full_sync
from findings_api.config import settings
from findings_api.db import get_db
from findings_api.schemas import SyncResponse

router = APIRouter(prefix="/admin", tags=["admin"])


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
    counts = await run_full_sync(db)
    total = sum(counts.values())
    return SyncResponse(
        indexed=counts,
        message=f"Indexed {total} resources. data_gov uses CC0/PD only; world_bank requires attribution.",
    )
