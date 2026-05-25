"""Per-session DuckDB file helpers."""

from __future__ import annotations

from pathlib import Path

import duckdb

from findings_api.config import settings


def session_db_path(session_id: str) -> Path:
    root = Path(settings.session_data_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{session_id}.duckdb"


def connect(session_id: str) -> duckdb.DuckDBPyConnection:
    path = session_db_path(session_id)
    return duckdb.connect(str(path))


def validate_filter(expr: str) -> bool:
    if not expr or not expr.strip():
        return True
    blocked = (";", "--", "/*", "*/", "drop ", "delete ", "insert ", "update ", "attach ")
    low = expr.lower()
    if any(b in low for b in blocked):
        return False
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_ \t\n\r'.=<>%,-|")
    return all(c in allowed for c in expr)


def build_analysis_view_sql(
    raw_table: str,
    analysis_table: str,
    *,
    filter_sql: str | None,
    total_rows: int,
    analysis_n: int,
    seed: int,
) -> str:
    where = f" WHERE {filter_sql.strip()}" if filter_sql and filter_sql.strip() else ""
    base = f"SELECT * FROM {raw_table}{where}"
    if analysis_n >= total_rows or total_rows <= 0:
        return f"CREATE OR REPLACE TABLE {analysis_table} AS {base}"
    pct = min(100.0, max(0.01, 100.0 * analysis_n / total_rows))
    return (
        f"CREATE OR REPLACE TABLE {analysis_table} AS "
        f"SELECT * FROM ({base}) TABLESAMPLE {pct}% (REPEATABLE, {seed}) "
        f"LIMIT {analysis_n}"
    )
