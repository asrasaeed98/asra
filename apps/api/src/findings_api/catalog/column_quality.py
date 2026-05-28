"""Detect generic / unusable column names before indexing a dataset."""

from __future__ import annotations

import re

# column1, column08, col_2, field3, var4, Unnamed: 0, _1, x12
_GENERIC = re.compile(
    r"^(?:"
    r"column\s*_?\s*\d+|"
    r"col\s*_?\s*\d+|"
    r"field\s*_?\s*\d+|"
    r"var\s*_?\s*\d+|"
    r"f\s*\d+|"
    r"x\s*\d+|"
    r"unnamed:?\s*\d+|"
    r"_+\d+"
    r")$",
    re.IGNORECASE,
)

# Single-letter headers except common meaningful ones
_SINGLE_LETTER_OK = frozenset({"n", "x", "y", "id"})


def is_generic_column(name: str) -> bool:
    raw = (name or "").strip()
    if not raw:
        return True
    if _GENERIC.match(raw):
        return True
    if len(raw) == 1 and raw.lower() not in _SINGLE_LETTER_OK:
        return True
    # Purely numeric header (often a sign the CSV has no real header row)
    if raw.isdigit():
        return True
    return False


def score_columns(columns: list[str]) -> tuple[bool, str, dict[str, int]]:
    """Return (acceptable, reason, stats)."""
    if not columns:
        return False, "no columns detected", {"total": 0, "meaningful": 0, "generic": 0}

    meaningful = [c for c in columns if not is_generic_column(c)]
    generic = len(columns) - len(meaningful)
    stats = {"total": len(columns), "meaningful": len(meaningful), "generic": generic}

    if len(meaningful) < 2:
        return (
            False,
            f"only {len(meaningful)} meaningful column name(s) — headers look generic "
            f"(e.g. column1, column08); need at least 2 descriptive fields",
            stats,
        )

    generic_ratio = generic / len(columns)
    if generic_ratio >= 0.5:
        return (
            False,
            f"{generic} of {len(columns)} columns have generic names — "
            "dataset likely lacks a proper header row",
            stats,
        )

    return True, "ok", stats
