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


def plans_for_table(profile: TableProfile) -> list[TestPlan]:
    plans: list[TestPlan] = []
    numeric = profile.numeric
    categorical = profile.categorical
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
