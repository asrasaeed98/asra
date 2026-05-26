from __future__ import annotations

import re

import pandas as pd

from findings_api.analysis.types import ColumnProfile, TableProfile

_MAX_CATEGORICAL_CARDINALITY = 50
_MIN_CATEGORICAL_CARDINALITY = 2


def _quote_ident(name: str) -> str:
    return f'"{name.replace(chr(34), chr(34) * 2)}"'


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
        if low in ("date", "year") and pd.api.types.is_numeric_dtype(series):
            years = pd.to_numeric(series, errors="coerce").dropna()
            if len(years) and float(years.min()) >= 1800 and float(years.max()) <= 2100:
                df[col] = pd.to_datetime(years.astype(int).astype(str), format="%Y", errors="coerce")
                continue
        if pd.api.types.is_numeric_dtype(series):
            continue
        if pd.api.types.is_datetime64_any_dtype(series):
            continue
        as_num = pd.to_numeric(series, errors="coerce")
        if as_num.notna().sum() >= max(3, int(len(df) * 0.5)):
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


def _classify_column(series: pd.Series) -> str:
    non_null = series.dropna()
    if len(non_null) == 0:
        return "other"
    if non_null.map(lambda v: isinstance(v, (dict, list))).any():
        return "other"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric" if _safe_nunique(non_null) > 1 else "other"
    nunique = _safe_nunique(non_null)
    if _MIN_CATEGORICAL_CARDINALITY <= nunique <= _MAX_CATEGORICAL_CARDINALITY:
        return "categorical"
    return "other"


def profile_dataframe(
    df: pd.DataFrame,
    *,
    table: str,
    resource_id: str,
    title: str,
) -> TableProfile:
    columns: list[ColumnProfile] = []
    for col in df.columns:
        series = df[col]
        kind = _classify_column(series)
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
    return TableProfile(
        table=table,
        resource_id=resource_id,
        title=title,
        n_rows=len(df),
        columns=columns,
    )


def profile_table(
    conn,
    table: str,
    *,
    resource_id: str,
    title: str,
) -> TableProfile:
    df = read_table_frame(conn, table)
    return profile_dataframe(df, table=table, resource_id=resource_id, title=title)


def sql_ident(name: str) -> str:
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        return name
    return _quote_ident(name)
