from fastapi import APIRouter, Query

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(
    q: str = Query("", description="Search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
):
    """Catalog search — stub until CKAN sync (slice 2)."""
    return {
        "query": q,
        "page": page,
        "limit": limit,
        "total": 0,
        "results": [],
        "message": "Catalog index not populated yet. Run CKAN sync job (BUILD_ORDER slice 2).",
    }
