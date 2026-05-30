"""Plain-language summary of statistical tests and ML models attempted in a run."""

from __future__ import annotations

from findings_api.analysis.profile import TableProfile
from findings_api.analysis.selector import plans_for_table

_PLAN_LABELS = {
    "correlation": "Spearman correlation",
    "group_comparison": "Group comparison",
    "chi_square": "Chi-square test",
    "trend": "Time trend",
}

_DERIVED_TREND_LABEL = "Year/time averages"

_ML_LABELS = [
    "K-means clustering",
    "DBSCAN clustering",
    "PCA structure",
    "Anomaly detection",
    "Local outlier detection",
]


def summarize_methods_run(
    profiles: list[TableProfile],
    *,
    ml_enabled: bool,
    joined_ok: bool,
) -> list[str]:
    """Unique human-readable methods planned for this session (in run order)."""
    labels: list[str] = []
    seen: set[str] = set()
    has_derived_trend = False

    for profile in profiles:
        table_joined = joined_ok and profile.table == "analysis_joined"
        for plan in plans_for_table(profile, joined=table_joined):
            if (plan.extra or {}).get("tier") == "derived":
                if plan.kind == "trend":
                    has_derived_trend = True
                continue
            label = _PLAN_LABELS.get(plan.kind)
            if label and label not in seen:
                seen.add(label)
                labels.append(label)

    if has_derived_trend and _DERIVED_TREND_LABEL not in seen:
        labels.append(_DERIVED_TREND_LABEL)

    if ml_enabled:
        for label in _ML_LABELS:
            if label not in seen:
                seen.add(label)
                labels.append(label)

    return labels
