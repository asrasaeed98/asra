from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from findings_api.db import get_db
from findings_api.models import CatalogResource
from findings_api.schemas import CatalogResult, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


def _to_result(row: CatalogResource) -> CatalogResult:
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
    )


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query("", description="Search query"),
    portal: str | None = Query(None, description="data_gov | world_bank | fred"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = q.strip().lower()
    stmt = select(CatalogResource).where(CatalogResource.ingestible.is_(True))
    if portal:
        stmt = stmt.where(CatalogResource.portal == portal)
    if query:
        tokens = [t for t in query.split() if len(t) > 1]
        if tokens:
            clauses = [CatalogResource.search_text.contains(t) for t in tokens]
            stmt = stmt.where(or_(*clauses))
        else:
            stmt = stmt.where(CatalogResource.search_text.contains(query))

    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    offset = (page - 1) * limit
    rows = db.execute(stmt.order_by(CatalogResource.title).offset(offset).limit(limit)).scalars().all()

    return SearchResponse(
        query=q,
        page=page,
        limit=limit,
        total=int(total),
        results=[_to_result(r) for r in rows],
    )
