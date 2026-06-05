"""JSON ingest must tolerate heterogeneous row shapes from NYC Open Data and other portals."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from findings_api.ingest.download import DownloadError
from findings_api.ingest.pipeline import (
    _flatten_fred_observations,
    _flatten_worldbank_rows,
    _load_bytes,
    _load_json,
    _series_id_from_resource,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _conn():
    return duckdb.connect()


def _table_columns(conn, table: str) -> set[str]:
    return {row[0] for row in conn.execute(f"DESCRIBE {table}").fetchall()}


def test_load_json_unions_keys_across_heterogeneous_rows():
    rows = [
        {"created": "2017-10-04T15:30:11.000", "bic_number": "HPA-1"},
        {
            "created": "2018-01-02T10:00:00.000",
            "bic_number": "HPM-2",
            "boro": "MANHATTAN",
            "account_name": "Example Market LLC",
        },
    ]
    data = json.dumps(rows).encode("utf-8")
    conn = _conn()
    try:
        _load_json(conn, "raw_0", data, portal="nyc_open_data")
        cols = _table_columns(conn, "raw_0")
        assert {"created", "bic_number", "boro", "account_name"}.issubset(cols)
        loaded = conn.execute(
            "SELECT bic_number, boro, account_name FROM raw_0 ORDER BY bic_number"
        ).fetchall()
        assert loaded == [
            ("HPA-1", None, None),
            ("HPM-2", "MANHATTAN", "Example Market LLC"),
        ]
    finally:
        conn.close()


def test_load_json_handles_late_appearing_columns_like_production_dataset():
    """Mimic Wholesale Markets: many rows omit boro; later rows include it."""
    rows = [{"created": "2017-01-01", "bic_number": f"FFM-{i}"} for i in range(400)]
    rows.append({"created": "2017-10-04T15:30:11.000", "bic_number": "FFM-999", "boro": "BRONX"})
    data = json.dumps(rows).encode("utf-8")
    conn = _conn()
    try:
        _load_json(conn, "raw_0", data, portal="nyc_open_data")
        assert conn.execute("SELECT COUNT(*) FROM raw_0").fetchone()[0] == 401
        assert "boro" in _table_columns(conn, "raw_0")
    finally:
        conn.close()


def test_load_json_fixture_resembles_production_wholesale_markets():
    data = (FIXTURES / "nyc_wholesale_markets_sample.json").read_bytes()
    conn = _conn()
    try:
        _load_json(conn, "raw_0", data, portal="nyc_open_data")
        assert conn.execute("SELECT COUNT(*) FROM raw_0").fetchone()[0] == 4
        cols = _table_columns(conn, "raw_0")
        assert "boro" in cols
        assert "account_name" in cols
        assert "trade_name" in cols
        assert ":id" in cols
        assert conn.execute(
            "SELECT COUNT(*) FROM raw_0 WHERE boro IS NOT NULL"
        ).fetchone()[0] == 2
    finally:
        conn.close()


@pytest.mark.parametrize("row_count", [500, 2000])
def test_load_json_heterogeneous_rows_beyond_default_schema_sample(row_count: int):
    """Regression: DuckDB default schema sampling fails when keys appear after row ~20k."""
    rows = [{"created": "2017-01-01", "bic_number": f"ROW-{i}"} for i in range(row_count - 1)]
    rows.append(
        {
            "created": "2017-10-04T15:30:11.000",
            "bic_number": "ROW-LAST",
            "boro": "QUEENS",
            "account_name": "Late schema column",
        }
    )
    data = json.dumps(rows).encode("utf-8")
    conn = _conn()
    try:
        _load_json(conn, "raw_0", data, portal="nyc_open_data")
        assert conn.execute("SELECT COUNT(*) FROM raw_0").fetchone()[0] == row_count
        assert "boro" in _table_columns(conn, "raw_0")
        last = conn.execute(
            "SELECT bic_number, boro, account_name FROM raw_0 WHERE bic_number = 'ROW-LAST'"
        ).fetchone()
        assert last == ("ROW-LAST", "QUEENS", "Late schema column")
    finally:
        conn.close()


def test_load_json_preserves_socrata_system_columns():
    rows = [
        {":id": "row-1", ":version": "rv-1", "bic_number": "A"},
        {"bic_number": "B", "boro": "BROOKLYN"},
    ]
    data = json.dumps(rows).encode("utf-8")
    conn = _conn()
    try:
        _load_json(conn, "raw_0", data, portal="nyc_open_data")
        assert {":id", "bic_number", "boro"}.issubset(_table_columns(conn, "raw_0"))
        assert conn.execute("SELECT COUNT(*) FROM raw_0").fetchone()[0] == 2
    finally:
        conn.close()


def test_load_json_many_optional_columns_union_without_error():
    rows = [
        {"id": 1, "alpha": "a"},
        {"id": 2, "beta": "b"},
        {"id": 3, "gamma": "c"},
        {"id": 4, "delta": "d", "alpha": "aa"},
        {"id": 5, "epsilon": "e", "beta": "bb", "gamma": "cc"},
    ]
    data = json.dumps(rows).encode("utf-8")
    conn = _conn()
    try:
        _load_json(conn, "raw_0", data, portal="nyc_open_data")
        assert _table_columns(conn, "raw_0") == {"id", "alpha", "beta", "gamma", "delta", "epsilon"}
    finally:
        conn.close()


def test_load_json_empty_rows_creates_placeholder_table():
    data = json.dumps([]).encode("utf-8")
    conn = _conn()
    try:
        _load_json(conn, "raw_0", data, portal="nyc_open_data")
        cols = _table_columns(conn, "raw_0")
        assert cols == {"placeholder"}
        assert conn.execute("SELECT COUNT(*) FROM raw_0").fetchone()[0] == 0
    finally:
        conn.close()


def test_load_json_single_object_payload():
    data = json.dumps({"created": "2020-01-01", "value": 42}).encode("utf-8")
    conn = _conn()
    try:
        _load_json(conn, "raw_0", data, portal="nyc_open_data")
        assert conn.execute("SELECT COUNT(*) FROM raw_0").fetchone()[0] == 1
        assert conn.execute("SELECT value FROM raw_0").fetchone()[0] == 42
    finally:
        conn.close()


def test_load_json_unsupported_shape_raises():
    data = b'"just a string"'
    conn = _conn()
    try:
        with pytest.raises(DownloadError, match="Unsupported JSON shape"):
            _load_json(conn, "raw_0", data, portal="nyc_open_data")
    finally:
        conn.close()


def test_load_json_worldbank_envelope():
    rows = [
        {
            "countryiso3code": "USA",
            "indicator": {"id": "SP.POP.TOTL", "value": "Population"},
            "country": {"id": "US", "value": "United States"},
            "date": "2020",
            "value": 331000000,
        },
        {
            "countryiso3code": "CAN",
            "indicator": {"id": "SP.POP.TOTL", "value": "Population"},
            "country": {"id": "CA", "value": "Canada"},
            "date": "2020",
            "value": 38000000,
        },
    ]
    payload = [{"page": 1, "pages": 1, "total": 2}, rows]
    data = json.dumps(payload).encode("utf-8")
    conn = _conn()
    try:
        _load_json(conn, "raw_0", data, portal="world_bank")
        assert conn.execute("SELECT COUNT(*) FROM raw_0").fetchone()[0] == 2
        cols = _table_columns(conn, "raw_0")
        assert {"country", "indicator", "date", "value", "countryiso3code"}.issubset(cols)
        usa = conn.execute(
            "SELECT countryiso3code, indicator, value FROM raw_0 WHERE countryiso3code = 'USA'"
        ).fetchone()
        assert usa == ("USA", "Population", 331000000)
    finally:
        conn.close()


def test_flatten_worldbank_rows_handles_nested_objects():
    rows = [
        {
            "countryiso3code": "USA",
            "indicator": {"id": "X", "value": "Indicator X"},
            "country": {"id": "US", "value": "United States"},
            "date": "2020",
            "value": {"value": 99},
        }
    ]
    flat = _flatten_worldbank_rows(rows)
    assert flat == [
        {
            "countryiso3code": "USA",
            "country": "United States",
            "indicator_id": "X",
            "indicator": "Indicator X",
            "date": "2020",
            "value": 99,
        }
    ]


def test_load_json_fred_observations():
    payload = {
        "count": 3,
        "observations": [
            {"date": "2020-01-01", "value": "1.5"},
            {"date": "2020-02-01", "value": "."},
            {"date": "2020-03-01", "value": "2.5"},
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    conn = _conn()
    try:
        _load_json(
            conn,
            "raw_0",
            data,
            portal="fred",
            resource_id="fred:UNRATE",
            resource_url="https://api.stlouisfed.org/fred/series/observations?series_id=UNRATE",
        )
        assert conn.execute("SELECT COUNT(*) FROM raw_0").fetchone()[0] == 2
        rows = conn.execute(
            "SELECT CAST(date AS VARCHAR), value, series_id FROM raw_0 ORDER BY date"
        ).fetchall()
        assert rows == [("2020-01-01", 1.5, "UNRATE"), ("2020-03-01", 2.5, "UNRATE")]
    finally:
        conn.close()


def test_flatten_fred_observations_skips_missing_values():
    rows = _flatten_fred_observations(
        [
            {"date": "2020-01-01", "value": "10"},
            {"date": "2020-02-01", "value": "."},
            {"date": "2020-03-01", "value": ""},
            {"date": "2020-04-01", "value": "bad"},
        ],
        "GDP",
    )
    assert rows == [{"date": "2020-01-01", "value": 10.0, "series_id": "GDP"}]


def test_series_id_from_resource_prefers_resource_id():
    assert (
        _series_id_from_resource(
            "fred:UNRATE",
            "https://api.stlouisfed.org/fred/series/observations?series_id=HOUST",
        )
        == "UNRATE"
    )


def test_load_bytes_routes_world_bank_portal_through_json_loader():
    rows = [{"id": 1, "value": 10}, {"id": 2, "value": 20}]
    data = json.dumps(rows).encode("utf-8")
    conn = _conn()
    try:
        _load_bytes(conn, "raw_0", data, kind="csv", portal="world_bank")
        assert conn.execute("SELECT COUNT(*) FROM raw_0").fetchone()[0] == 2
        assert _table_columns(conn, "raw_0") == {"id", "value"}
    finally:
        conn.close()


def test_load_bytes_routes_json_kind_through_json_loader():
    rows = [{"alpha": 1}, {"alpha": 2, "beta": 3}]
    data = json.dumps(rows).encode("utf-8")
    conn = _conn()
    try:
        _load_bytes(conn, "raw_0", data, kind="json", portal="nyc_open_data")
        assert conn.execute("SELECT COUNT(*) FROM raw_0").fetchone()[0] == 2
        assert _table_columns(conn, "raw_0") == {"alpha", "beta"}
    finally:
        conn.close()


def test_load_bytes_csv_path_still_works_for_tabular_data():
    data = b"year,value\n2020,1\n2021,2\n2022,3\n"
    conn = _conn()
    try:
        _load_bytes(conn, "raw_0", data, kind="csv", portal="data_gov")
        assert conn.execute("SELECT COUNT(*) FROM raw_0").fetchone()[0] == 3
        assert _table_columns(conn, "raw_0") == {"year", "value"}
    finally:
        conn.close()
