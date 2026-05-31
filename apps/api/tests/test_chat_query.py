"""Chat DuckDB query validation and execution."""

import duckdb

from findings_api.analysis.chat_sql import (
    build_query_schema,
    execute_chat_query,
    list_queryable_tables,
    validate_chat_sql,
)


def _setup(conn):
    conn.execute(
        "CREATE TABLE analysis_0 (country VARCHAR, year INTEGER, electricity DOUBLE, literacy DOUBLE)"
    )
    conn.executemany(
        "INSERT INTO analysis_0 VALUES (?, ?, ?, ?)",
        [
            ("USA", 2020, 100.0, 99.0),
            ("NGA", 2020, 55.0, 62.0),
            ("FIN", 2020, 100.0, 99.0),
        ],
    )
    conn.execute("CREATE TABLE raw_0 (country VARCHAR, value DOUBLE)")
    conn.executemany("INSERT INTO raw_0 VALUES (?, ?)", [("X", 1.0)])


def test_list_queryable_tables_excludes_raw():
    conn = duckdb.connect()
    _setup(conn)
    assert list_queryable_tables(conn) == ["analysis_0"]


def test_validate_rejects_non_select():
    ok, msg = validate_chat_sql("DELETE FROM analysis_0", {"analysis_0"})
    assert not ok
    assert "SELECT" in msg


def test_validate_rejects_unknown_table():
    ok, _ = validate_chat_sql("SELECT * FROM secret_table", {"analysis_0"})
    assert not ok


def test_execute_ranking_query():
    conn = duckdb.connect()
    _setup(conn)
    result = execute_chat_query(
        conn,
        "SELECT country, electricity FROM analysis_0 ORDER BY electricity ASC LIMIT 1",
    )
    assert result["ok"]
    assert result["rows"][0]["country"] == "NGA"


def test_build_query_schema():
    conn = duckdb.connect()
    _setup(conn)
    schema = build_query_schema(conn)
    assert schema[0]["table"] == "analysis_0"
    assert schema[0]["n_rows"] == 3
    assert any(c["name"] == "country" for c in schema[0]["columns"])
