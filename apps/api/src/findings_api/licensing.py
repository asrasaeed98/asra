"""License normalization for catalog ingest gate."""

ALLOWED = frozenset({"CC0", "US_PD", "US_GOV_WORK", "PDDL"})

_RAW_TO_NORMALIZED: dict[str, str] = {
    "cc0": "CC0",
    "cc0-1.0": "CC0",
    "cc-zero": "CC0",
    "us-pd": "US_PD",
    "us-public-domain": "US_PD",
}


def normalize_license(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    key = str(raw).strip().lower()
    if key in _RAW_TO_NORMALIZED:
        return _RAW_TO_NORMALIZED[key]
    if "creative commons zero" in key or key == "cc0":
        return "CC0"
    if "public domain" in key or "government work" in key:
        return "US_GOV_WORK"
    return None


def is_allowed(normalized: str | None) -> bool:
    return normalized in ALLOWED
