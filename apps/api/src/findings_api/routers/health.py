from fastapi import APIRouter

from findings_api import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "findings-api", "version": __version__}
