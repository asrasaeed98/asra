"""Harmonized cross-dataset correlation for paired public-data indicators."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import pandas as pd
from scipy import stats

from findings_api.analysis.measure_semantics import MEASURE_COLUMN_NAMES, measure_slug, resolve_measure_label
from findings_api.analysis.profile import read_table_frame, sql_ident
from findings_api.analysis.tests.correlation import _MAX_P, _MIN_R, _score
from findings_api.analysis.types import Finding

logger = logging.getLogger(__name__)

MIN_PAIRS = 8
MIN_ENTITIES = 5
MERGED_TABLE = "cross_measure_merged"

_ENTITY_ISO_COLUMNS = (
    "countryiso3code",
    "country_code",
    "countrycode",
    "iso3",
    "iso",
    "iso_code",
)
_ENTITY_NAME_COLUMNS = ("country", "country_name", "nation", "state", "state_name", "region")
_TIME_COLUMNS = ("date", "year", "yr", "fiscal_year", "calendar_year", "obs_date", "time_period", "period")

# World Bank / international aggregate rows that are not comparable countries.
_AGGREGATE_SUBSTRINGS = (
    "ibrd only",
    "ida & ibrd",
    "ida only",
    "ida total",
    "least developed countries",
    "low income",
    "middle income",
    "high income",
    "income group",
    "small states",
    "post-demographic dividend",
    "pre-demographic dividend",
    "early-demographic dividend",
    "late-demographic dividend",
    "fragile",
    "euro area",
    "european union",
    "world",
    "north america",
    "latin america",
    "sub-saharan africa",
    "east asia",
    "south asia",
    "middle east",
    "europe & central asia",
    "aggregates",
    "other small states",
    "small island",
)

_ISO3_RE = re.compile(r"^[A-Z]{3}$")


@dataclass
class PanelSpec:
    table: str
    resource_id: str
    title: str
    entity_col: str
    time_col: str
    measure_col: str
    measure_label: str
    entity_kind: str  # iso3 | name


@dataclass
class CrossMeasureResult:
    findings: list[Finding] = field(default_factory=list)
    report: dict = field(default_factory=dict)
    paired_ok: bool = False


def _pick_column(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    lower = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    return None


def _pick_measure_column(columns: list[str]) -> str | None:
    lower = {c.lower(): c for c in columns}
    for cand in MEASURE_COLUMN_NAMES:
        if cand in lower:
            return lower[cand]
    skip = frozenset(
        _ENTITY_ISO_COLUMNS
        + _ENTITY_NAME_COLUMNS
        + _TIME_COLUMNS
        + ("indicator", "indicator_id", "series_id", "series")
    )
    for col in columns:
        low = col.lower()
        if low in skip or low.endswith("_id") or low.startswith("indicator"):
            continue
        return col
    return None


def _is_aggregate_entity(value: object) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return True
    text = str(value).strip()
    if not text:
        return True
    if _ISO3_RE.match(text.upper()) and text.upper() == text and len(text) == 3:
        return False
    low = text.lower()
    return any(token in low for token in _AGGREGATE_SUBSTRINGS)


def _normalize_entity(value: object, *, kind: str) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    if kind == "iso3":
        token = text.upper()
        if _ISO3_RE.match(token):
            return token
        return None
    if _is_aggregate_entity(text):
        return None
    return text.casefold()


def _year_from_value(value: object) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return int(value.year)
    if hasattr(value, "year") and not isinstance(value, str):
        try:
            return int(value.year)
        except (TypeError, ValueError):
            pass
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{4}", text):
        return int(text)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return int(text[:4])
    parsed = pd.to_datetime(text, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return int(parsed.year)


def _detect_panel(conn, table: str, resource_id: str, title: str) -> PanelSpec | None:
    df = read_table_frame(conn, table)
    if df.empty:
        return None
    columns = [str(c) for c in df.columns]
    measure_col = _pick_measure_column(columns)
    if not measure_col:
        return None
    time_col = _pick_column(columns, _TIME_COLUMNS)
    if not time_col:
        return None

    iso_col = _pick_column(columns, _ENTITY_ISO_COLUMNS)
    if iso_col:
        entity_col = iso_col
        entity_kind = "iso3"
    else:
        name_col = _pick_column(columns, _ENTITY_NAME_COLUMNS)
        if not name_col:
            return None
        entity_col = name_col
        entity_kind = "name"

    ctx = resolve_measure_label(conn, table, measure_col, catalog_title=title, use_ai=False)
    measure_label = str(ctx.get("label") or title or measure_col)

    return PanelSpec(
        table=table,
        resource_id=resource_id,
        title=title,
        entity_col=entity_col,
        time_col=time_col,
        measure_col=measure_col,
        measure_label=measure_label,
        entity_kind=entity_kind,
    )


def _harmonized_frame(conn, panel: PanelSpec) -> pd.DataFrame:
    df = read_table_frame(conn, panel.table)
    rows: list[dict[str, object]] = []
    for _, row in df.iterrows():
        entity = _normalize_entity(row.get(panel.entity_col), kind=panel.entity_kind)
        year = _year_from_value(row.get(panel.time_col))
        value = pd.to_numeric(row.get(panel.measure_col), errors="coerce")
        if entity is None or year is None or pd.isna(value):
            continue
        rows.append({"entity_id": entity, "year": year, "value": float(value)})
    if not rows:
        return pd.DataFrame(columns=["entity_id", "year", "value"])
    out = pd.DataFrame(rows)
    out = out.groupby(["entity_id", "year"], as_index=False)["value"].mean()
    return out


def _write_merged_table(conn, merged: pd.DataFrame, col_a: str, col_b: str) -> None:
    payload = merged.rename(columns={"value_a": col_a, "value_b": col_b})
    conn.register("_cross_measure_df", payload)
    conn.execute(f"CREATE OR REPLACE TABLE {MERGED_TABLE} AS SELECT * FROM _cross_measure_df")


def _coverage_note(
    *,
    strategy: str,
    n_pairs: int,
    n_entities: int,
    year_min: int | None,
    year_max: int | None,
    label_a: str,
    label_b: str,
) -> str:
    span = ""
    if year_min is not None and year_max is not None:
        span = f", {year_min}–{year_max}"
    return (
        f"Cross-measure correlation on {n_pairs:,} matched country-years across "
        f"{n_entities:,} entities{span} ({strategy.replace('_', ' ')})."
    )


def _make_finding(
    *,
    idx: int,
    col_a: str,
    col_b: str,
    label_a: str,
    label_b: str,
    r: float,
    p: float,
    n: int,
    resource_id: str,
    view: str,
    strategy: str,
    primary: bool,
    coverage: dict,
    sql: str,
    extra_caveat: str = "",
) -> Finding:
    direction = "negative" if r < 0 else "positive"
    caveat = "correlation is not causation"
    if extra_caveat:
        caveat = f"{extra_caveat}; {caveat}"
    return Finding(
        id=f"f_{idx}",
        type="spearman_correlation",
        title=(
            f"{label_a} and {label_b} "
            f"{'move in opposite directions' if r < 0 else 'tend to move together'}"
        ),
        columns=[col_a, col_b],
        value=round(float(r), 4),
        p_value=round(float(p), 6),
        n=n,
        method="spearman",
        caveat=caveat,
        sql=sql,
        datasets=[resource_id],
        score=_score(float(r), float(p)) * (1.35 if primary else 1.0),
        details={
            "dataset_title": f"{label_a} + {label_b}",
            "direction": direction,
            "column_labels": {col_a: label_a, col_b: label_b},
            "cross_measure": True,
            "correlation_view": view,
            "join_strategy": strategy,
            "coverage": coverage,
            "primary": primary,
            "badge": "Cross-dataset relationship" if primary else None,
        },
    )


def _try_correlation(
    frame: pd.DataFrame,
    col_a: str,
    col_b: str,
    *,
    min_pairs: int = MIN_PAIRS,
) -> tuple[float, float, int] | None:
    pair = frame[[col_a, col_b]].dropna()
    if len(pair) < min_pairs:
        return None
    if pair[col_a].nunique() < 2 or pair[col_b].nunique() < 2:
        return None
    r, p = stats.spearmanr(pair[col_a], pair[col_b])
    if pd.isna(r) or pd.isna(p):
        return None
    if abs(float(r)) < _MIN_R or float(p) >= _MAX_P:
        return None
    return float(r), float(p), len(pair)


def _merge_panels(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    merged = left.merge(right, on=["entity_id", "year"], how="inner", suffixes=("_a", "_b"))
    return merged.dropna(subset=["value_a", "value_b"])


def _strategies(left: PanelSpec, right: PanelSpec) -> list[tuple[str, PanelSpec, PanelSpec]]:
    ordered: list[tuple[str, PanelSpec, PanelSpec]] = []
    if left.entity_kind == "iso3" and right.entity_kind == "iso3":
        ordered.append(("iso3_year", left, right))
    if left.entity_kind == "name" and right.entity_kind == "name":
        ordered.append(("country_year", left, right))
    # Fallback: harmonize via available entity columns even if kinds differ.
    if ("iso3_year", left, right) not in ordered and ("country_year", left, right) not in ordered:
        ordered.append(("entity_year", left, right))
    return ordered


def run_cross_measure_analysis(
    conn,
    left_table: str,
    right_table: str,
    *,
    left_resource_id: str,
    right_resource_id: str,
    left_title: str,
    right_title: str,
    finding_offset: int = 0,
) -> CrossMeasureResult:
    """Build harmonized overlap and run pooled / latest-year / country-mean correlations."""
    result = CrossMeasureResult()
    left_panel = _detect_panel(conn, left_table, left_resource_id, left_title)
    right_panel = _detect_panel(conn, right_table, right_resource_id, right_title)
    if not left_panel or not right_panel:
        result.report = {
            "success": False,
            "reason": "Could not detect entity, time, and measure columns in both datasets.",
        }
        return result

    combined_rid = f"{left_resource_id}+{right_resource_id}"
    used_slugs: set[str] = set()
    col_a = measure_slug(left_panel.measure_label, fallback="measure_a", used=used_slugs)
    col_b = measure_slug(right_panel.measure_label, fallback="measure_b", used=used_slugs)
    label_a = left_panel.measure_label
    label_b = right_panel.measure_label

    best: Finding | None = None
    all_findings: list[Finding] = []
    idx = finding_offset
    chosen_report: dict | None = None

    for strategy, lp, rp in _strategies(left_panel, right_panel):
        left_df = _harmonized_frame(conn, lp)
        right_df = _harmonized_frame(conn, rp)
        merged = _merge_panels(left_df, right_df)
        if merged.empty:
            continue

        n_entities = int(merged["entity_id"].nunique())
        year_min = int(merged["year"].min())
        year_max = int(merged["year"].max())
        coverage = {
            "strategy": strategy,
            "matched_pairs": int(len(merged)),
            "entities": n_entities,
            "year_start": year_min,
            "year_end": year_max,
            "measure_a": label_a,
            "measure_b": label_b,
        }

        if len(merged) < MIN_PAIRS:
            chosen_report = {
                "success": False,
                "reason": f"Only {len(merged)} overlapping country-years where both indicators have values (need {MIN_PAIRS}).",
                **coverage,
            }
            continue

        _write_merged_table(conn, merged, col_a, col_b)
        base_sql = (
            f"SELECT {sql_ident(col_a)}, {sql_ident(col_b)} FROM {MERGED_TABLE} "
            f"WHERE {sql_ident(col_a)} IS NOT NULL AND {sql_ident(col_b)} IS NOT NULL"
        )

        # 1) Pooled country-year overlap (primary)
        pooled = _try_correlation(
            merged.rename(columns={"value_a": col_a, "value_b": col_b}),
            col_a,
            col_b,
        )
        if pooled:
            r, p, n = pooled
            idx += 1
            finding = _make_finding(
                idx=idx,
                col_a=col_a,
                col_b=col_b,
                label_a=label_a,
                label_b=label_b,
                r=r,
                p=p,
                n=n,
                resource_id=combined_rid,
                view="panel_pooled",
                strategy=strategy,
                primary=True,
                coverage=coverage,
                sql=base_sql,
            )
            all_findings.append(finding)
            best = finding

        # 2) Latest common year cross-section
        latest_year = int(merged["year"].max())
        latest = merged[merged["year"] == latest_year].rename(columns={"value_a": col_a, "value_b": col_b})
        latest_stats = _try_correlation(latest, col_a, col_b, min_pairs=min(MIN_PAIRS, MIN_ENTITIES))
        if latest_stats:
            r, p, n = latest_stats
            idx += 1
            all_findings.append(
                _make_finding(
                    idx=idx,
                    col_a=col_a,
                    col_b=col_b,
                    label_a=label_a,
                    label_b=label_b,
                    r=r,
                    p=p,
                    n=n,
                    resource_id=combined_rid,
                    view="cross_section_latest",
                    strategy=strategy,
                    primary=False,
                    coverage={**coverage, "latest_year": latest_year},
                    sql=f"{base_sql} AND year = {latest_year}",
                    extra_caveat=f"Based on {latest_year} only ({n} entities)",
                )
            )

        # 3) Country means
        means = (
            merged.groupby("entity_id", as_index=False)[["value_a", "value_b"]]
            .mean()
            .rename(columns={"value_a": col_a, "value_b": col_b})
        )
        mean_stats = _try_correlation(means, col_a, col_b, min_pairs=min(MIN_PAIRS, MIN_ENTITIES))
        if mean_stats:
            r, p, n = mean_stats
            idx += 1
            conn.register("_cross_measure_means", means)
            all_findings.append(
                _make_finding(
                    idx=idx,
                    col_a=col_a,
                    col_b=col_b,
                    label_a=label_a,
                    label_b=label_b,
                    r=r,
                    p=p,
                    n=n,
                    resource_id=combined_rid,
                    view="country_means",
                    strategy=strategy,
                    primary=False,
                    coverage={**coverage, "country_means_n": n},
                    sql=(
                        f"SELECT {sql_ident(col_a)}, {sql_ident(col_b)} "
                        f"FROM _cross_measure_means "
                        f"WHERE {sql_ident(col_a)} IS NOT NULL AND {sql_ident(col_b)} IS NOT NULL"
                    ),
                    extra_caveat="Each point is a country average across available years",
                )
            )

        if best:
            chosen_report = {
                "success": True,
                "primary_view": "panel_pooled",
                "summary_note": _coverage_note(
                    strategy=strategy,
                    n_pairs=int(len(merged)),
                    n_entities=n_entities,
                    year_min=year_min,
                    year_max=year_max,
                    label_a=label_a,
                    label_b=label_b,
                ),
                **coverage,
            }
            break

        if not chosen_report:
            chosen_report = {
                "success": False,
                "reason": (
                    f"Found {len(merged)} overlapping country-years across {n_entities} entities, "
                    "but no statistically significant correlation passed thresholds."
                ),
                **coverage,
            }

    result.findings = all_findings
    result.report = chosen_report or {
        "success": False,
        "reason": "No overlapping country-years with values for both indicators.",
    }
    result.paired_ok = bool(best)
    return result
