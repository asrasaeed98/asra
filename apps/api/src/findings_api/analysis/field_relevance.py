"""Evaluate dataset columns for analytical relevance before analysis.

Classifies fields, ranks them for tests and summaries, and recommends derived
dimensions (borough, neighborhood, month/year) — especially for NYC Open Data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from findings_api.analysis.types import ColumnProfile, TableProfile

ANALYTICAL_CATEGORIES = (
    "core_analytical",
    "geographic",
    "temporal",
    "numeric_measure",
    "administrative_identifier",
    "metadata",
    "unknown",
)

# Human-readable NYC geographic dimensions (preferred over coordinates).
_NYC_GEO_PREFERRED = frozenset({
    "borough",
    "boro",
    "boro_nm",
    "borough_name",
    "boroughcode",
    "neighborhood",
    "neighbourhood",
    "nta",
    "nta_name",
    "nta2020",
    "nta2020_name",
    "zip",
    "zipcode",
    "zip_code",
    "postcode",
    "incident_zip",
    "community_board",
    "communityboard",
    "community_district",
    "communitydistrict",
    "commntyd",
    "cd",
    "council_district",
    "police_precinct",
    "precinct",
    "precinct_num",
    "station",
    "park_borough",
    "school_district",
    "census_tract",
    "census_block",
    "address",
    "street_name",
    "cross_street",
    "intersection",
    "city",
})

# Coordinate / geometry fields to deprioritize when human-readable geo exists.
_COORD_NAMES = frozenset({
    "latitude",
    "longitude",
    "lat",
    "lon",
    "lng",
    "lat_lon",
    "latlong",
    "geolocation",
    "the_geom",
    "geom",
    "point",
    "x_coord",
    "y_coord",
    "xcoordinate",
    "ycoordinate",
})

# Socrata system / computed columns.
_METADATA_NAMES = frozenset({
    ":id",
    ":created_at",
    ":updated_at",
    ":version",
    ":@computed_region",
    ":@geocoded_column",
    "geocoded_column",
    "objectid",
    "globalid",
    "shape_area",
    "shape_length",
    "shape_leng",
    "url",
    "uri",
    "link",
    "source",
    "data_as_of",
    "last_updated",
})

# Row keys, case numbers, and other administrative identifiers.
_ADMIN_SUFFIXES = ("_id", "_key", "_num", "_number", "_no", "_code")
_ADMIN_NAMES = frozenset({
    "id",
    "unique_key",
    "uniquekey",
    "record_id",
    "recordid",
    "incident_number",
    "complaint_number",
    "cmplnt_num",
    "ticket_number",
    "violation_id",
    "job_number",
    "permit_id",
    "license_number",
    "bin",
    "bbl",
    "block",
    "lot",
    "house_number",
    "housenumber",
})

# Outcome / category columns that drive business insight.
_CORE_HINTS = (
    "desc",
    "description",
    "type",
    "category",
    "class",
    "status",
    "offense",
    "ofns",
    "violation",
    "reason",
    "resolution",
    "agency",
    "program",
    "grade",
    "result",
    "outcome",
    "law_cat",
    "pd_desc",
    "descriptor",
    "complaint",
    "charge",
    "crime",
    "inspection",
    "action",
    "method",
    "mode",
    "severity",
    "level",
    "rank",
    "rating",
    "score",
    "flag",
    "indicator",
    "sector",
    "industry",
    "occupation",
    "race",
    "ethnicity",
    "gender",
    "sex",
    "age_group",
    "borough_response",
)

_TIME_NAMES = frozenset({
    "date",
    "datetime",
    "timestamp",
    "time",
    "year",
    "yr",
    "month",
    "day",
    "week",
    "quarter",
    "fiscal_year",
    "calendar_year",
    "obs_date",
    "time_period",
    "period",
    "created",
    "updated",
    "closed",
    "opened",
    "occurred",
    "incident",
    "reported",
    "approved",
    "issued",
    "filed",
    "start",
    "end",
    "from",
    "to",
})

_MEASURE_HINTS = (
    "count",
    "total",
    "sum",
    "amount",
    "amt",
    "value",
    "val",
    "rate",
    "ratio",
    "percent",
    "pct",
    "avg",
    "average",
    "mean",
    "median",
    "min",
    "max",
    "volume",
    "weight",
    "distance",
    "duration",
    "hours",
    "days",
    "cost",
    "price",
    "fee",
    "fine",
    "penalty",
    "score",
    "index",
    "population",
    "size",
    "area_sqft",
    "units",
    "beds",
    "rooms",
)

# Geo preference groups — keep first match, drop redundant variants.
GEO_PREFERENCE_GROUPS: list[list[str]] = [
    ["boro_nm", "borough", "borough_name", "boro", "boroughcode"],
    ["neighborhood", "nta_name", "nta2020_name", "nta", "nta2020", "neighbourhood"],
    ["zipcode", "zip_code", "zip", "incident_zip", "postcode"],
    ["community_district", "communitydistrict", "commntyd", "cd", "community_board", "communityboard"],
    ["police_precinct", "precinct", "precinct_num"],
    ["country", "country_name", "countryiso3code", "country_code", "countrycode", "iso3", "iso"],
    ["state", "state_name", "state_code", "state_abbr", "stusps"],
    ["fips", "fips_code", "county_fips"],
    ["geo_id", "geoid"],
]


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _name_tokens(name: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", name.lower()) if t}


def _is_preferred_geo_name(name: str) -> bool:
    norm = _norm(name)
    tokens = _name_tokens(name)
    for pref in _NYC_GEO_PREFERRED:
        pn = _norm(pref)
        if norm == pn or pn in norm or norm in pn:
            return True
        if pref in tokens:
            return True
    return False


def _matches_hint(name: str, hints: tuple[str, ...]) -> bool:
    norm = _norm(name)
    tokens = _name_tokens(name)
    for hint in hints:
        h = _norm(hint)
        if h in norm or h in tokens:
            return True
    return False


def _is_admin_identifier(name: str) -> bool:
    norm = _norm(name)
    if norm in _ADMIN_NAMES:
        return True
    low = name.lower()
    if low.endswith(_ADMIN_SUFFIXES) and norm not in _NYC_GEO_PREFERRED:
        return True
    if norm.endswith("id") and len(norm) <= 12 and norm not in _NYC_GEO_PREFERRED:
        return True
    return False


def _is_coordinate_field(name: str) -> bool:
    norm = _norm(name)
    if norm in _COORD_NAMES:
        return True
    tokens = _name_tokens(name)
    if tokens & {"latitude", "longitude", "lat", "lon", "lng"}:
        return True
    if norm.startswith("computedregion") or norm.startswith("geocoded"):
        return True
    return False


def classify_field(
    name: str,
    *,
    kind: str | None = None,
    nunique: int | None = None,
) -> str:
    """Classify a column into an analytical category."""
    norm = _norm(name)
    low = name.lower()

    if low.startswith(":") or norm in _METADATA_NAMES or _is_coordinate_field(name):
        if _is_coordinate_field(name) and norm in _NYC_GEO_PREFERRED:
            return "geographic"
        if _is_coordinate_field(name):
            return "metadata"
        return "metadata"

    if _is_admin_identifier(name):
        return "administrative_identifier"

    if _is_preferred_geo_name(name) or _matches_hint(name, ("borough", "boro", "neighborhood", "precinct", "zip")):
        return "geographic"

    if kind == "datetime" or norm in _TIME_NAMES or _matches_hint(name, tuple(_TIME_NAMES)):
        return "temporal"

    if kind == "numeric":
        if _matches_hint(name, _MEASURE_HINTS):
            return "numeric_measure"
        if _is_coordinate_field(name):
            return "metadata"
        if nunique is not None and nunique <= 1:
            return "metadata"
        return "numeric_measure"

    if kind == "categorical":
        if _matches_hint(name, _CORE_HINTS):
            return "core_analytical"
        if nunique is not None and nunique > 300:
            return "metadata"
        return "core_analytical"

    if _matches_hint(name, _CORE_HINTS):
        return "core_analytical"

    return "unknown"


def _category_score(
    category: str,
    *,
    kind: str,
    has_preferred_geo: bool,
    is_coordinate: bool,
) -> int:
    base = {
        "core_analytical": 88,
        "geographic": 92,
        "temporal": 80,
        "numeric_measure": 75,
        "unknown": 40,
        "administrative_identifier": 15,
        "metadata": 5,
    }.get(category, 30)

    if category == "geographic" and has_preferred_geo and is_coordinate:
        return 5
    if is_coordinate and has_preferred_geo:
        return 5
    if category == "numeric_measure" and kind == "numeric":
        base += 5
    if category == "geographic" and kind == "categorical":
        base += 5
    if category == "core_analytical" and kind == "categorical":
        base += 3
    return base


def _field_reason(name: str, category: str, *, kind: str, has_preferred_geo: bool) -> str:
    if category == "geographic":
        return "Human-readable location for comparing patterns across NYC areas."
    if category == "core_analytical":
        return "Describes what happened — useful for category breakdowns and comparisons."
    if category == "temporal":
        return "Time dimension for trends, seasonality, and before/after comparisons."
    if category == "numeric_measure":
        return "Quantitative outcome or count suitable for distributions and correlations."
    if category == "administrative_identifier":
        return "Record key or case number — useful for lookup, not aggregate analysis."
    if category == "metadata" and _is_coordinate_field(name):
        if has_preferred_geo:
            return "Raw coordinates — excluded because borough/neighborhood columns are available."
        return "Raw coordinates — prefer borough or neighborhood for readable geographic analysis."
    if category == "metadata":
        return "System or technical field with limited analytical value."
    if category == "unknown":
        return "Unclassified — included only when higher-priority fields are scarce."
    return "Included for analysis."


@dataclass
class FieldAssessment:
    name: str
    category: str
    score: int
    kind: str
    reason: str
    include_in_analysis: bool


@dataclass
class DerivedDimension:
    dimension: str
    source_columns: list[str]
    reason: str


@dataclass
class FieldRelevanceReport:
    ranked_fields: list[FieldAssessment] = field(default_factory=list)
    excluded_fields: list[FieldAssessment] = field(default_factory=list)
    derived_dimensions: list[DerivedDimension] = field(default_factory=list)
    analysis_columns: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ranked_fields": [
                {
                    "name": f.name,
                    "category": f.category,
                    "score": f.score,
                    "kind": f.kind,
                    "reason": f.reason,
                }
                for f in self.ranked_fields
            ],
            "excluded_fields": [
                {
                    "name": f.name,
                    "category": f.category,
                    "reason": f.reason,
                }
                for f in self.excluded_fields
            ],
            "derived_dimensions": [
                {
                    "dimension": d.dimension,
                    "source_columns": d.source_columns,
                    "reason": d.reason,
                }
                for d in self.derived_dimensions
            ],
            "analysis_columns": self.analysis_columns,
        }


def _has_preferred_geo(columns: list[ColumnProfile]) -> bool:
    for col in columns:
        if _is_preferred_geo_name(col.name):
            return True
        if classify_field(col.name, kind=col.kind) == "geographic" and not _is_coordinate_field(col.name):
            return True
    return False


def _recommend_derived(
    columns: list[ColumnProfile],
    *,
    has_preferred_geo: bool,
) -> list[DerivedDimension]:
    derived: list[DerivedDimension] = []
    names = {c.name for c in columns}
    norms = {_norm(c.name): c.name for c in columns}

    coord_cols = [c.name for c in columns if _is_coordinate_field(c.name)]
    if coord_cols and not has_preferred_geo:
        derived.append(
            DerivedDimension(
                dimension="borough",
                source_columns=coord_cols,
                reason="Only latitude/longitude found — map coordinates to borough before geographic analysis.",
            )
        )
        derived.append(
            DerivedDimension(
                dimension="neighborhood",
                source_columns=coord_cols,
                reason="Neighborhood (NTA) adds finer geographic context than raw coordinates.",
            )
        )

    for col in columns:
        if col.kind != "datetime":
            continue
        low = col.name.lower()
        derived.append(
            DerivedDimension(
                dimension="year",
                source_columns=[col.name],
                reason=f"Extract year from {col.name} for long-term trend comparisons.",
            )
        )
        if "month" not in low and "year" not in low:
            derived.append(
                DerivedDimension(
                    dimension="month",
                    source_columns=[col.name],
                    reason=f"Extract month from {col.name} for seasonality and monthly patterns.",
                )
            )

    if norms.get("communitydistrict") or norms.get("commntyd") or norms.get("cd"):
        src = norms.get("communitydistrict") or norms.get("commntyd") or norms.get("cd")
        if src and "borough" not in norms:
            derived.append(
                DerivedDimension(
                    dimension="borough",
                    source_columns=[src],
                    reason="Community district can be rolled up to borough for higher-level comparisons.",
                )
            )

    if norms.get("precinct") and "borough" not in norms:
        derived.append(
            DerivedDimension(
                dimension="borough",
                source_columns=[norms["precinct"]],
                reason="Police precinct maps to borough — useful when borough column is missing.",
            )
        )

    # Deduplicate by dimension name (keep first).
    seen: set[str] = set()
    unique: list[DerivedDimension] = []
    for item in derived:
        if item.dimension in seen:
            continue
        seen.add(item.dimension)
        unique.append(item)
    return unique


def evaluate_fields(
    columns: list[ColumnProfile],
    *,
    portal: str | None = None,
) -> FieldRelevanceReport:
    """Evaluate all columns and return ranked / excluded lists for analysis."""
    has_geo = _has_preferred_geo(columns)
    assessments: list[FieldAssessment] = []

    for col in columns:
        if col.kind == "other":
            assessments.append(
                FieldAssessment(
                    name=col.name,
                    category="metadata",
                    score=0,
                    kind=col.kind,
                    reason="High cardinality or unsupported type — skipped for statistical tests.",
                    include_in_analysis=False,
                )
            )
            continue

        category = classify_field(col.name, kind=col.kind, nunique=col.nunique)
        is_coord = _is_coordinate_field(col.name)
        score = _category_score(
            category,
            kind=col.kind,
            has_preferred_geo=has_geo,
            is_coordinate=is_coord,
        )

        include = score >= 40 and category not in ("metadata", "administrative_identifier")
        if is_coord and has_geo:
            include = False
            category = "metadata"

        # NYC portal: be stricter about admin IDs unless few analytical columns exist.
        if portal == "nyc_open_data" and category == "administrative_identifier":
            include = False

        reason = _field_reason(col.name, category, kind=col.kind, has_preferred_geo=has_geo)
        assessments.append(
            FieldAssessment(
                name=col.name,
                category=category,
                score=score,
                kind=col.kind,
                reason=reason,
                include_in_analysis=include,
            )
        )

    # If we'd exclude everything, relax slightly for unknown/numeric.
    if not any(a.include_in_analysis for a in assessments):
        for a in assessments:
            if a.kind in ("numeric", "categorical", "datetime") and a.category not in ("metadata",):
                a.include_in_analysis = True
                a.score = max(a.score, 50)

    ranked = sorted(
        [a for a in assessments if a.include_in_analysis],
        key=lambda a: (-a.score, a.name),
    )
    excluded = [a for a in assessments if not a.include_in_analysis]

    analysis_columns: dict[str, list[str]] = {
        "numeric": [a.name for a in ranked if a.kind == "numeric"],
        "categorical": [a.name for a in ranked if a.kind == "categorical"],
        "datetime": [a.name for a in ranked if a.kind == "datetime"],
    }

    return FieldRelevanceReport(
        ranked_fields=ranked,
        excluded_fields=excluded,
        derived_dimensions=_recommend_derived(columns, has_preferred_geo=has_geo),
        analysis_columns=analysis_columns,
    )


def evaluate_profile(profile: TableProfile, *, portal: str | None = None) -> FieldRelevanceReport:
    return evaluate_fields(profile.columns, portal=portal)


def _geo_group_key(name: str, group: list[str]) -> int | None:
    norm = _norm(name)
    tokens = _name_tokens(name)
    for idx, candidate in enumerate(group):
        cn = _norm(candidate)
        if norm == cn or cn in norm or norm in cn:
            return idx
        if candidate in tokens:
            return idx
    return None


def dedupe_geo_columns(categorical: list[str]) -> list[str]:
    """Drop redundant geo code columns when a preferred name column is present."""
    drop: set[str] = set()
    for group in GEO_PREFERENCE_GROUPS:
        present: list[tuple[int, str]] = []
        for col in categorical:
            key = _geo_group_key(col, group)
            if key is not None:
                present.append((key, col))
        if len(present) <= 1:
            continue
        present.sort(key=lambda item: item[0])
        drop.update(col for _, col in present[1:])
    return [c for c in categorical if c not in drop]
