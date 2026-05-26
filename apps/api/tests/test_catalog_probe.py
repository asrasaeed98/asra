"""Tests for catalog URL probing."""

from findings_api.catalog.probe import probe_bytes


def test_probe_csv_ok():
    data = b"year,rate\n2020,5.1\n2021,4.2\n"
    result = probe_bytes(data, url="https://example.com/rates.csv")
    assert result.ingestible
    assert result.detected_format == "CSV"
    assert result.columns == ["year", "rate"]


def test_probe_rejects_html():
    data = b"<!DOCTYPE html><html><body>Download</body></html>"
    result = probe_bytes(data, url="https://example.com/page")
    assert not result.ingestible
    assert result.detected_format == "HTML"


def test_probe_rejects_zip():
    data = b"PK\x03\x04" + b"\x00" * 100
    result = probe_bytes(data, url="https://example.com/data.zip")
    assert not result.ingestible
    assert result.detected_format == "ZIP"


def test_probe_flat_json():
    data = b'[{"id": 1, "value": 10}, {"id": 2, "value": 20}]'
    result = probe_bytes(data, url="https://example.com/data.json")
    assert result.ingestible
    assert result.detected_format == "JSON_RECORDS"


def test_probe_worldbank_envelope():
    data = b'[{"page":1}, [{"countryiso3code":"USA","indicator":{"id":"X"},"country":{"id":"US"},"date":"2020","value":1}]]'
    result = probe_bytes(data, url="https://api.worldbank.org/v2/country/all/indicator/X?format=json")
    assert result.ingestible
    assert result.detected_format == "JSON_WORLDBANK"


def test_probe_rejects_nested_json_without_adapter():
    data = b'[{"meta": {"nested": true}, "value": 1}]'
    result = probe_bytes(data, url="https://example.com/data.json")
    assert not result.ingestible
    assert result.detected_format == "JSON_NESTED"
