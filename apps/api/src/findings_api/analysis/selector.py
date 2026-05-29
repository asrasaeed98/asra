from __future__ import annotations

from dataclasses import dataclass

from findings_api.analysis.profile import (
    is_panel_table,
    preferred_geo_column,
    preferred_measure_column,
)
from findings_api.analysis.types import TableProfile


@dataclass
class TestPlan:
    kind: str
    table: str
    resource_id: str
    title: str
    columns: list[str]
    extra: dict | None = None


# Ordered by preference: when several columns in a group are present, keep only
# the first (the human-readable name) and drop redundant code/ISO variants so we
# don't emit duplicate findings like "differs across Country" and
# "differs across Country code".
_GEO_PREFERENCE_GROUPS: list[list[str]] = [
    ["country", "country_name", "countryiso3code", "country_code", "countrycode", "iso3", "iso"],
    ["state", "state_name", "state_code", "state_abbr", "stusps"],
    ["fips", "fips_code", "county_fips"],
    ["geo_id", "geoid"],
]


def _dedupe_geo_columns(categorical: list[str]) -> list[str]:
    """Drop redundant geo code columns when a preferred name column is present."""

    def norm(name: str) -> str:
        return name.lower().replace(" ", "").replace("_", "")

    drop: set[str] = set()
    for group in _GEO_PREFERENCE_GROUPS:
        group_norm = [norm(g) for g in group]
        present = [c for c in categorical if norm(c) in group_norm]
        if len(present) <= 1:
            continue
        ranked = sorted(present, key=lambda c: group_norm.index(norm(c)))
        drop.update(ranked[1:])
    return [c for c in categorical if c not in drop]


def plans_for_table(profile: TableProfile) -> list[TestPlan]:
    plans: list[TestPlan] = []
    numeric = profile.numeric
    categorical = _dedupe_geo_columns(profile.categorical)
    datetime_cols = profile.datetime

    panel = is_panel_table(profile)

    if len(numeric) >= 2:
        plans.append(
            TestPlan(
                kind="correlation",
                table=profile.table,
                resource_id=profile.resource_id,
                title=profile.title,
                columns=numeric[:12],
            )
        )

    for cat in categorical[:6]:
        for num in numeric[:8]:
            plans.append(
                TestPlan(
                    kind="group_comparison",
                    table=profile.table,
                    resource_id=profile.resource_id,
                    title=profile.title,
                    columns=[num, cat],
                )
            )

    if len(categorical) >= 2:
        plans.append(
            TestPlan(
                kind="chi_square",
                table=profile.table,
                resource_id=profile.resource_id,
                title=profile.title,
                columns=categorical[:2],
            )
        )

    for dt in datetime_cols[:2]:
        for num in numeric[:4]:
            if panel:
                plans.append(
                    TestPlan(
                        kind="trend",
                        table=profile.table,
                        resource_id=profile.resource_id,
                        title=profile.title,
                        columns=[num, dt],
                        extra={"aggregate_by_time": True, "tier": "derived"},
                    )
                )
            else:
                plans.append(
                    TestPlan(
                        kind="trend",
                        table=profile.table,
                        resource_id=profile.resource_id,
                        title=profile.title,
                        columns=[num, dt],
                        extra={"tier": "primary"},
                    )
                )

    if panel:
        measure = preferred_measure_column(profile)
        geo = preferred_geo_column(profile)
        if measure and geo:
            pair = [measure, geo]
            if not any(p.kind == "group_comparison" and p.columns == pair for p in plans):
                plans.insert(
                    0,
                    TestPlan(
                        kind="group_comparison",
                        table=profile.table,
                        resource_id=profile.resource_id,
                        title=profile.title,
                        columns=pair,
                    ),
                )

    return plans[:24]
