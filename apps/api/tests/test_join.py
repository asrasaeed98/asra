import duckdb

from findings_api.analysis.join import (
    assess_join,
    assess_join_on,
    build_joined_table_on,
    count_join_rows,
    max_key_duplication,
    safe_join_columns,
    suggest_joins,
)


def _panel_rows(countries=("US", "CA", "MX", "GB", "FR"), years=(2018, 2019)):
    """Multi-country panel: single-key joins on country or year are unsafe."""
    rows_a = []
    rows_b = []
    for i, country in enumerate(countries):
        for j, year in enumerate(years):
            idx = i * len(years) + j
            rows_a.append(f"('{country}', {year}, {idx}.0)")
            rows_b.append(f"('{country}', {year}, {idx * 10}.0)")
    return ", ".join(rows_a), ", ".join(rows_b)


def test_max_key_duplication():
    conn = duckdb.connect()
    conn.execute("CREATE TABLE t AS SELECT * FROM (VALUES ('A'), ('A'), ('B')) v(k)")
    assert max_key_duplication(conn, "t", "k") == 2


def _country_year_profiles(conn):
    rows_a, rows_b = _panel_rows()
    conn.execute(f"CREATE TABLE raw_0 AS SELECT * FROM (VALUES {rows_a}) v(country, year, v)")
    conn.execute(f"CREATE TABLE raw_1 AS SELECT * FROM (VALUES {rows_b}) v(country, year, v)")
    return [
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


def test_composite_join_country_year():
    conn = duckdb.connect()
    rows_a = ", ".join(f"('US', {y}, {y}.0)" for y in range(2015, 2025))
    rows_b = ", ".join(f"('US', {y}, {y * 10}.0)" for y in range(2015, 2025))
    conn.execute(f"CREATE TABLE a AS SELECT * FROM (VALUES {rows_a}) v(country, year, v)")
    conn.execute(f"CREATE TABLE b AS SELECT * FROM (VALUES {rows_b}) v(country, year, v)")
    pairs = [("country", "country"), ("year", "year")]
    ok, matched, warning, ol, or_ = assess_join_on(conn, "a", "b", pairs)
    assert ok
    assert matched == 10
    assert warning is None
    assert ol == 1.0
    assert or_ == 1.0
    build_joined_table_on(conn, "a", "b", pairs)
    assert int(conn.execute("SELECT COUNT(*) FROM analysis_joined").fetchone()[0]) == 10


def test_suggest_joins_ranks_composite_over_weak_single():
    conn = duckdb.connect()
    profiles = _country_year_profiles(conn)
    suggestions = suggest_joins(conn, profiles)
    assert suggestions
    assert suggestions[0].ok
    assert "country" in suggestions[0].label.lower()
    assert "year" in suggestions[0].label.lower()
    assert suggestions[0].matched_rows >= 8


def test_auto_join_selection_prefers_recommended():
    from findings_api.analysis.join import JoinSuggestion, auto_join_selection

    suggestions = [
        JoinSuggestion(
            keys=["year"],
            left_keys=["year"],
            right_keys=["year"],
            label="year",
            matched_rows=5,
            overlap_left_pct=0.5,
            overlap_right_pct=0.5,
            score=0.6,
            ok=False,
        ),
        JoinSuggestion(
            keys=["country", "year"],
            left_keys=["country", "year"],
            right_keys=["country", "year"],
            label="country + year",
            matched_rows=20,
            overlap_left_pct=0.95,
            overlap_right_pct=0.95,
            score=0.95,
            ok=True,
            auto_recommended=True,
        ),
    ]
    picked = auto_join_selection(suggestions)
    assert picked is not None
    assert picked.label == "country + year"


def test_safe_join_columns_filters_unsafe_shared_names():
    conn = duckdb.connect()
    profiles = _country_year_profiles(conn)
    # country or year alone repeats on both sides — unsafe; composite country+year is safe
    labels = safe_join_columns(conn, profiles)
    assert any("country" in lbl and "year" in lbl for lbl in labels)


def test_count_join_rows():
    conn = duckdb.connect()
    conn.execute("CREATE TABLE l AS SELECT * FROM (VALUES ('A'), ('B')) v(k)")
    conn.execute("CREATE TABLE r AS SELECT * FROM (VALUES ('A'), ('C')) v(k)")
    assert count_join_rows(conn, "l", "r", "k") == 1
