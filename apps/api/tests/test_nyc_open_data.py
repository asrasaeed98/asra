"""Tests for NYC Open Data / Socrata helpers."""

import pytest

from findings_api.catalog.quality import apply_probe
from findings_api.catalog.probe import ProbeResult
from findings_api.catalog.socrata import (
    CATALOG_RESOURCE_URL_MAX_LEN,
    analysis_row_cap,
    build_catalog_resource_url,
    build_scalar_soql,
    parse_query_url,
    query_url,
)
from findings_api.config import settings
from findings_api.licensing import is_allowed
from findings_api.models import CatalogResource


@pytest.fixture(autouse=True)
def _fast_probe(monkeypatch):
    monkeypatch.setattr(settings, "catalog_min_rows", 5)


def test_nyc_license_allowed():
    assert is_allowed("US_GOV_WORK", "nyc_open_data") is True


def test_build_scalar_soql_excludes_geo():
    columns = [
        {"fieldName": "boro_nm", "dataTypeName": "text"},
        {"fieldName": "lat_lon", "dataTypeName": "point"},
        {"fieldName": "count", "dataTypeName": "number"},
    ]
    soql = build_scalar_soql(columns, limit=100)
    assert soql == "SELECT boro_nm, count LIMIT 100"


def test_build_catalog_resource_url_fits_varchar():
    columns = [
        {"fieldName": f"very_long_column_name_{i}", "dataTypeName": "text"}
        for i in range(40)
    ]
    url, soql = build_catalog_resource_url("https://data.cityofnewyork.us", "mg8s-7r2b", columns)
    assert len(url) <= CATALOG_RESOURCE_URL_MAX_LEN
    assert soql.startswith("SELECT ")
    assert "LIMIT" in soql


def test_query_url_roundtrip():
    soql = "SELECT boro_nm LIMIT 100"
    url = query_url("https://data.cityofnewyork.us", "5uac-w243", soql)
    base, ds_id, parsed = parse_query_url(url)
    assert base == "https://data.cityofnewyork.us"
    assert ds_id == "5uac-w243"
    assert parsed == soql


def test_analysis_row_cap():
    assert analysis_row_cap(limit=50_000) == 50_000
    assert analysis_row_cap(limit=200_000) == 100_000


def test_apply_probe_preserves_socrata_row_count():
    rec = CatalogResource(
        id="nyc:test",
        portal="nyc_open_data",
        title="Test",
        license_normalized="US_GOV_WORK",
        license_display="test",
        attribution_required=False,
        attribution_text="",
        publisher="NYC",
        source_url="https://example.com",
        search_text="test",
        row_count_hint=1_875_154,
    )
    apply_probe(
        rec,
        ProbeResult(True, "flat JSON records", "JSON_RECORDS", ["a", "b"], row_count=None),
    )
    assert rec.row_count_hint == 1_875_154
    assert rec.ingestible is True
