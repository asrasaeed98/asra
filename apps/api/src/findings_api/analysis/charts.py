from __future__ import annotations

import re
from typing import Any

import pandas as pd

from findings_api.analysis.labels import column_label, label_from_details, measure_label
from findings_api.analysis.types import ChartSpec, Finding

_ROW_LIMITS = {
    "spearman_correlation": 1500,
    "group_comparison": 500,
    "time_trend": 2000,
}

_MAX_BAR_CATEGORIES = 10
_MIN_HORIZONTAL_BAR_CATEGORIES = 5

_GEO_CODE_FIELDS = frozenset(
    {
        "countryiso3code",
        "country_code",
        "state_code",
        "state_abbr",
        "stusps",
        "fips",
        "fips_code",
        "geoid",
        "geo_id",
    }
)
_GEO_NAME_FIELDS = frozenset({"country", "country_name", "state", "state_name", "region"})

_VEGA_WIDTH = 420
_VEGA_HEIGHT = 260


def _serialize_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        clean: dict[str, Any] = {}
        for key, value in row.items():
            if pd.isna(value):
                clean[str(key)] = None
            elif isinstance(value, pd.Timestamp):
                clean[str(key)] = value.isoformat()
            elif hasattr(value, "item"):
                clean[str(key)] = value.item()
            else:
                clean[str(key)] = value
        rows.append(clean)
    return rows


def _fetch_rows(conn, sql: str, *, limit: int) -> list[dict[str, Any]]:
    query = sql.strip().rstrip(";")
    if not re.search(r"\blimit\b", query, flags=re.IGNORECASE):
        query = f"{query} LIMIT {limit}"
    try:
        df = conn.execute(query).fetchdf()
    except Exception:
        return []
    return _serialize_rows(df)


def _base_spec(*, mark: str | dict[str, Any], encoding: dict[str, Any]) -> dict[str, Any]:
    mark_obj: str | dict[str, Any] = mark
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": _VEGA_WIDTH,
        "height": _VEGA_HEIGHT,
        "mark": mark_obj,
        "encoding": encoding,
        "config": {
            "axis": {"labelColor": "#78716c", "titleColor": "#44403c"},
            "view": {"stroke": "#e8ddd0"},
        },
    }


def _bar_y_field(values: list[dict[str, Any]], y_field: str, num: str) -> str:
    if values and "mean_value" in values[0]:
        return "mean_value"
    return y_field if y_field in (values[0] if values else {}) else num


def _trim_bar_values(
    values: list[dict[str, Any]],
    grp: str,
    y_field: str,
    *,
    max_categories: int = _MAX_BAR_CATEGORIES,
) -> tuple[list[dict[str, Any]], int, bool]:
    """Keep the top categories by value when there are too many for a readable axis."""
    total = len(values)
    if total <= max_categories:
        return values, total, False

    def sort_key(row: dict[str, Any]) -> float:
        raw = row.get(y_field)
        try:
            return float(raw) if raw is not None else float("-inf")
        except (TypeError, ValueError):
            return float("-inf")

    trimmed = sorted(values, key=sort_key, reverse=True)[:max_categories]
    return trimmed, total, True


def _should_use_horizontal_bar(grp: str, n_categories: int) -> bool:
    low = grp.lower()
    if n_categories >= _MIN_HORIZONTAL_BAR_CATEGORIES:
        return True
    if low in _GEO_CODE_FIELDS | _GEO_NAME_FIELDS:
        return n_categories >= 4
    return False


def _chart_title_with_limit(title: str, *, trimmed: bool, shown: int, total: int) -> str:
    if not trimmed:
        return title
    return f"{title} (top {shown} of {total})"


def _has_geo_name_chart(findings: list[Finding], measure: str) -> bool:
    for other in findings:
        if len(other.columns) != 2:
            continue
        other_measure, other_grp = other.columns
        if other_measure == measure and other_grp.lower() in _GEO_NAME_FIELDS:
            return True
    return False


def _should_skip_geo_code_bar(finding: Finding, findings: list[Finding]) -> bool:
    if finding.type not in ("group_comparison", "descriptive"):
        return False
    if len(finding.columns) != 2:
        return False
    _, grp = finding.columns
    if grp.lower() not in _GEO_CODE_FIELDS:
        return False
    return _has_geo_name_chart(findings, finding.columns[0])


def _build_bar_chart_spec(
    *,
    grp: str,
    y_field: str,
    y_title: str,
    values: list[dict[str, Any]],
    title: str,
    finding_id: str,
    aggregate_mean: bool = False,
) -> ChartSpec:
    trimmed_values, total, was_trimmed = _trim_bar_values(values, grp, y_field)
    horizontal = _should_use_horizontal_bar(grp, len(trimmed_values))
    chart_title = _chart_title_with_limit(
        title, trimmed=was_trimmed, shown=len(trimmed_values), total=total
    )

    if horizontal:
        encoding: dict[str, Any] = {
            "y": {
                "field": grp,
                "type": "nominal",
                "title": column_label(grp),
                "sort": "-x",
            },
            "x": {
                "field": y_field,
                "type": "quantitative",
                "title": y_title,
            },
            "tooltip": [
                {"field": grp, "type": "nominal", "title": column_label(grp)},
                {"field": y_field, "type": "quantitative", "title": y_title},
            ],
        }
        if aggregate_mean:
            encoding["x"]["aggregate"] = "mean"
    else:
        encoding = {
            "x": {
                "field": grp,
                "type": "nominal",
                "title": column_label(grp),
                "sort": "-y",
            },
            "y": {
                "field": y_field,
                "type": "quantitative",
                "title": y_title,
            },
            "tooltip": [
                {"field": grp, "type": "nominal", "title": column_label(grp)},
                {"field": y_field, "type": "quantitative", "title": y_title},
            ],
        }
        if aggregate_mean:
            encoding["y"]["aggregate"] = "mean"

    spec = _base_spec(mark={"type": "bar", "color": "#e879a9"}, encoding=encoding)
    spec["data"] = {"values": trimmed_values}
    return ChartSpec(
        id=f"chart_{finding_id}",
        finding_id=finding_id,
        type="bar",
        title=chart_title,
        spec=spec,
    )


