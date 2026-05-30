from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from findings_api.catalog.search_rank import rank_catalog_rows
from findings_api.db import get_db
from findings_api.models import CatalogResource
from findings_api.schemas import CatalogResult, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])

_SEARCH_POOL = 500


def _to_result(
    row: CatalogResource,
    *,
    relevance_score: float | None = None,
    quality_score: float | None = None,
    match_reason: str | None = None,
) -> CatalogResult:
    return CatalogResult(
        id=row.id,
        portal=row.portal,
        title=row.title,
        description=row.description,
        organization=row.organization,
        tags=row.tags or [],
        format=row.format,
        license_normalized=row.license_normalized,
        license_display=row.license_display,
        attribution_required=row.attribution_required,
        attribution_text=row.attribution_text,
        publisher=row.publisher,
        source_url=row.source_url,
        resource_url=row.resource_url,
        byte_size=row.byte_size,
        row_count_hint=row.row_count_hint,
        relevance_score=relevance_score,
        quality_score=quality_score,
        match_reason=match_reason,
    )


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query("", description="Search query"),
    portal: str | None = Query(None, description="data_gov | world_bank | fred"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = q.strip()
    stmt = select(CatalogResource).where(CatalogResource.ingestible.is_(True))
    if portal:
        stmt = stmt.where(CatalogResource.portal == portal)

    tokens = [t for t in query.lower().split() if len(t) > 1]
    if tokens:
        clauses = [CatalogResource.search_text.contains(t) for t in tokens]
        stmt = stmt.where(or_(*clauses))
    elif query:
        stmt = stmt.where(CatalogResource.search_text.contains(query.lower()))

    pool = db.execute(stmt.limit(_SEARCH_POOL)).scalars().all()
    ranked = rank_catalog_rows(list(pool), query)
    total = len(ranked)

    offset = (page - 1) * limit
    page_slice = ranked[offset : offset + limit]
    results = [
        _to_result(
            row,
            relevance_score=round(combined, 4) if query else None,
            quality_score=round(quality, 4),
            match_reason=why,
        )
        for row, combined, quality, why in page_slice
    ]

    return SearchResponse(
        query=q,
        page=page,
        limit=limit,
        total=int(total),
        results=results,
    )
