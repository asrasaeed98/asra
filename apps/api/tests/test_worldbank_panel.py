import duckdb
import pandas as pd

from findings_api.analysis.profile import (
    is_panel_table,
    preferred_geo_column,
    preferred_measure_column,
    profile_table,
    read_table_frame,
)
from findings_api.analysis.selector import plans_for_table
from findings_api.analysis.tests.trend import run_trend


def _worldbank_frame() -> pd.DataFrame:
    rows = []
    countries = [("USA", "United States"), ("CAN", "Canada"), ("MEX", "Mexico")]
    for year in range(2000, 2012):
        for iso, name in countries:
            base = {"USA": 50, "CAN": 70, "MEX": 30}[iso]
            rows.append(
                {
                    "countryiso3code": iso,
                    "country": name,
                    "indicator_id": "EG.CFT.ACCS.ZS",
                    "indicator": "Access to clean fuels",
                    "date": str(year),
                    "value": float(base + (year - 2000) * 2 + hash(iso) % 5),
                }
            )
    return pd.DataFrame(rows)


def test_worldbank_string_date_profiles_as_panel():
    conn = duckdb.connect()
    df = _worldbank_frame()
    conn.register("wb_tmp", df)
    conn.execute("CREATE TABLE wb AS SELECT * FROM wb_tmp")
    profile = profile_table(conn, "wb", resource_id="wb:EG.CFT.ACCS.ZS", title="Access to Clean Fuels (% of population)")
    assert "value" in profile.numeric
    assert "country" in profile.categorical
    assert "date" in profile.datetime
    assert all(c.kind == "other" for c in profile.columns if c.name == "indicator_id")


def test_read_table_frame_coerces_string_dates():
    conn = duckdb.connect()
    df = _worldbank_frame()
    conn.register("wb_tmp", df)
    conn.execute("CREATE TABLE wb AS SELECT * FROM wb_tmp")
    loaded = read_table_frame(conn, "wb")
    assert pd.api.types.is_datetime64_any_dtype(loaded["date"])


def test_plans_for_worldbank_panel_includes_geo_and_trend():
    conn = duckdb.connect()
    df = _worldbank_frame()
    conn.register("wb_tmp", df)
    conn.execute("CREATE TABLE wb AS SELECT * FROM wb_tmp")
    profile = profile_table(conn, "wb", resource_id="wb:1", title="Access to Clean Fuels")
    plans = plans_for_table(profile)
    kinds = [p.kind for p in plans]
    assert "group_comparison" in kinds
    assert "trend" in kinds
    trend = next(p for p in plans if p.kind == "trend" and p.columns[0] == "value")
    assert trend.extra and trend.extra.get("aggregate_by_time")
    assert trend.extra.get("tier") == "derived"


def test_trend_aggregates_panel_before_regression():
    conn = duckdb.connect()
    df = _worldbank_frame()
    conn.register("wb_tmp", df)
    conn.execute("CREATE TABLE wb AS SELECT * FROM wb_tmp")
    profile = profile_table(conn, "wb", resource_id="wb:1", title="Access to Clean Fuels")
    findings = run_trend(
        conn,
        "wb",
        "value",
        "date",
        resource_id="wb:1",
        dataset_title=profile.title,
        finding_offset=0,
        aggregate_by_time=True,
    )
    assert findings
    assert findings[0].type == "time_trend"
    assert "Access to Clean Fuels" in findings[0].title
    assert "AVG" in findings[0].sql.upper()
