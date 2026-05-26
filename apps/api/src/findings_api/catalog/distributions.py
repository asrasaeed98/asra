"""Pick the best tabular download URL from DCAT distributions."""

from __future__ import annotations


def distribution_url(dist: dict) -> str | None:
    if not isinstance(dist, dict):
        return None
    return dist.get("downloadURL") or dist.get("accessURL")


def distribution_format_hint(dist: dict, url: str) -> str:
    fmt = (dist.get("format") or dist.get("mediaType") or "").upper()
    low = url.lower()
    if "CSV" in fmt or low.endswith(".csv"):
        return "CSV"
    if "JSON" in fmt or low.endswith(".json"):
        return "JSON"
    if fmt:
        return fmt.split("/")[-1][:32]
    if low.endswith(".csv"):
        return "CSV"
    if low.endswith(".json"):
        return "JSON"
    return "UNKNOWN"


def score_distribution(dist: dict) -> int:
    """Higher score = more likely to be a direct tabular download."""
    url = (distribution_url(dist) or "").lower()
    if not url:
        return -100

    score = 0
    if dist.get("downloadURL"):
        score += 25
    fmt = (dist.get("format") or dist.get("mediaType") or "").lower()

    if url.endswith(".csv") or url.endswith(".csv?"):
        score += 50
    if url.endswith(".json") or url.endswith(".json?"):
        score += 45
    if "csv" in fmt or "/csv" in url:
        score += 40
    if "json" in fmt:
        score += 35
    if url.endswith(".tsv") or "tab-separated" in fmt:
        score += 30

    blocked = (".zip", ".gz", ".gdb", ".pdf", ".html", ".htm", ".xlsx", ".xls", ".shp", ".kml", ".kmz")
    if any(ext in url for ext in blocked):
        score -= 60

    # Deprioritize portal landing pages (no file extension, shallow path)
    if not any(url.endswith(ext) for ext in (".csv", ".json", ".tsv", ".txt")):
        if url.count("/") <= 4 and "download" not in url and "api/" not in url:
            score -= 35

    return score


def ranked_distributions(dcat: dict) -> list[tuple[str, str, int]]:
    """Return (url, format_hint, score) sorted best-first."""
    dists = dcat.get("distribution") or []
    ranked: list[tuple[str, str, int]] = []
    for dist in dists:
        if not isinstance(dist, dict):
            continue
        url = distribution_url(dist)
        if not url:
            continue
        ranked.append((url, distribution_format_hint(dist, url), score_distribution(dist)))
    ranked.sort(key=lambda item: item[2], reverse=True)
    return ranked
