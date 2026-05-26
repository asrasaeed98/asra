from __future__ import annotations

from findings_api.analysis.types import Finding

# Store up to this many ranked findings on the session; UI shows DISPLAY_TOP by default.
MAX_STORED_FINDINGS = 50
DISPLAY_TOP = 5
# Avoid five near-duplicate cards of the same test type when scores are close.
MAX_PER_TYPE_IN_TOP = 2


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
) -> list[Finding]:
    """
    Pick the top N cards for the main results view.

    Strategy (works across data.gov CSVs, World Bank APIs, etc.):
    1. Rank every finding by score = effect size × strength of evidence (−log10 p).
    2. Prefer variety: at most `max_per_type` cards per test type in the top N.
    3. Fill any leftover slots with the next highest-scoring findings.
    """
    if len(ranked) <= n:
        return list(ranked)

    selected: list[Finding] = []
    type_counts: dict[str, int] = {}

    for finding in ranked:
        if len(selected) >= n:
            break
        count = type_counts.get(finding.type, 0)
        if count >= max_per_type:
            continue
        selected.append(finding)
        type_counts[finding.type] = count + 1

    if len(selected) < n:
        picked = {f.id for f in selected}
        for finding in ranked:
            if finding.id in picked:
                continue
            selected.append(finding)
            if len(selected) >= n:
                break

    return selected[:n]
