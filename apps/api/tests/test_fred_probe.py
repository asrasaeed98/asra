"""Tests for FRED catalog probing."""

import json

from findings_api.catalog.probe import probe_bytes


def test_probe_fred_ok():
    payload = {
        "count": 320,
        "observations": [{"date": f"2020-{i:02d}-01", "value": str(i)} for i in range(1, 26)],
    }
    data = json.dumps(payload).encode()
    result = probe_bytes(data, url="https://api.stlouisfed.org/fred/series/observations", portal="fred")
    assert result.ingestible
    assert result.detected_format == "JSON_FRED"
    assert result.row_count == 320


def test_probe_fred_rejects_sparse():
    payload = {"count": 5, "observations": [{"date": "2020-01-01", "value": "1"}]}
    data = json.dumps(payload).encode()
    result = probe_bytes(data, portal="fred")
    assert not result.ingestible
    assert result.row_count == 5
