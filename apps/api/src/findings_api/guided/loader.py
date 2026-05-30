"""Load curated explore paths from paths.yaml; themes from catalog/topics.yaml."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from findings_api.catalog.topic_config import CatalogTopic, load_topics

_PATHS_FILE = Path(__file__).resolve().parent / "paths.yaml"

# Backwards-compatible alias used in guided router/tests.
GuidedTopic = CatalogTopic

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "in",
        "on",
        "for",
        "to",
        "with",
        "is",
        "are",
        "do",
        "does",
        "how",
        "what",
        "why",
        "when",
        "where",
        "my",
        "me",
        "i",
        "we",
        "about",
        "between",
        "relate",
        "related",
        "relationship",
        "compare",
        "vs",
        "versus",
    }
)


@dataclass(frozen=True)
class GuidedPath:
    id: str
    title: str
    topic: str
    quality: str
    description: str
    user_intent: str
    question_patterns: tuple[str, ...]
    resource_ids: tuple[str, ...]
    join_hint: tuple[tuple[str, str], ...]
    why: str

    @property
    def is_pair(self) -> bool:
        return len(self.resource_ids) >= 2


def tokenize(text: str) -> list[str]:
    raw = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [t for t in raw if len(t) > 1 and t not in _STOPWORDS]


@lru_cache(maxsize=1)
def load_paths() -> tuple[GuidedPath, ...]:
    data = yaml.safe_load(_PATHS_FILE.read_text(encoding="utf-8")) or {}
    paths: list[GuidedPath] = []
    for p in data.get("paths") or []:
        join_hint: list[tuple[str, str]] = []
        for item in p.get("join_hint") or []:
            if isinstance(item, dict):
                left = str(item.get("left") or "").strip()
                right = str(item.get("right") or "").strip()
                if left and right:
                    join_hint.append((left, right))
        paths.append(
            GuidedPath(
                id=str(p["id"]),
                title=str(p["title"]),
                topic=str(p.get("topic") or "general"),
                quality=str(p.get("quality") or "good"),
                description=str(p.get("description") or ""),
                user_intent=str(p.get("user_intent") or ""),
                question_patterns=tuple(str(x).lower() for x in (p.get("question_patterns") or [])),
                resource_ids=tuple(str(x) for x in (p.get("resource_ids") or [])),
                join_hint=tuple(join_hint),
                why=str(p.get("why") or ""),
            )
        )
    return tuple(paths)


def load_guided_config() -> tuple[tuple[CatalogTopic, ...], tuple[GuidedPath, ...]]:
    return load_topics(), load_paths()


def all_featured_resource_ids() -> frozenset[str]:
    ids: set[str] = set()
    for path in load_paths():
        ids.update(path.resource_ids)
    return frozenset(ids)


def paths_for_topic(topic_id: str) -> list[GuidedPath]:
    return [p for p in load_paths() if p.topic == topic_id]


def match_paths(query: str, *, topic: str | None = None, limit: int = 5) -> list[tuple[GuidedPath, float]]:
    """Score curated paths against a question or topic filter."""
    paths = load_paths()
    q = (query or "").strip().lower()
    tokens = tokenize(q)

    scored: list[tuple[GuidedPath, float]] = []
    for path in paths:
        if topic and path.topic != topic:
            continue
        score = 0.0
        if not q and not topic:
            score = _quality_weight(path.quality)
        elif not q and topic:
            score = _quality_weight(path.quality) + 0.5
        else:
            for pattern in path.question_patterns:
                if pattern in q:
                    score += 1.5
                pattern_tokens = tokenize(pattern)
                overlap = len(set(tokens) & set(pattern_tokens))
                score += overlap * 0.35
            for token in tokens:
                if token in path.title.lower() or token in path.description.lower():
                    score += 0.2
        score += _quality_weight(path.quality)
        if score > 0.05:
            scored.append((path, score))

    scored.sort(key=lambda x: (x[1], _quality_weight(x[0].quality)), reverse=True)
    return scored[:limit]


def _quality_weight(quality: str) -> float:
    return {"verified": 0.5, "good": 0.25}.get(quality.lower(), 0.1)


def path_by_id(path_id: str) -> GuidedPath | None:
    for path in load_paths():
        if path.id == path_id:
            return path
    return None
