from fastapi import APIRouter

from findings_api import __version__
from findings_api.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "findings-api",
        "version": __version__,
        "app_name": settings.app_display_name,
    }
