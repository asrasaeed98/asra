"""Plain-language headlines and impact lines for finding cards."""

from __future__ import annotations

from findings_api.analysis.labels import column_label
from findings_api.analysis.types import Finding

# Legacy alias — ML findings are ranked alongside statistical tests when quality gates pass.
EXCLUDE_FROM_RANKING = frozenset()


def _fmt_number(value: float) -> str:
    av = abs(value)
    if av >= 1_000_000:
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    if av >= 1000:
        return f"{value:,.0f}"
    if av >= 1:
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{value:.4g}"


def _maybe_money(label: str, value: float) -> str:
    low = label.lower()
    if any(w in low for w in ("amount", "award", "grant", "dollar", "gdp", "cost", "price")):
        return f"${_fmt_number(value)}"
    return _fmt_number(value)


def headline_for(finding: Finding) -> str:
    cols = finding.columns
    if finding.type == "group_comparison" and len(cols) >= 2:
        return f"{column_label(cols[0])} differs across {column_label(cols[1])}"
    if finding.type == "spearman_correlation" and len(cols) >= 2:
        direction = finding.details.get("direction", "related")
        if direction == "negative":
            return f"{column_label(cols[0])} and {column_label(cols[1])} move in opposite directions"
        return f"{column_label(cols[0])} and {column_label(cols[1])} tend to move together"
    if finding.type == "time_trend" and len(cols) >= 1:
        direction = finding.details.get("direction", "change")
        return f"{column_label(cols[0])} shows an {direction} trend over time"
    if finding.type == "chi_square" and len(cols) >= 2:
        return f"{column_label(cols[0])} and {column_label(cols[1])} appear linked"
    if finding.type == "descriptive":
        return finding.title
    if finding.type in ("kmeans_cluster", "dbscan_cluster"):
        return finding.title
    if finding.type in ("anomaly_top_rows", "lof_anomaly"):
        return finding.title
    if finding.type == "pca_structure":
        return finding.title
    return finding.title.split("(")[0].strip()


def impact_for(finding: Finding) -> str | None:
    if finding.type == "group_comparison" and len(finding.columns) >= 2:
        metric = column_label(finding.columns[0])
        group = column_label(finding.columns[1]).lower()
        means: dict = finding.details.get("group_means") or {}
        top = finding.details.get("highest_group")
        bottom = finding.details.get("lowest_group")
        if top is not None and bottom is not None and means:
            top_v = means.get(top)
            bottom_v = means.get(bottom)
            if top_v is not None and bottom_v is not None:
                return (
                    f"Average {metric.lower()} is highest for {top} "
                    f"({_maybe_money(metric, float(top_v))}) and lowest for {bottom} "
                    f"({_maybe_money(metric, float(bottom_v))}) across {group}s in this sample."
                )
        return f"{metric} is not uniform across {group}s — some groups average noticeably higher or lower."

    if finding.type == "spearman_correlation" and len(finding.columns) >= 2:
        a, b = column_label(finding.columns[0]), column_label(finding.columns[1])
        direction = finding.details.get("direction", "positive")
        if direction == "negative":
            return f"When {a.lower()} goes up, {b.lower()} tends to go down (and vice versa) in this dataset."
        return f"Higher {a.lower()} tends to coincide with higher {b.lower()} in this dataset."

    if finding.type == "time_trend" and finding.columns:
        metric = column_label(finding.columns[0])
        direction = finding.details.get("direction", "upward")
        word = "increased" if direction == "upward" else "decreased"
        return f"{metric} generally {word} over the time period covered by this data."

    if finding.type == "chi_square" and len(finding.columns) >= 2:
        return (
            f"Certain combinations of {column_label(finding.columns[0]).lower()} and "
            f"{column_label(finding.columns[1]).lower()} show up more often than you'd expect by chance."
        )

    if finding.type == "descriptive":
        if finding.details.get("top_values"):
            return "Overview of the most common values in this dataset."
        if finding.details.get("median") is not None:
            return "Typical values and spread for a key numeric column."
        return "Summary of the size and shape of the loaded data."

    if finding.type == "kmeans_cluster":
        return "Rows group into clusters with similar numeric profiles."
    if finding.type == "dbscan_cluster":
        return "Dense regions in numeric space form natural groupings."
    if finding.type in ("anomaly_top_rows", "lof_anomaly"):
        return "A small set of rows looks unlike the rest on numeric fields."
    if finding.type == "pca_structure":
        return "Much of the numeric variation can be summarized by a single combined axis."

    return None


def technical_summary(finding: Finding) -> str:
    """Full stats line for the technical details panel."""
    parts: list[str] = []
    if finding.value is not None:
        parts.append(f"effect = {finding.value}")
    if finding.p_value is not None:
        parts.append(f"p = {finding.p_value}")
    parts.append(f"n = {finding.n}")
    if finding.method:
        parts.append(f"method = {finding.method}")
    return finding.title if not parts else f"{finding.title} ({', '.join(parts)})"


def enrich_finding(finding: Finding) -> Finding:
    finding.details = dict(finding.details or {})
    if "technical_title" not in finding.details:
        finding.details["technical_title"] = finding.title
    finding.details["headline"] = headline_for(finding)
    impact = impact_for(finding)
    if impact:
        finding.details["impact"] = impact
    finding.title = finding.details["headline"]
    return finding


def enrich_findings(findings: list[Finding]) -> list[Finding]:
    return [enrich_finding(f) for f in findings]
