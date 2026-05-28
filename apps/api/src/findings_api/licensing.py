"""License normalization and ingest gate."""

from __future__ import annotations

# No attribution required beyond provenance UI
ALLOWED_STRICT = frozenset({"CC0", "US_PD", "US_GOV_WORK", "PDDL"})

# CC-BY allowed only from World Bank portal (mandatory attribution on record)
ALLOWED_WITH_ATTRIBUTION = frozenset({"CC_BY"})

_RAW_TO_NORMALIZED: dict[str, str] = {
    "cc0": "CC0",
    "cc0-1.0": "CC0",
    "cc-zero": "CC0",
    "cc-zero-1.0": "CC0",
    "us-pd": "US_PD",
    "us-public-domain": "US_PD",
    "cc-by": "CC_BY",
    "cc-by-4.0": "CC_BY",
    "cc-by-4": "CC_BY",
}


def normalize_license(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    key = str(raw).strip().lower()
    if key in _RAW_TO_NORMALIZED:
        return _RAW_TO_NORMALIZED[key]
    if "creativecommons.org/publicdomain/zero" in key or "creative commons zero" in key or key == "cc0":
        return "CC0"
    if "usa.gov/publicdomain" in key or "publicdomain/label" in key:
        return "US_PD"
    if "usa.gov/government-works" in key or "government-works" in key:
        return "US_GOV_WORK"
    if "public domain" in key:
        return "US_PD"
    if "government work" in key or "us government" in key:
        return "US_GOV_WORK"
    if "cc-by" in key or "creative commons attribution" in key:
        return "CC_BY"
    return None


def is_allowed(normalized: str | None, portal: str) -> bool:
    if not normalized:
        return False
    if normalized in ALLOWED_STRICT:
        return True
    if portal in ("world_bank",) and normalized in ALLOWED_WITH_ATTRIBUTION:
        return True
    return False


def attribution_required(normalized: str | None) -> bool:
    return normalized in ALLOWED_WITH_ATTRIBUTION


def default_attribution(portal: str, title: str, publisher: str, source_url: str) -> str:
    if portal == "world_bank":
        return (
            f"The World Bank: {title}: {publisher}. "
            f"Source: {source_url}. Licensed under CC BY 4.0."
        )
    if portal == "fred":
        return (
            f"Source: {publisher} via FRED — {title}. "
            f"{source_url}. Citation requested."
        )
    return f"Source: {publisher}. {source_url}"
