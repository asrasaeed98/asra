"""Explicit analysis modes: explore (one dataset) vs compare (two datasets)."""

from __future__ import annotations

from typing import Literal

AnalysisMode = Literal["explore", "compare"]


def resolve_analysis_mode(dataset_count: int) -> AnalysisMode:
    """One dataset → explore; two datasets → compare."""
    if dataset_count == 2:
        return "compare"
    return "explore"


def table_sets_for_mode(
    *,
    mode: AnalysisMode,
    table_names: list[str],
    joined_table: str | None,
    joined_ok: bool,
) -> tuple[list[str], list[str]]:
    """
    Return (context_tables, test_tables).

    context_tables — profiled for metadata, glossary, and AI context.
    test_tables — run the statistical test planner (explore or joined correlation).
    """
    if mode == "explore":
        if not table_names:
            return [], []
        return [table_names[0]], [table_names[0]]

    # compare — full per-table analysis; joined table replaces both when join succeeds.
    if joined_ok and joined_table:
        return [joined_table], [joined_table]

    return list(table_names), list(table_names)
