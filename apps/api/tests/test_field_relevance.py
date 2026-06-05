"""Field relevance evaluation for NYC and general datasets."""

from __future__ import annotations

from findings_api.analysis.field_relevance import (
    classify_field,
    dedupe_geo_columns,
    evaluate_fields,
)
from findings_api.analysis.profile import profile_dataframe, profile_table
from findings_api.analysis.selector import plans_for_table
from findings_api.analysis.types import ColumnProfile, TableProfile
from findings_api.catalog.socrata import build_scalar_soql, scalar_field_names
import pandas as pd


def _col(name: str, kind: str, nunique: int = 10) -> ColumnProfile:
    return ColumnProfile(name=name, dtype="x", kind=kind, nunique=nunique, null_pct=0.0)


def test_classify_nyc_geographic_and_core():
    assert classify_field("boro_nm", kind="categorical") == "geographic"
    assert classify_field("ofns_desc", kind="categorical") == "core_analytical"
    assert classify_field("latitude", kind="numeric") == "metadata"
    assert classify_field("cmplnt_num", kind="categorical") == "administrative_identifier"


def test_evaluate_excludes_coords_when_borough_present():
    columns = [
        _col("boro_nm", "categorical", 5),
        _col("ofns_desc", "categorical", 40),
        _col("latitude", "numeric", 5000),
        _col("longitude", "numeric", 5000),
        _col("cmplnt_num", "categorical", 9000),
        _col("unique_key", "categorical", 9000),
    ]
    report = evaluate_fields(columns, portal="nyc_open_data")

    ranked_names = [f.name for f in report.ranked_fields]
    excluded_names = [f.name for f in report.excluded_fields]

    assert "boro_nm" in ranked_names
    assert "ofns_desc" in ranked_names
    assert "latitude" in excluded_names
    assert "longitude" in excluded_names
    assert "cmplnt_num" in excluded_names
    assert report.analysis_columns["categorical"][0] == "boro_nm"


def test_recommends_borough_from_coordinates():
    columns = [
        _col("latitude", "numeric", 5000),
        _col("longitude", "numeric", 5000),
        _col("ofns_desc", "categorical", 30),
    ]
    report = evaluate_fields(columns, portal="nyc_open_data")
    dims = {d.dimension for d in report.derived_dimensions}
    assert "borough" in dims
    assert "neighborhood" in dims


def test_dedupe_nyc_borough_variants():
    assert dedupe_geo_columns(["boro_nm", "borough", "ofns_desc"]) == ["boro_nm", "ofns_desc"]


def test_selector_skips_latitude_for_group_comparisons():
    df = pd.DataFrame(
        {
            "boro_nm": ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX"] * 10,
            "ofns_desc": ["THEFT", "ASSAULT", "BURGLARY", "FRAUD"] * 10,
            "latitude": [40.75, 40.65, 40.74, 40.85] * 10,
            "value": [1.0, 2.0, 3.0, 4.0] * 10,
        }
    )
    profile = profile_dataframe(df, table="t", resource_id="nyc:1", title="NYPD")
    relevance = evaluate_fields(profile.columns, portal="nyc_open_data")
    profile.field_relevance = relevance.to_dict()

    plans = plans_for_table(profile)
    group_cats = {p.columns[1] for p in plans if p.kind == "group_comparison"}
    assert "boro_nm" in group_cats
    assert "latitude" not in group_cats


def test_socrata_scalar_fields_prioritize_borough_over_ids():
    columns = [
        {"fieldName": "unique_key", "dataTypeName": "text"},
        {"fieldName": "boro_nm", "dataTypeName": "text"},
        {"fieldName": "ofns_desc", "dataTypeName": "text"},
        {"fieldName": "latitude", "dataTypeName": "number"},
        {"fieldName": "longitude", "dataTypeName": "number"},
        {"fieldName": "cmplnt_num", "dataTypeName": "text"},
    ]
    names = scalar_field_names(columns)
    assert names[0] == "boro_nm"
    assert "latitude" not in names
    assert "longitude" not in names
    assert "unique_key" not in names


def test_build_scalar_soql_still_excludes_point_type():
    columns = [
        {"fieldName": "boro_nm", "dataTypeName": "text"},
        {"fieldName": "lat_lon", "dataTypeName": "point"},
        {"fieldName": "count", "dataTypeName": "number"},
    ]
    soql = build_scalar_soql(columns, limit=100)
    assert soql == "SELECT boro_nm, count LIMIT 100"
