"""Relevance and quality ranking for catalog search (technical / browse users)."""

from __future__ import annotations

import re

from findings_api.guided.loader import all_featured_resource_ids, tokenize
from findings_api.models import CatalogResource

_QUALITY_ORDER = {"verified": 3, "good": 2, "": 1}

# World Bank standard panel indicators — prefer in browse when scores tie.
_WB_CURATED_PREFIXES = (
    "wb:NY.GDP.PCAP.CD",
    "wb:SP.DYN.LE00.IN",
    "wb:EG.ELC.ACCS.ZS",
    "wb:EG.CFT.ACCS.ZS",
    "wb:SL.UEM.TOTL.ZS",
    "wb:SE.ADT.LITR.ZS",
    "wb:SI.POV.DDAY",
    "wb:IT.NET.USER.ZS",
    "fred:UNRATE",
    "fred:CPIAUCSL",
    "fred:GDP",
)

_FEATURED = all_featured_resource_ids()


def _token_hits(search_text: str, tokens: list[str]) -> tuple[int, float]:
    if not tokens:
        return 0, 0.0
    text = (search_text or "").lower()
    hits = sum(1 for t in tokens if t in text)
    # Title-weight proxy: earlier tokens in search_text often include title
    title_boost = 0.0
    for t in tokens:
        if re.search(rf"\b{re.escape(t)}\b", text[: min(len(text), 200)]):
            title_boost += 0.15
    return hits, hits / len(tokens) + title_boost


def catalog_quality_score(row: CatalogResource) -> float:
    """Static quality prior — higher = better explore / analysis candidate."""
    score = 0.0
    if row.id in _FEATURED:
        score += 0.45
    elif row.id in _WB_CURATED_PREFIXES:
        score += 0.25

    hint = row.row_count_hint or 0
    if hint >= 10_000:
        score += 0.35
    elif hint >= 1_000:
        score += 0.25
    elif hint >= 100:
        score += 0.12

    portal = row.portal or ""
    if portal == "world_bank":
        score += 0.15
    elif portal == "fred":
        score += 0.12
    elif portal == "data_gov":
        score += 0.05

    fmt = (row.format or "").upper()
    if fmt in ("CSV", "JSON_WORLDBANK", "JSON"):
        score += 0.08

    if row.columns and len(row.columns) >= 3:
        score += 0.05

    return round(min(score, 1.0), 4)


def match_reason(row: CatalogResource, tokens: list[str]) -> str | None:
    if not tokens:
        if row.id in _FEATURED:
            return "Featured explore example with verified analysis path."
        if (row.row_count_hint or 0) >= 1000:
            return "Large sample size — well suited for statistical analysis."
        return None
    title = (row.title or "").lower()
    matched = [t for t in tokens if t in title or t in (row.search_text or "")]
    if not matched:
        return None
    shown = ", ".join(matched[:4])
    extra = len(matched) - 4
    if extra > 0:
        shown += f", +{extra} more"
    return f"Matches: {shown}"


def rank_catalog_rows(
    rows: list[CatalogResource],
    query: str,
) -> list[tuple[CatalogResource, float, float, str | None]]:
    """
    Return rows sorted by combined relevance + quality.

    Each tuple: (row, combined_score, quality_score, match_reason).
    """
    tokens = tokenize(query)
    scored: list[tuple[CatalogResource, float, float, str | None]] = []
    for row in rows:
        quality = catalog_quality_score(row)
        hits, match_frac = _token_hits(row.search_text or "", tokens)
        if tokens:
            if hits == 0:
                continue
            combined = match_frac * 0.65 + quality * 0.35
        else:
            combined = quality
        reason = match_reason(row, tokens)
        scored.append((row, combined, quality, reason))

    scored.sort(key=lambda x: (x[1], x[2], x[0].title or ""), reverse=True)
    return scored
