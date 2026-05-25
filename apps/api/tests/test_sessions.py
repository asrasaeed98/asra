from unittest.mock import AsyncMock, patch

import pytest
SAMPLE_CSV = b"state,value,year\nCA,10.1,2020\nNY,9.2,2020\nTX,8.5,2020\n"


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


def test_session_not_found(client):
    assert client.get("/sessions/nope/status").status_code == 404


def test_compute_analysis_n():
    from findings_api.sampling import compute_analysis_n, sampling_tier

    assert compute_analysis_n(1_000_000) == 50_000
    assert compute_analysis_n(5_000) == 5_000
    assert sampling_tier(50_000) == "full_ok"
    assert sampling_tier(500_000) == "recommend_filter"
