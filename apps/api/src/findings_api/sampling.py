"""Row limits and sample size helpers (see docs/findings-ai/SAMPLING.md)."""

from __future__ import annotations

from findings_api.config import settings


def compute_analysis_n(
    available_rows: int,
    *,
    row_cap: int | None = None,
    min_sample: int | None = None,
    sample_pct: float | None = None,
) -> int:
    cap = row_cap if row_cap is not None else settings.row_cap
    floor = min_sample if min_sample is not None else settings.min_sample
    pct = sample_pct if sample_pct is not None else settings.sample_pct
    if available_rows <= 0:
        return 0
    if available_rows <= cap:
        return available_rows
    return min(cap, max(floor, round(pct * available_rows)))


def sampling_tier(total_rows: int) -> str:
    if total_rows <= 100_000:
        return "full_ok"
    if total_rows <= 1_000_000:
        return "recommend_filter"
    return "require_filter"
