from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from findings_api.catalog.search_rank import rank_catalog_rows
from findings_api.catalog.topic_classifier import count_primary_themes, filter_by_topic
from findings_api.catalog.topic_config import load_topics, topic_by_id
from findings_api.db import get_db
from findings_api.guided.loader import load_paths
from findings_api.models import CatalogResource
from findings_api.schemas import CatalogResult, SearchResponse, SearchTopicOut

router = APIRouter(prefix="/search", tags=["search"])

_SEARCH_POOL = 500
_TOPIC_SEARCH_POOL = 2000


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
        columns=row.columns or [],
        relevance_score=relevance_score,
        quality_score=quality_score,
        match_reason=match_reason,
    )


@router.get("/topics", response_model=list[SearchTopicOut])
def search_topics(db: Session = Depends(get_db)):
    """Browse themes with ingestible dataset counts for the search empty state."""
    rows = db.execute(
        select(CatalogResource).where(CatalogResource.ingestible.is_(True))
    ).scalars().all()
    dataset_counts = count_primary_themes(list(rows))
    path_counts: dict[str, int] = {}
    for path in load_paths():
        path_counts[path.topic] = path_counts.get(path.topic, 0) + 1

    return [
        SearchTopicOut(
            id=topic.id,
            title=topic.title,
            description=topic.description,
            icon=topic.icon,
            dataset_count=dataset_counts.get(topic.id, 0),
            path_count=path_counts.get(topic.id, 0),
        )
        for topic in load_topics()
    ]


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query("", description="Search query"),
    topic: str | None = Query(None, description="Theme filter: economy | health | environment | education | poverty"),
    portal: str | None = Query(None, description="data_gov | world_bank | fred | nyc_open_data"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = q.strip()
    topic_id = (topic or "").strip() or None
    if topic_id and topic_by_id(topic_id) is None:
        raise HTTPException(status_code=400, detail=f"Unknown topic '{topic_id}'")

    stmt = select(CatalogResource).where(CatalogResource.ingestible.is_(True))
    if portal:
        stmt = stmt.where(CatalogResource.portal == portal)

    tokens = [t for t in query.lower().split() if len(t) > 1]
    if tokens:
        clauses = [CatalogResource.search_text.contains(t) for t in tokens]
        stmt = stmt.where(or_(*clauses))
    elif query:
        stmt = stmt.where(CatalogResource.search_text.contains(query.lower()))

    pool_limit = _TOPIC_SEARCH_POOL if topic_id else _SEARCH_POOL
    pool = db.execute(stmt.limit(pool_limit)).scalars().all()

    if topic_id:
        pool = filter_by_topic(list(pool), topic_id)

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
        topic=topic_id,
        page=page,
        limit=limit,
        total=int(total),
        results=results,
    )
