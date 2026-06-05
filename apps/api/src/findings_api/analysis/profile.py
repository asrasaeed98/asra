from __future__ import annotations

import re
from typing import Any

import pandas as pd

from findings_api.analysis.types import ColumnProfile, TableProfile

_MAX_CATEGORICAL_CARDINALITY = 50
_MIN_CATEGORICAL_CARDINALITY = 2
# Categorical columns at or below this many distinct values get their full value
# list in dataset_facts (so chat can answer membership questions like "is the US
# in here?"). Above it we fall back to a few examples to keep token cost bounded.
_VALUE_LIST_MAX = 300

_TIME_COLUMN_NAMES = frozenset(
    {"date", "year", "yr", "fiscal_year", "calendar_year", "obs_date", "time_period", "period"}
)
_GEO_COLUMN_NAMES = frozenset(
    {
        "country",
        "countryiso3code",
        "country_code",
        "country_name",
        "state",
        "state_code",
        "state_abbr",
        "stusps",
        "state_name",
        "fips",
        "fips_code",
        "geo_id",
        "geoid",
        "county_fips",
        "region",
        # NYC Open Data
        "borough",
        "boro",
        "boro_nm",
        "borough_name",
        "neighborhood",
        "nta",
        "nta_name",
        "zip",
        "zipcode",
        "zip_code",
        "incident_zip",
        "community_board",
        "community_district",
        "commntyd",
        "police_precinct",
        "precinct",
        "council_district",
    }
)
_METADATA_COLUMN_NAMES = frozenset(
    {"indicator", "indicator_id", "indicator_code", "series_id", "series", "variable"}
)


def _quote_ident(name: str) -> str:
    return f'"{name.replace(chr(34), chr(34) * 2)}"'


def _coerce_to_year_datetime(series: pd.Series) -> pd.Series | None:
    nums = pd.to_numeric(series, errors="coerce")
    if nums.notna().sum() < max(3, int(len(series) * 0.5)):
        return None
    valid = nums.dropna()
    if len(valid) == 0:
        return None
    lo, hi = float(valid.min()), float(valid.max())
    if not (1800 <= lo <= 2100 and 1800 <= hi <= 2100):
        return None
    int_years = nums.round().astype("Int64")
    return pd.to_datetime(int_years.astype(str), format="%Y", errors="coerce")


def read_table_frame(conn, table: str) -> pd.DataFrame:
    df = conn.execute(f"SELECT * FROM {table}").fetchdf()
    for col in list(df.columns):
        series = df[col]
        if series.map(lambda v: isinstance(v, (dict, list))).any():
            df[col] = series.apply(
                lambda v: v.get("value") if isinstance(v, dict) and "value" in v else str(v)
                if isinstance(v, (dict, list))
                else v
            )
            series = df[col]
        low = str(col).lower()
        if low in _TIME_COLUMN_NAMES:
            coerced = _coerce_to_year_datetime(series)
            if coerced is not None:
                df[col] = coerced
                continue
        if pd.api.types.is_numeric_dtype(series):
            continue
        if pd.api.types.is_datetime64_any_dtype(series):
            continue
        as_num = pd.to_numeric(series, errors="coerce")
        if as_num.notna().sum() >= max(3, int(len(df) * 0.5)):
            if low in _TIME_COLUMN_NAMES:
                coerced = _coerce_to_year_datetime(as_num)
                if coerced is not None:
                    df[col] = coerced
                    continue
            df[col] = as_num
            continue
        as_dt = pd.to_datetime(series, errors="coerce", utc=True)
        if as_dt.notna().sum() >= max(3, int(len(df) * 0.5)):
            df[col] = as_dt
    return df


def _safe_nunique(series: pd.Series) -> int:
    try:
        return int(series.nunique(dropna=True))
    except TypeError:
        as_str = series.dropna().astype(str)
        return int(as_str.nunique()) if len(as_str) else 0


def _classify_column(name: str, series: pd.Series) -> str:
    low = name.lower()
    non_null = series.dropna()
    if len(non_null) == 0:
        return "other"
    if low in _METADATA_COLUMN_NAMES:
        return "other"
    if non_null.map(lambda v: isinstance(v, (dict, list))).any():
        return "other"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        if low in _TIME_COLUMN_NAMES:
            return "datetime"
        return "numeric" if _safe_nunique(non_null) > 1 else "other"
    nunique = _safe_nunique(non_null)
    if low in _GEO_COLUMN_NAMES and nunique >= _MIN_CATEGORICAL_CARDINALITY:
        return "categorical"
    if _MIN_CATEGORICAL_CARDINALITY <= nunique <= _MAX_CATEGORICAL_CARDINALITY:
        return "categorical"
    return "other"


