"""Guided explore — question-first dataset and pair suggestions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from findings_api.catalog.search_rank import catalog_quality_score, rank_catalog_rows
from findings_api.db import get_db
from findings_api.guided.loader import (
    load_guided_config,
    match_paths,
    path_by_id,
    paths_for_topic,
    tokenize,
)
from findings_api.models import CatalogResource
from findings_api.routers.search import _to_result
from findings_api.schemas import (
    CatalogResult,
    GuidedPathPair,
    GuidedSuggestResponse,
    GuidedTopicOut,
)

router = APIRouter(prefix="/guided", tags=["guided"])

_SEARCH_POOL = 400


def _enrich(row: CatalogResource, *, quality: float | None = None, why: str | None = None) -> CatalogResult:
    base = _to_result(row)
    data = base.model_dump()
    if quality is not None:
        data["quality_score"] = quality
    if why:
        data["match_reason"] = why
    return CatalogResult(**data)


def _path_to_pair(path, db: Session) -> GuidedPathPair | None:
    rows = {
        r.id: r
        for r in db.execute(
            select(CatalogResource).where(
                CatalogResource.id.in_(list(path.resource_ids)),
                CatalogResource.ingestible.is_(True),
            )
        ).scalars()
    }
    if not all(rid in rows for rid in path.resource_ids):
        return None
    return GuidedPathPair(
        path_id=path.id,
        title=path.title,
        topic=path.topic,
        quality=path.quality,
        description=path.description,
        user_intent=path.user_intent,
        resource_ids=list(path.resource_ids),
        join_hint=[{"left": l, "right": r} for l, r in path.join_hint],
        why=path.why,
        datasets=[_enrich(rows[rid], quality=catalog_quality_score(rows[rid])) for rid in path.resource_ids],
    )


@router.get("/topics", response_model=list[GuidedTopicOut])
def guided_topics():
    topics, paths = load_guided_config()
    out: list[GuidedTopicOut] = []
    for topic in topics:
        topic_paths = [p for p in paths if p.topic == topic.id]
        out.append(
            GuidedTopicOut(
                id=topic.id,
                title=topic.title,
                description=topic.description,
                icon=topic.icon,
                path_count=len(topic_paths),
            )
        )
    return out


@router.get("/paths", response_model=list[GuidedPathPair])
def guided_paths(
    topic: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """All curated paths (for explore browse), optionally filtered by topic."""
    _, all_paths = load_guided_config()
    items = paths_for_topic(topic) if topic else list(all_paths)
    pairs: list[GuidedPathPair] = []
    for path in sorted(items, key=lambda p: (p.quality != "verified", p.title)):
        pair = _path_to_pair(path, db)
        if pair:
            pairs.append(pair)
    return pairs


@router.get("/paths/{path_id}", response_model=GuidedPathPair)
def guided_path_detail(path_id: str, db: Session = Depends(get_db)):
    path = path_by_id(path_id)
    if not path:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Path not found")
    pair = _path_to_pair(path, db)
    if not pair:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Path datasets not available in catalog")
    return pair


@router.get("/suggest", response_model=GuidedSuggestResponse)
def guided_suggest(
    q: str = Query("", description="User question"),
    topic: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = q.strip()
    tokens = tokenize(query)

    matched = match_paths(query, topic=topic, limit=5)
    recommended: list[GuidedPathPair] = []
    for path, _score in matched:
        pair = _path_to_pair(path, db)
        if pair:
            recommended.append(pair)

    stmt = select(CatalogResource).where(CatalogResource.ingestible.is_(True))
    pool = db.execute(stmt.limit(_SEARCH_POOL)).scalars().all()
    ranked = rank_catalog_rows(list(pool), query if not topic else f"{topic} {' '.join(tokens)}")

    used_ids = {rid for p in recommended for rid in p.resource_ids}
    datasets: list[CatalogResult] = []
    for row, combined, quality, why in ranked:
        if row.id in used_ids:
            continue
        item = _enrich(row, quality=quality, why=why)
        item.relevance_score = round(combined, 4)
        datasets.append(item)
        if len(datasets) >= limit:
            break

    paraphrase = None
    if query:
        paraphrase = query[0].upper() + query[1:] if query else None
    elif topic:
        topics, _ = load_guided_config()
        t = next((x for x in topics if x.id == topic), None)
        if t:
            paraphrase = f"Explore {t.title.lower()} datasets and example pairings."

    fallback = None
    if not recommended and not datasets:
        fallback = (
            "We couldn't find a strong match. Try a shorter question, pick a topic below, "
            "or browse the full catalog."
        )

    return GuidedSuggestResponse(
        query=query,
        topic=topic,
        paraphrase=paraphrase,
        recommended_pairs=recommended,
        datasets=datasets,
        fallback_message=fallback,
    )
