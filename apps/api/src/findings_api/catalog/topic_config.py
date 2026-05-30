"""Shared catalog/explore theme definitions (topics.yaml)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

_TOPICS_FILE = Path(__file__).resolve().parent / "topics.yaml"


@dataclass(frozen=True)
class CatalogTopic:
    id: str
    title: str
    description: str
    icon: str = "chart"
    wb_tags: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()


def _normalize_tag(value: str) -> str:
    return (value or "").strip().casefold()


@lru_cache(maxsize=1)
def load_topics() -> tuple[CatalogTopic, ...]:
    data = yaml.safe_load(_TOPICS_FILE.read_text(encoding="utf-8")) or {}
    topics: list[CatalogTopic] = []
    for item in data.get("topics") or []:
        topics.append(
            CatalogTopic(
                id=str(item["id"]),
                title=str(item["title"]),
                description=str(item.get("description") or ""),
                icon=str(item.get("icon") or "chart"),
                wb_tags=tuple(str(t) for t in (item.get("wb_tags") or [])),
                keywords=tuple(str(k).lower() for k in (item.get("keywords") or [])),
            )
        )
    return tuple(topics)


def topic_by_id(topic_id: str) -> CatalogTopic | None:
    needle = (topic_id or "").strip()
    for topic in load_topics():
        if topic.id == needle:
            return topic
    return None


def all_topic_ids() -> frozenset[str]:
    return frozenset(t.id for t in load_topics())


def wb_tag_to_topic_id(tag: str) -> str | None:
    """Map a World Bank topic label to a canonical theme id."""
    normalized = _normalize_tag(tag)
    if not normalized:
        return None
    for topic in load_topics():
        for wb_tag in topic.wb_tags:
            if _normalize_tag(wb_tag) == normalized:
                return topic.id
    return None
