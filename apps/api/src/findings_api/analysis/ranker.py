from __future__ import annotations

from findings_api.analysis.profile import is_geo_column
from findings_api.analysis.types import Finding

# Store up to this many ranked findings on the session; UI shows DISPLAY_TOP by default.
MAX_STORED_FINDINGS = 50
DISPLAY_TOP = 5
# Avoid five near-duplicate cards of the same test type when scores are close.
MAX_PER_TYPE_IN_TOP = 2
_JOINED_CORRELATION_BOOST = 2.5


def _is_geo_group_comparison(finding: Finding) -> bool:
    return (
        finding.type == "group_comparison"
        and len(finding.columns) >= 2
        and is_geo_column(finding.columns[1])
    )


def apply_ranking_context(
    findings: list[Finding],
    *,
    joined: bool = False,
) -> list[Finding]:
    """Adjust scores so joined cross-measure correlations lead the results page."""
    if not joined:
        return findings
    for finding in findings:
        if finding.type == "spearman_correlation":
            finding.score *= _JOINED_CORRELATION_BOOST
        elif _is_geo_group_comparison(finding):
            finding.score *= 0.05
        elif finding.type == "time_trend":
            finding.score *= 0.6
    return findings


def rank_findings(findings: list[Finding], *, limit: int | None = MAX_STORED_FINDINGS) -> list[Finding]:
    """Dedupe, score-sort, and assign stable ids. Returns the full ranked list (capped for storage)."""
    deduped: dict[tuple, Finding] = {}
    for f in findings:
        key = (f.type, tuple(sorted(f.columns)), tuple(sorted(f.datasets)))
        existing = deduped.get(key)
        if existing is None or f.score > existing.score:
            deduped[key] = f
    ranked = sorted(deduped.values(), key=lambda x: x.score, reverse=True)
    if limit is not None:
        ranked = ranked[:limit]
    for i, finding in enumerate(ranked, start=1):
        finding.id = f"f_{i}"
    return ranked


def select_display_findings(
    ranked: list[Finding],
    n: int = DISPLAY_TOP,
    *,
    max_per_type: int = MAX_PER_TYPE_IN_TOP,
    joined: bool = False,
) -> list[Finding]:
    """
    Pick the top N cards for the main results view.

    Strategy (works across data.gov CSVs, World Bank APIs, etc.):
    1. Rank every finding by score = effect size × strength of evidence (−log10 p).
    2. When two datasets were joined, lead with the cross-measure correlation.
    3. Prefer variety: at most `max_per_type` cards per test type in the top N.
    4. Fill any leftover slots with the next highest-scoring findings.
    """
    if not ranked:
        return []

    pool = list(ranked)
    selected: list[Finding] = []

    if joined:
        correlations = [f for f in pool if f.type == "spearman_correlation"]
        if correlations:
            lead = correlations[0]
            selected.append(lead)
            pool = [f for f in pool if f.id != lead.id]

    if len(pool) <= n - len(selected):
        selected.extend(pool)
        return selected[:n]

    type_counts: dict[str, int] = {}
    for f in selected:
        type_counts[f.type] = type_counts.get(f.type, 0) + 1

    for finding in pool:
        if len(selected) >= n:
            break
        count = type_counts.get(finding.type, 0)
        if count >= max_per_type:
            continue
        if joined and _is_geo_group_comparison(finding):
            continue
        selected.append(finding)
        type_counts[finding.type] = count + 1

    if len(selected) < n:
        picked = {f.id for f in selected}
        for finding in pool:
            if finding.id in picked:
                continue
            if joined and _is_geo_group_comparison(finding):
                continue
            selected.append(finding)
            if len(selected) >= n:
                break

    return selected[:n]
