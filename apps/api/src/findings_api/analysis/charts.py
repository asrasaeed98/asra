from __future__ import annotations

from findings_api.analysis.types import ChartSpec, Finding


def charts_for_findings(findings: list[Finding]) -> list[ChartSpec]:
    charts: list[ChartSpec] = []
    for finding in findings[:6]:
        if finding.type == "spearman_correlation" and len(finding.columns) == 2:
            x, y = finding.columns
            charts.append(
                ChartSpec(
                    id=f"chart_{finding.id}",
                    finding_id=finding.id,
                    type="scatter",
                    title=finding.title,
                    spec={
                        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                        "mark": {"type": "point", "filled": True, "opacity": 0.7},
                        "encoding": {
                            "x": {"field": x, "type": "quantitative", "title": x},
                            "y": {"field": y, "type": "quantitative", "title": y},
                        },
                        "data": {"name": "points"},
                    },
                )
            )
        elif finding.type == "group_comparison" and len(finding.columns) == 2:
            num, grp = finding.columns
            charts.append(
                ChartSpec(
                    id=f"chart_{finding.id}",
                    finding_id=finding.id,
                    type="bar",
                    title=finding.title,
                    spec={
                        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                        "mark": "bar",
                        "encoding": {
                            "x": {"field": grp, "type": "nominal", "title": grp},
                            "y": {"field": num, "type": "quantitative", "aggregate": "mean", "title": f"Mean {num}"},
                        },
                        "data": {"name": "groups"},
                    },
                )
            )
        elif finding.type == "time_trend" and len(finding.columns) == 2:
            val, time_col = finding.columns
            charts.append(
                ChartSpec(
                    id=f"chart_{finding.id}",
                    finding_id=finding.id,
                    type="line",
                    title=finding.title,
                    spec={
                        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                        "mark": {"type": "line", "point": True},
                        "encoding": {
                            "x": {"field": time_col, "type": "temporal", "title": time_col},
                            "y": {"field": val, "type": "quantitative", "title": val},
                        },
                        "data": {"name": "series"},
                    },
                )
            )
    return charts
