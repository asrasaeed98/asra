import duckdb

from findings_api.analysis.join import assess_join, count_join_rows, max_key_duplication, safe_join_columns


def test_max_key_duplication():
    conn = duckdb.connect()
    conn.execute("CREATE TABLE t AS SELECT * FROM (VALUES ('A'), ('A'), ('B')) v(k)")
    assert max_key_duplication(conn, "t", "k") == 2


def test_assess_join_rejects_duplicate_keys_on_both_sides():
    conn = duckdb.connect()
    conn.execute("CREATE TABLE a AS SELECT * FROM (VALUES ('X', 1), ('X', 2)) v(k, v)")
    conn.execute("CREATE TABLE b AS SELECT * FROM (VALUES ('X', 3), ('X', 4)) v(k, v)")
    ok, matched, warning = assess_join(conn, "a", "b", "k")
    assert not ok
    assert matched == 0
    assert warning is not None
    assert "both" in warning.lower()


def test_assess_join_allows_many_to_one():
    conn = duckdb.connect()
    conn.execute("CREATE TABLE a AS SELECT 'X' AS k, i AS v FROM range(8) t(i)")
    conn.execute("CREATE TABLE b AS SELECT 'X' AS k, 99 AS v")
    ok, matched, warning = assess_join(conn, "a", "b", "k")
    assert ok
    assert matched == 8
    assert warning is None


def test_safe_join_columns_filters_unsafe_shared_names():
    conn = duckdb.connect()
    conn.execute("CREATE TABLE raw_0 AS SELECT * FROM (VALUES ('US', 2020, 1.0), ('US', 2021, 2.0)) v(country, year, v)")
    conn.execute("CREATE TABLE raw_1 AS SELECT * FROM (VALUES ('US', 2020, 10.0), ('US', 2021, 11.0)) v(country, year, v)")
    profiles = [
        {
            "raw_table": "raw_0",
            "analysis_table": "raw_0",
            "columns": [{"name": "country"}, {"name": "year"}, {"name": "v"}],
        },
        {
            "raw_table": "raw_1",
            "analysis_table": "raw_1",
            "columns": [{"name": "country"}, {"name": "year"}, {"name": "v"}],
        },
    ]
    # country repeats on both sides — unsafe; year repeats on both — unsafe
    assert safe_join_columns(conn, profiles) == []


def test_count_join_rows():
    conn = duckdb.connect()
    conn.execute("CREATE TABLE l AS SELECT * FROM (VALUES ('A'), ('B')) v(k)")
    conn.execute("CREATE TABLE r AS SELECT * FROM (VALUES ('A'), ('C')) v(k)")
    assert count_join_rows(conn, "l", "r", "k") == 1
