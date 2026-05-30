"""Classify catalog resources into canonical browse/explore themes."""

from __future__ import annotations

from functools import lru_cache

from findings_api.catalog.topic_config import load_topics, wb_tag_to_topic_id
from findings_api.models import CatalogResource

# Minimum score to include a theme on a resource.
_MATCH_THRESHOLD = 1.0

# Strong signal when a World Bank topic tag maps cleanly.
_WB_TAG_SCORE = 3.0

# Keyword hit weights (title weighted higher than description/search/tags).
_TITLE_KEYWORD_SCORE = 2.0
_BODY_KEYWORD_SCORE = 1.0


@lru_cache(maxsize=1)
def _keyword_index() -> tuple[tuple[str, str], ...]:
    """Flat (topic_id, keyword) pairs for scanning."""
    pairs: list[tuple[str, str]] = []
    for topic in load_topics():
        for keyword in topic.keywords:
            if keyword:
                pairs.append((topic.id, keyword))
    return tuple(pairs)


def classify_resource(row: CatalogResource) -> tuple[str, ...]:
    """Return matching theme ids for a catalog row, strongest first."""
    scores: dict[str, float] = {}

    for tag in row.tags or []:
        topic_id = wb_tag_to_topic_id(str(tag))
        if topic_id:
            scores[topic_id] = scores.get(topic_id, 0.0) + _WB_TAG_SCORE

    title = (row.title or "").lower()
    body = " ".join(
        part
        for part in (
            row.description or "",
            row.search_text or "",
            " ".join(str(t) for t in (row.tags or [])),
        )
        if part
    ).lower()

    for topic_id, keyword in _keyword_index():
        if keyword in title:
            scores[topic_id] = scores.get(topic_id, 0.0) + _TITLE_KEYWORD_SCORE
        elif keyword in body:
            scores[topic_id] = scores.get(topic_id, 0.0) + _BODY_KEYWORD_SCORE

    matched = [(tid, score) for tid, score in scores.items() if score >= _MATCH_THRESHOLD]
    matched.sort(key=lambda item: (-item[1], item[0]))
    return tuple(tid for tid, _ in matched)


def primary_theme(row: CatalogResource) -> str | None:
    themes = classify_resource(row)
    return themes[0] if themes else None


def resource_matches_topic(row: CatalogResource, topic_id: str) -> bool:
    return topic_id in classify_resource(row)


def filter_by_topic(rows: list[CatalogResource], topic_id: str) -> list[CatalogResource]:
    return [row for row in rows if resource_matches_topic(row, topic_id)]


def count_primary_themes(rows: list[CatalogResource]) -> dict[str, int]:
    """Count ingestible datasets by primary theme id."""
    counts = {topic.id: 0 for topic in load_topics()}
    for row in rows:
        primary = primary_theme(row)
        if primary and primary in counts:
            counts[primary] += 1
    return counts

