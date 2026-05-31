"""Read-only DuckDB queries for grounded chat follow-ups."""

from __future__ import annotations

import json
import re
from typing import Any

import duckdb

from findings_api.config import settings

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|create|alter|attach|copy|pragma|export|install|load|"
    r"replace|truncate|grant|revoke|call|execute|prepare)\b",
    re.IGNORECASE,
)
_TABLE_REF = re.compile(
    r"\b(?:from|join)\s+([\"`]?(?:[a-zA-Z_][a-zA-Z0-9_]*)[\"`]?)",
    re.IGNORECASE,
)
_LIMIT_RE = re.compile(r"\blimit\s+(\d+)", re.IGNORECASE)

# Prefer analysis / join tables over raw downloads.
_PREFERRED_PREFIXES = ("analysis_", "cross_measure_", "analysis_joined")


def _normalize_table(name: str) -> str:
    return name.strip().strip('"`')


def list_queryable_tables(conn: duckdb.DuckDBPyConnection) -> list[str]:
    rows = conn.execute("SHOW TABLES").fetchall()
    names = [_normalize_table(str(r[0])) for r in rows]
    allowed = []
    for name in names:
        if name.startswith("raw_"):
            continue
        if name.startswith("analysis") or name.startswith("cross_measure"):
            allowed.append(name)
    return sorted(allowed, key=lambda n: (0 if n.startswith(_PREFERRED_PREFIXES) else 1, n))


def describe_table(conn: duckdb.DuckDBPyConnection, table: str) -> dict[str, Any]:
    safe = _normalize_table(table)
    rows = conn.execute(f"DESCRIBE {safe}").fetchall()
    count = int(conn.execute(f"SELECT COUNT(*) FROM {safe}").fetchone()[0])
    columns = [{"name": str(r[0]), "type": str(r[1])} for r in rows]
    return {"table": safe, "n_rows": count, "columns": columns}


def build_query_schema(conn: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    return [describe_table(conn, t) for t in list_queryable_tables(conn)]


def validate_chat_sql(sql: str, allowed_tables: set[str]) -> tuple[bool, str]:
    text = sql.strip()
    if not text:
        return False, "Empty query"
    if ";" in text.rstrip(";"):
        return False, "Only a single SELECT statement is allowed"
    body = text.rstrip(";").strip()
    if not body.lower().startswith("select"):
        return False, "Only SELECT queries are allowed"
    if _FORBIDDEN.search(body):
        return False, "Query contains a forbidden keyword"
    if "--" in body or "/*" in body:
        return False, "SQL comments are not allowed"
    referenced = {_normalize_table(m.group(1)) for m in _TABLE_REF.finditer(body)}
    if not referenced:
        return False, "Query must read from a session table (FROM ...)"
    unknown = referenced - allowed_tables
    if unknown:
        return False, f"Table(s) not allowed: {', '.join(sorted(unknown))}"
    return True, ""


def _apply_row_limit(sql: str, max_rows: int) -> str:
    body = sql.strip().rstrip(";")
    match = _LIMIT_RE.search(body)
    if match:
        current = int(match.group(1))
        if current > max_rows:
            body = _LIMIT_RE.sub(f"LIMIT {max_rows}", body, count=1)
        return body
    return f"{body} LIMIT {max_rows}"


def execute_chat_query(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    *,
    max_rows: int | None = None,
) -> dict[str, Any]:
    """Run a validated read-only query; returns JSON-serializable rows."""
    cap = max_rows if max_rows is not None else settings.chat_query_max_rows
    allowed = set(list_queryable_tables(conn))
    ok, reason = validate_chat_sql(sql, allowed)
    if not ok:
        return {"ok": False, "error": reason, "rows": [], "columns": []}

    query = _apply_row_limit(sql, cap)
    try:
        df = conn.execute(query).fetchdf()
    except duckdb.Error as exc:
        return {"ok": False, "error": str(exc).split("\n")[0][:200], "rows": [], "columns": []}

    if len(df) > cap:
        df = df.head(cap)
    rows = json.loads(df.to_json(orient="records", date_format="iso"))
    return {
        "ok": True,
        "sql": query,
        "columns": [str(c) for c in df.columns],
        "n": len(rows),
        "rows": rows,
    }
