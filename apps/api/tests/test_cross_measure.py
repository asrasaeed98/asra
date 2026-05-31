"""Harmonized cross-dataset correlation (panel merge + fallback views)."""

import duckdb

from findings_api.analysis.cross_measure import run_cross_measure_analysis
from findings_api.analysis.narrative import enrich_finding

UNEMPLOYMENT = "Unemployment, total (% of total labor force)"
WORKING_CAPITAL = "Working capital (% of total assets)"


def _wb_country_year(conn, table: str, indicator: str, value_fn, *, iso: bool = True):
    rows = []
    countries = [("USA", "United States"), ("GBR", "United Kingdom"), ("DEU", "Germany")]
    for code, name in countries:
        for year in range(2015, 2021):
            entity = code if iso else name
            rows.append((entity, str(year), indicator, float(value_fn(code, year))))
    conn.execute(
        f"CREATE TABLE {table} (countryiso3code VARCHAR, date VARCHAR, indicator VARCHAR, value DOUBLE)"
        if iso
        else f"CREATE TABLE {table} (country VARCHAR, date VARCHAR, indicator VARCHAR, value DOUBLE)"
    )
    col = "countryiso3code" if iso else "country"
    conn.executemany(f"INSERT INTO {table} VALUES (?, ?, ?, ?)", rows)


def test_cross_measure_iso3_pooled_negative_correlation():
    conn = duckdb.connect()
    _wb_country_year(
        conn,
        "left_t",
        UNEMPLOYMENT,
        lambda code, year: hash(code) % 10 + year % 5,
    )
    _wb_country_year(
        conn,
        "right_t",
        WORKING_CAPITAL,
        lambda code, year: 100 - (hash(code) % 10 + year % 5),
    )

    result = run_cross_measure_analysis(
        conn,
        "left_t",
        "right_t",
        left_resource_id="wb-unemp",
        right_resource_id="wb-wc",
        left_title="Unemployment",
        right_title="Working capital",
    )

    assert result.paired_ok
    assert result.report.get("success")
    assert result.report.get("strategy") == "iso3_year"
    pooled = [f for f in result.findings if f.details.get("correlation_view") == "panel_pooled"]
    assert pooled, "expected pooled panel correlation"
    primary = pooled[0]
    assert primary.details.get("primary") is True
    assert primary.value < 0
    enriched = enrich_finding(primary)
    assert "unemployment" in enriched.title.lower()
    assert "working capital" in enriched.title.lower()


def test_cross_measure_filters_wb_aggregates():
    conn = duckdb.connect()
    rows = []
    for i in range(12):
        rows.append(("C{:02d}".format(i), "2020", UNEMPLOYMENT, float(i)))
    rows.append(("IBR", "2020", UNEMPLOYMENT, 99.0))
    rows.append(("IDA only", "2020", UNEMPLOYMENT, 88.0))
    conn.execute(
        "CREATE TABLE left_t (country VARCHAR, date VARCHAR, indicator VARCHAR, value DOUBLE)"
    )
    conn.executemany("INSERT INTO left_t VALUES (?, ?, ?, ?)", rows)

    rows_r = []
    for i in range(12):
        rows_r.append(("C{:02d}".format(i), "2020", WORKING_CAPITAL, float(100 - i)))
    conn.execute(
        "CREATE TABLE right_t (country VARCHAR, date VARCHAR, indicator VARCHAR, value DOUBLE)"
    )
    conn.executemany("INSERT INTO right_t VALUES (?, ?, ?, ?)", rows_r)

    result = run_cross_measure_analysis(
        conn,
        "left_t",
        "right_t",
        left_resource_id="a",
        right_resource_id="b",
        left_title="Unemployment",
        right_title="Working capital",
    )

    assert result.paired_ok
    assert result.report.get("entities") == 12


def test_cross_measure_country_name_fallback():
    conn = duckdb.connect()
    _wb_country_year(
        conn,
        "left_t",
        UNEMPLOYMENT,
        lambda _code, year: float(year % 7),
        iso=False,
    )
    _wb_country_year(
        conn,
        "right_t",
        WORKING_CAPITAL,
        lambda _code, year: float(20 - year % 7),
        iso=False,
    )

    result = run_cross_measure_analysis(
        conn,
        "left_t",
        "right_t",
        left_resource_id="a",
        right_resource_id="b",
        left_title="Unemployment",
        right_title="Working capital",
    )

    assert result.paired_ok
    assert result.report.get("strategy") == "country_year"


def test_cross_measure_sparse_overlap_reports_reason():
    conn = duckdb.connect()
    conn.execute(
        "CREATE TABLE left_t (country VARCHAR, date VARCHAR, indicator VARCHAR, value DOUBLE)"
    )
    conn.executemany(
        "INSERT INTO left_t VALUES (?, ?, ?, ?)",
        [("USA", "2020", UNEMPLOYMENT, 5.0), ("GBR", "2020", UNEMPLOYMENT, 6.0)],
    )
    conn.execute(
        "CREATE TABLE right_t (country VARCHAR, date VARCHAR, indicator VARCHAR, value DOUBLE)"
    )
    conn.executemany(
        "INSERT INTO right_t VALUES (?, ?, ?, ?)",
        [("DEU", "2020", WORKING_CAPITAL, 10.0), ("FRA", "2020", WORKING_CAPITAL, 11.0)],
    )

    result = run_cross_measure_analysis(
        conn,
        "left_t",
        "right_t",
        left_resource_id="a",
        right_resource_id="b",
        left_title="Unemployment",
        right_title="Working capital",
    )

    assert not result.paired_ok
    assert not result.findings
    assert "overlapping" in result.report.get("reason", "").lower()
