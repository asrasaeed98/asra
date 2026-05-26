"""Human-readable column labels and a lightweight data dictionary."""

from __future__ import annotations

import re

# Known fields from common open-data sources (expand per portal over time).
_COLUMN_DICTIONARY: dict[str, dict[str, str]] = {
    "approvedoutright": {
        "label": "Approved outright amount",
        "description": "Grant funds approved that do not require matching funds from the recipient.",
    },
    "approvedmatching": {
        "label": "Approved matching amount",
        "description": "Grant funds approved that require the recipient to provide matching funds.",
    },
    "awardoutright": {
        "label": "Award outright amount",
        "description": "Outright grant dollars awarded.",
    },
    "awardmatching": {
        "label": "Award matching amount",
        "description": "Matching grant dollars awarded.",
    },
    "originalamount": {
        "label": "Original grant amount",
        "description": "Initial amount of the grant award.",
    },
    "supplementamount": {
        "label": "Supplement amount",
        "description": "Additional funds added to an existing grant.",
    },
    "program": {
        "label": "Program",
        "description": "NEH program area that funded the grant.",
    },
    "division": {
        "label": "Division",
        "description": "NEH division responsible for the grant.",
    },
    "organizationtype": {
        "label": "Organization type",
        "description": "Type of institution that received the grant (e.g. university, museum).",
    },
    "applicanttype": {
        "label": "Applicant type",
        "description": "Category of entity that applied for the grant.",
    },
    "instcountry": {
        "label": "Institution country",
        "description": "Country where the funded institution is located.",
    },
    "yearawarded": {
        "label": "Year awarded",
        "description": "Calendar year the grant was awarded.",
    },
    "value": {
        "label": "Value",
        "description": "Numeric indicator value (common in API/time-series datasets).",
    },
    "country": {
        "label": "Country",
        "description": "Country name or label.",
    },
    "countryiso3code": {
        "label": "Country code",
        "description": "Three-letter ISO country code.",
    },
    "date": {
        "label": "Year",
        "description": "Reference year for the observation.",
    },
    "indicator": {
        "label": "Indicator",
        "description": "Name of the measured indicator.",
    },
}


def _normalize_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def humanize_column(name: str) -> str:
    """Turn ApprovedOutright or approved_outright into 'Approved outright'."""
    if not name:
        return name
    s = str(name).strip()
    if "_" in s:
        return " ".join(part.lower() for part in s.split("_") if part).capitalize()
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", spaced)
    return spaced.strip().capitalize() if spaced.isupper() else spaced.strip()


def column_label(name: str) -> str:
    entry = _COLUMN_DICTIONARY.get(_normalize_key(name))
    if entry:
        return entry["label"]
    return humanize_column(name)


def column_description(name: str) -> str | None:
    entry = _COLUMN_DICTIONARY.get(_normalize_key(name))
    return entry.get("description") if entry else None


def column_entry(name: str) -> dict[str, str | None]:
    return {
        "name": name,
        "label": column_label(name),
        "description": column_description(name),
    }


def glossary_for_columns(names: list[str]) -> list[dict[str, str | None]]:
    seen: set[str] = set()
    out: list[dict[str, str | None]] = []
    for name in names:
        key = _normalize_key(name)
        if key in seen:
            continue
        seen.add(key)
        out.append(column_entry(name))
    return out
