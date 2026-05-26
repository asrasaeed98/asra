from unittest.mock import AsyncMock, patch

import pytest
SAMPLE_CSV = b"state,value,year\nCA,10.1,2020\nNY,9.2,2020\nTX,8.5,2020\n"


@patch("findings_api.ingest.pipeline.fetch_resource_bytes", new_callable=AsyncMock)
def test_ingest_two_world_bank_datasets(mock_fetch, client, tmp_path, monkeypatch):
    monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path))
    from findings_api.config import settings

    settings.session_data_dir = str(tmp_path)

    wb_json = b'[{"page":1,"pages":1,"per_page":500,"total":2},[{"indicator":{"id":"1","value":"Test"},"country":{"id":"US","value":"United States"},"countryiso3code":"USA","date":"2020","value":42.0,"unit":"","obs_status":"","decimal":1}]]'

    mock_fetch.return_value = (wb_json, "json")

    # Add second catalog entry
    from findings_api.db import get_session_factory
    from findings_api.models import CatalogResource

    factory = get_session_factory()
    s = factory()
    s.add(
        CatalogResource(
            id="test:2",
            portal="world_bank",
            title="Second indicator",
            description=None,
            organization="WB",
            tags=[],
            format="API",
            license_normalized="CC_BY",
            license_raw="CC-BY",
            license_display="CC BY",
            attribution_required=True,
            attribution_text="attr",
            publisher="WB",
            source_url="https://wb/2",
            resource_url="https://api.worldbank.org/v2/country/all/indicator/2?format=json",
            search_text="test two",
        )
    )
    s.commit()
    s.close()

    resp = client.post("/sessions", json={"resource_ids": ["test:1", "test:2"]})
    assert resp.status_code == 200
    session_id = resp.json()["id"]

    import time

    for _ in range(80):
        status = client.get(f"/sessions/{session_id}/status").json()
        if status["status"] in ("ready", "failed"):
            break
        time.sleep(0.05)

    detail = client.get(f"/sessions/{session_id}").json()
    assert detail["status"] == "ready", detail.get("error") or detail.get("message")
    assert len(detail["preview"]["datasets"]) == 2

    run = client.post(f"/sessions/{session_id}/run")
    assert run.status_code == 200

    for _ in range(120):
        status = client.get(f"/sessions/{session_id}/status").json()
        if status["status"] in ("complete", "failed"):
            break
        time.sleep(0.05)

    assert client.get(f"/sessions/{session_id}/status").json()["status"] == "complete"


@patch("findings_api.ingest.pipeline.fetch_resource_bytes", new_callable=AsyncMock)
def test_create_session_and_ingest(mock_fetch, client, tmp_path, monkeypatch):
    monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path))
    from findings_api.config import settings

    settings.session_data_dir = str(tmp_path)
    mock_fetch.return_value = (SAMPLE_CSV, "csv")

    resp = client.post(
        "/sessions",
        json={"resource_ids": ["test:1"], "user_intent": "unemployment trends", "ml_enabled": True},
    )
    assert resp.status_code == 200
    session_id = resp.json()["id"]

    import time

    for _ in range(50):
        status = client.get(f"/sessions/{session_id}/status").json()
        if status["status"] in ("ready", "failed"):
            break
        time.sleep(0.1)

    detail = client.get(f"/sessions/{session_id}").json()
    assert detail["status"] == "ready"
    assert detail["preview"]["datasets"][0]["row_count"] == 3

    patch_resp = client.patch(
        f"/sessions/{session_id}",
        json={"filters": {"0": "state = 'CA'"}, "ml_enabled": False},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["config"]["filters"]["0"] == "state = 'CA'"

    run = client.post(f"/sessions/{session_id}/run")
    assert run.status_code == 200
    assert run.json()["phase"] == "prepare"

    for _ in range(120):
        status = client.get(f"/sessions/{session_id}/status").json()
        if status["status"] in ("complete", "failed"):
            break
        time.sleep(0.05)

    assert client.get(f"/sessions/{session_id}/status").json()["status"] == "complete"


def test_session_not_found(client):
    assert client.get("/sessions/nope/status").status_code == 404


def test_compute_analysis_n():
    from findings_api.sampling import compute_analysis_n, sampling_tier

    assert compute_analysis_n(1_000_000) == 50_000
    assert compute_analysis_n(5_000) == 5_000
    assert sampling_tier(50_000) == "full_ok"
    assert sampling_tier(500_000) == "recommend_filter"
