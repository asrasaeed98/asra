"""Tests for Vega-Lite chart generation."""

import duckdb

from findings_api.analysis.charts import charts_for_findings
from findings_api.analysis.types import Finding


def _finding(**kwargs) -> Finding:
    defaults = {
        "id": "f_1",
        "title": "Test finding",
        "columns": [],
        "value": 0.5,
        "p_value": 0.01,
        "n": 100,
        "method": "test",
        "caveat": "test",
        "sql": "SELECT 1",
        "datasets": ["ds:1"],
        "score": 1.0,
        "details": {},
    }
    defaults.update(kwargs)
    return Finding(**defaults)


def test_scatter_chart_embeds_data():
    conn = duckdb.connect()
    conn.execute("CREATE TABLE t AS SELECT i AS x, i * 2 AS y FROM range(30) t(i)")
    finding = _finding(
        type="spearman_correlation",
        columns=["x", "y"],
        sql="SELECT x, y FROM t",
    )
    charts = charts_for_findings(conn, [finding])
    assert len(charts) == 1
    assert charts[0].type == "scatter"
    values = charts[0].spec["data"]["values"]
    assert len(values) == 30
    assert "x" in values[0] and "y" in values[0]


def test_bar_chart_uses_aggregated_sql():
    conn = duckdb.connect()
    conn.execute(
        "CREATE TABLE t AS SELECT CASE WHEN i % 2 = 0 THEN 'A' ELSE 'B' END AS grp, i AS val "
        "FROM range(20) t(i)"
    )
    finding = _finding(
        type="group_comparison",
        columns=["val", "grp"],
        sql="SELECT grp, AVG(val) AS mean_value FROM t GROUP BY 1 ORDER BY 2 DESC",
    )
    charts = charts_for_findings(conn, [finding])
    assert len(charts) == 1
    assert charts[0].type == "bar"
    values = charts[0].spec["data"]["values"]
    assert len(values) == 2
    assert "mean_value" in values[0]


def test_skips_finding_when_sql_returns_no_rows():
    conn = duckdb.connect()
    conn.execute("CREATE TABLE t AS SELECT 1 AS x")
    finding = _finding(
        type="spearman_correlation",
        columns=["x", "missing"],
        sql="SELECT x, missing FROM t",
    )
    charts = charts_for_findings(conn, [finding])
    assert charts == []


def test_bar_chart_trims_many_categories():
    conn = duckdb.connect()
    rows = ", ".join(f"('C{i}', {100 - i}.0)" for i in range(20))
    conn.execute(f"CREATE TABLE t AS SELECT * FROM (VALUES {rows}) v(grp, mean_value)")
    finding = _finding(
        type="group_comparison",
        columns=["val", "grp"],
        sql="SELECT grp, mean_value FROM t ORDER BY 2 DESC",
    )
    charts = charts_for_findings(conn, [finding])
    assert len(charts) == 1
    values = charts[0].spec["data"]["values"]
    assert len(values) == 10
    assert "top 10 of 20" in charts[0].title


def test_skips_country_code_chart_when_country_present():
    conn = duckdb.connect()
    conn.execute(
        "CREATE TABLE t AS SELECT * FROM (VALUES ('USA', 'United States', 50.0), ('CAN', 'Canada', 70.0)) "
        "v(countryiso3code, country, mean_value)"
    )
    iso_finding = _finding(
        id="f_iso",
        type="group_comparison",
        columns=["val", "countryiso3code"],
        sql="SELECT countryiso3code, mean_value FROM t",
    )
    country_finding = _finding(
        id="f_country",
        type="group_comparison",
        columns=["val", "country"],
        sql="SELECT country, mean_value FROM t",
    )
    charts = charts_for_findings(conn, [iso_finding, country_finding])
    assert len(charts) == 1
    assert charts[0].finding_id == "f_country"
