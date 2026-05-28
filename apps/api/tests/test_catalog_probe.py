"""Tests for catalog URL probing."""

from findings_api.catalog.probe import probe_bytes


def test_probe_csv_ok():
    lines = ["year,rate"] + [f"2020,{i}" for i in range(25)]
    data = "\n".join(lines).encode()
    result = probe_bytes(data, url="https://example.com/rates.csv")
    assert result.ingestible
    assert result.detected_format == "CSV"
    assert result.columns == ["year", "rate"]
    assert result.row_count == 25


def test_probe_rejects_small_csv():
    data = b"year,rate\n2020,5.1\n"
    result = probe_bytes(data, url="https://example.com/rates.csv")
    assert not result.ingestible
    assert "need at least" in result.reason


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
    rows = [{"id": i, "value": i * 10} for i in range(25)]
    data = str(rows).replace("'", '"').encode()
    result = probe_bytes(data, url="https://example.com/data.json")
    assert result.ingestible
    assert result.detected_format == "JSON_RECORDS"
    assert result.row_count == 25


def test_probe_worldbank_envelope():
    rows = [
        {
            "countryiso3code": "USA",
            "indicator": {"id": "X"},
            "country": {"id": "US"},
            "date": str(2000 + i),
            "value": i,
        }
        for i in range(25)
    ]
    payload = [{"page": 1, "total": 25}, rows]
    import json

    data = json.dumps(payload).encode()
    result = probe_bytes(data, url="https://api.worldbank.org/v2/country/all/indicator/X?format=json")
    assert result.ingestible
    assert result.detected_format == "JSON_WORLDBANK"
    assert result.row_count == 25


def test_probe_rejects_sparse_worldbank():
    data = b'[{"page":1,"total":1}, [{"countryiso3code":"USA","indicator":{"id":"X"},"country":{"id":"US"},"date":"2020","value":1}]]'
    result = probe_bytes(data, url="https://api.worldbank.org/v2/country/all/indicator/X?format=json")
    assert not result.ingestible
    assert result.row_count == 1


def test_probe_rejects_generic_csv_headers():
    lines = ["column1,column2,column3"] + [f"{i},1,2" for i in range(25)]
    data = "\n".join(lines).encode()
    result = probe_bytes(data, url="https://example.com/data.csv")
    assert not result.ingestible
    assert "generic" in result.reason.lower() or "meaningful" in result.reason.lower()


def test_probe_rejects_nested_json_without_adapter():
    data = b'[{"meta": {"nested": true}, "value": 1}]'
    result = probe_bytes(data, url="https://example.com/data.json")
    assert not result.ingestible
    assert result.detected_format == "JSON_NESTED"