def _chart_for_finding(conn, finding: Finding, *, all_findings: list[Finding]) -> ChartSpec | None:
    if finding.type == "spearman_correlation" and len(finding.columns) == 2:
        x, y = finding.columns
        values = _fetch_rows(conn, finding.sql, limit=_ROW_LIMITS["spearman_correlation"])
        if not values:
            return None
        x_title = label_from_details(finding.details, x)
        y_title = label_from_details(finding.details, y)
        spec = _base_spec(
            mark={"type": "point", "filled": True, "opacity": 0.65, "color": "#e879a9"},
            encoding={
                "x": {"field": x, "type": "quantitative", "title": x_title},
                "y": {"field": y, "type": "quantitative", "title": y_title},
                "tooltip": [
                    {"field": x, "type": "quantitative", "title": x_title},
                    {"field": y, "type": "quantitative", "title": y_title},
                ],
            },
        )
        spec["data"] = {"values": values}
        return ChartSpec(
            id=f"chart_{finding.id}",
            finding_id=finding.id,
            type="scatter",
            title=finding.title,
            spec=spec,
        )

    if finding.type == "group_comparison" and len(finding.columns) == 2:
        if _should_skip_geo_code_bar(finding, all_findings):
            return None
        num, grp = finding.columns
        values = _fetch_rows(conn, finding.sql, limit=_ROW_LIMITS["group_comparison"])
        if not values:
            return None
        y_field = _bar_y_field(values, "mean_value", num)
        dataset_title = str((finding.details or {}).get("dataset_title") or "")
        measure_context = (finding.details or {}).get("measure_context")
        y_title = f"Mean {measure_label(num, dataset_title=dataset_title, measure_context=measure_context)}"
        return _build_bar_chart_spec(
            grp=grp,
            y_field=y_field,
            y_title=y_title,
            values=values,
            title=finding.title,
            finding_id=finding.id,
            aggregate_mean=y_field == num,
        )

    if finding.type == "time_trend" and len(finding.columns) == 2:
        val, time_col = finding.columns
        values = _fetch_rows(conn, finding.sql, limit=_ROW_LIMITS["time_trend"])
        if not values:
            return None
        dataset_title = str((finding.details or {}).get("dataset_title") or "")
        measure_context = (finding.details or {}).get("measure_context")
        y_title = measure_label(val, dataset_title=dataset_title, measure_context=measure_context)
        spec = _base_spec(
            mark={"type": "line", "point": True, "color": "#e879a9"},
            encoding={
                "x": {"field": time_col, "type": "temporal", "title": column_label(time_col)},
                "y": {"field": val, "type": "quantitative", "title": y_title},
                "tooltip": [
                    {"field": time_col, "type": "temporal", "title": column_label(time_col)},
                    {"field": val, "type": "quantitative", "title": y_title},
                ],
            },
        )
        spec["data"] = {"values": values}
        return ChartSpec(
            id=f"chart_{finding.id}",
            finding_id=finding.id,
            type="line",
            title=finding.title,
            spec=spec,
        )

    if finding.type == "descriptive" and len(finding.columns) == 2:
        details = finding.details or {}
        chart_type = details.get("chart_type")
        val, other = finding.columns
        values = _fetch_rows(conn, finding.sql, limit=_ROW_LIMITS["time_trend"])
        if not values:
            return None
        dataset_title = str(details.get("dataset_title") or "")
        measure_context = details.get("measure_context")
        y_title = measure_label(val, dataset_title=dataset_title, measure_context=measure_context)
        if chart_type == "time_trend":
            time_col = other
            spec = _base_spec(
                mark={"type": "line", "point": True, "color": "#e879a9"},
                encoding={
                    "x": {"field": time_col, "type": "temporal", "title": column_label(time_col)},
                    "y": {"field": val, "type": "quantitative", "title": y_title},
                },
            )
            spec["data"] = {"values": values}
            return ChartSpec(
                id=f"chart_{finding.id}",
                finding_id=finding.id,
                type="line",
                title=finding.title,
                spec=spec,
            )
        if chart_type == "group_comparison":
            if _should_skip_geo_code_bar(finding, all_findings):
                return None
            grp = other
            y_field = _bar_y_field(values, "mean_value", val)
            return _build_bar_chart_spec(
                grp=grp,
                y_field=y_field,
                y_title=y_title,
                values=values,
                title=finding.title,
                finding_id=finding.id,
            )

    return None


def charts_for_findings(conn, findings: list[Finding]) -> list[ChartSpec]:
    """Build up to six Vega-Lite charts with embedded data for display findings."""
    charts: list[ChartSpec] = []
    for finding in findings[:6]:
        chart = _chart_for_finding(conn, finding, all_findings=findings)
        if chart is not None:
            charts.append(chart)
    return charts
