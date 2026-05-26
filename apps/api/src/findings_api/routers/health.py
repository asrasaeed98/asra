from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from findings_api import __version__
from findings_api.config import settings
from findings_api.db import get_db
from findings_api.models import CatalogResource

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        catalog_count = int(db.scalar(select(func.count()).select_from(CatalogResource)) or 0)
    except Exception:
        catalog_count = 0
    return {
        "status": "ok",
        "service": "findings-api",
        "version": __version__,
        "app_name": settings.app_display_name,
        "catalog_count": catalog_count,
    }
