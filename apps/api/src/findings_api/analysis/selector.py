from __future__ import annotations

from dataclasses import dataclass

from findings_api.analysis.field_relevance import dedupe_geo_columns
from findings_api.analysis.profile import (
    is_geo_column,
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


def plans_for_table(profile: TableProfile, *, joined: bool = False) -> list[TestPlan]:
    plans: list[TestPlan] = []
    numeric = profile.analysis_numeric
    categorical = dedupe_geo_columns(profile.analysis_categorical)
    datetime_cols = profile.analysis_datetime

    panel = is_panel_table(profile)
    cross_measure = joined and len(numeric) >= 2

    if len(numeric) >= 2:
        plans.append(
            TestPlan(
                kind="correlation",
                table=profile.table,
                resource_id=profile.resource_id,
                title=profile.title,
                columns=numeric[:12],
                extra={"primary": cross_measure} if cross_measure else None,
            )
        )

    group_cats = categorical[:6]
    if cross_measure:
        # Joined multi-measure tables: country-level bars are tautological vs correlation.
        group_cats = [c for c in group_cats if not is_geo_column(c)]

    for cat in group_cats:
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

    if panel and not cross_measure:
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
