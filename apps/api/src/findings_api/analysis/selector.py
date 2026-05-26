from __future__ import annotations

from dataclasses import dataclass

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
            plans.append(
                TestPlan(
                    kind="trend",
                    table=profile.table,
                    resource_id=profile.resource_id,
                    title=profile.title,
                    columns=[num, dt],
                )
            )

    return plans[:24]