def _column_fact(name: str, kind: str, series: pd.Series) -> dict[str, Any]:
    fact: dict[str, Any] = {"name": str(name), "type": kind}
    non_null = series.dropna()
    if len(non_null) == 0:
        return fact
    try:
        if kind == "datetime":
            dt = pd.to_datetime(non_null, errors="coerce").dropna()
            if len(dt):
                lo, hi = dt.min(), dt.max()
                yearly = bool((dt.dt.month == 1).all() and (dt.dt.day == 1).all())
                fact["min"] = str(lo.year) if yearly else lo.date().isoformat()
                fact["max"] = str(hi.year) if yearly else hi.date().isoformat()
        elif kind == "numeric":
            fact["min"] = round(float(non_null.min()), 4)
            fact["max"] = round(float(non_null.max()), 4)
            fact["mean"] = round(float(non_null.mean()), 4)
        elif kind == "categorical":
            cleaned = non_null.astype(str).str.strip()
            cleaned = cleaned[cleaned != ""]
            distinct = int(cleaned.nunique())
            fact["distinct"] = distinct
            if 0 < distinct <= _VALUE_LIST_MAX:
                fact["values"] = sorted(cleaned.unique().tolist())
            else:
                top = cleaned.value_counts().head(6)
                fact["examples"] = [str(v) for v in top.index]
    except (TypeError, ValueError):
        pass
    return fact


def profile_dataframe(
    df: pd.DataFrame,
    *,
    table: str,
    resource_id: str,
    title: str,
) -> TableProfile:
    columns: list[ColumnProfile] = []
    fact_columns: list[dict[str, Any]] = []
    time_coverage: dict[str, Any] | None = None
    for col in df.columns:
        series = df[col]
        kind = _classify_column(str(col), series)
        null_pct = float(series.isna().mean() * 100.0) if len(df) else 0.0
        columns.append(
            ColumnProfile(
                name=str(col),
                dtype=str(series.dtype),
                kind=kind,
                nunique=_safe_nunique(series),
                null_pct=null_pct,
            )
        )
        fact = _column_fact(str(col), kind, series)
        fact_columns.append(fact)
        if kind == "datetime" and time_coverage is None and "min" in fact and "max" in fact:
            time_coverage = {"column": str(col), "start": fact["min"], "end": fact["max"]}

    facts = {
        "title": title,
        "n_rows": len(df),
        "columns": fact_columns,
    }
    if time_coverage is not None:
        facts["time_coverage"] = time_coverage

    return TableProfile(
        table=table,
        resource_id=resource_id,
        title=title,
        n_rows=len(df),
        columns=columns,
        facts=facts,
    )


def profile_table(
    conn,
    table: str,
    *,
    resource_id: str,
    title: str,
    extra_measure_contexts: dict[str, dict[str, str | None]] | None = None,
    portal: str | None = None,
) -> TableProfile:
    from findings_api.analysis.field_relevance import evaluate_fields
    from findings_api.analysis.measure_semantics import (
        MEASURE_COLUMN_NAMES,
        resolve_measure_label,
    )

    df = read_table_frame(conn, table)
    profile = profile_dataframe(df, table=table, resource_id=resource_id, title=title)
    relevance = evaluate_fields(profile.columns, portal=portal)
    profile.field_relevance = relevance.to_dict()
    if profile.facts is not None:
        profile.facts["field_relevance"] = profile.field_relevance

    contexts: dict[str, dict[str, str | None]] = {}
    injected = extra_measure_contexts or {}
    for col in profile.analysis_numeric:
        if col in injected:
            # Pre-resolved before a join (when the source table was unambiguous).
            contexts[col] = injected[col]
        elif col.lower() in MEASURE_COLUMN_NAMES:
            contexts[col] = resolve_measure_label(
                conn, table, col, catalog_title=title, use_ai=True
            )
    profile.measure_contexts = contexts
    return profile


def sql_ident(name: str) -> str:
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        return name
    return _quote_ident(name)


def is_panel_table(profile: TableProfile) -> bool:
    """Long-format indicator panel: geo + time + a single measure column."""
    has_time = bool(profile.datetime)
    has_measure = any(c.name.lower() in ("value", "val") and c.kind == "numeric" for c in profile.columns)
    has_geo = any(c.name.lower() in _GEO_COLUMN_NAMES and c.kind == "categorical" for c in profile.columns)
    return has_time and has_measure and has_geo


def is_geo_column(name: str) -> bool:
    """True when a column name is a geographic grouping field."""
    return name.lower() in _GEO_COLUMN_NAMES


def preferred_geo_column(profile: TableProfile) -> str | None:
    cats = profile.analysis_categorical
    for pref in (
        "borough",
        "boro_nm",
        "neighborhood",
        "nta_name",
        "zipcode",
        "zip_code",
        "community_district",
        "precinct",
        "country",
        "countryiso3code",
        "state",
        "fips",
        "region",
    ):
        if pref in cats:
            return pref
    for name in cats:
        if name.lower() in _GEO_COLUMN_NAMES:
            return name
    return None


def preferred_measure_column(profile: TableProfile) -> str | None:
    nums = profile.analysis_numeric
    for pref in ("value", "val"):
        if pref in nums:
            return pref
    return nums[0] if nums else None


def preferred_time_column(profile: TableProfile) -> str | None:
    dts = profile.analysis_datetime
    for pref in ("date", "year", "obs_date", "time_period"):
        if pref in dts:
            return pref
    return dts[0] if dts else None
