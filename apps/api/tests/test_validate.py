"""Tests for pre-analysis table validation."""

import duckdb

from findings_api.catalog.validate import validate_table


def test_validate_table_ok():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE t AS SELECT * FROM (VALUES (1, 'a'), (2, 'b'), (3, 'c')) AS v(x, y)")
    result = validate_table(conn, "t", min_rows=2)
    assert result.ok
    assert result.row_count == 3
    conn.close()


def test_validate_table_rejects_too_few_rows():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE t AS SELECT 1 AS x, 'a' AS y")
    result = validate_table(conn, "t", min_rows=20)
    assert not result.ok
    assert "only 1 row" in result.reason
    conn.close()
