from unittest.mock import AsyncMock, patch

import pandas as pd

from findings_api.analysis.profile import profile_dataframe
from findings_api.analysis.ranker import rank_findings
from findings_api.analysis.types import Finding


def test_rank_findings_caps_and_dedupes():
    findings = [
        Finding("f_9", "spearman_correlation", "a", ["x", "y"], 0.5, 0.01, 100, "spearman", "", "", ["d1"], score=2.0),
        Finding("f_10", "spearman_correlation", "b", ["x", "y"], 0.6, 0.001, 100, "spearman", "", "", ["d1"], score=3.0),
    ]
    ranked = rank_findings(findings)
    assert len(ranked) == 1
    assert ranked[0].id == "f_1"
    assert ranked[0].value == 0.6


def test_select_display_findings_diversifies_types():
    from findings_api.analysis.ranker import select_display_findings

    findings = [
        Finding("x", "spearman_correlation", "a", ["a", "b"], 0.9, 0.001, 100, "m", "", "", [], score=10),
        Finding("x", "spearman_correlation", "b", ["c", "d"], 0.8, 0.001, 100, "m", "", "", [], score=9),
        Finding("x", "spearman_correlation", "c", ["e", "f"], 0.7, 0.001, 100, "m", "", "", [], score=8),
        Finding("x", "group_comparison", "d", ["v", "g"], 1.0, 0.001, 100, "m", "", "", [], score=7),
        Finding("x", "time_trend", "e", ["v", "t"], 0.5, 0.001, 100, "m", "", "", [], score=6),
    ]
    ranked = rank_findings(findings)
    top = select_display_findings(ranked, 3)
    types = {f.type for f in top}
    assert len(top) == 3
    assert len(types) >= 2


def test_profile_dataframe_detects_numeric_and_categorical():
    df = pd.DataFrame(
        {
            "state": ["CA", "NY", "TX", "CA", "NY"] * 4,
            "value": [1.0, 2.0, 3.0, 4.0, 5.0] * 4,
            "year": [2020, 2021, 2022, 2023, 2024] * 4,
        }
    )
    profile = profile_dataframe(df, table="analysis_0", resource_id="t:1", title="Test")
    assert "value" in profile.numeric
    assert "state" in profile.categorical


@patch("findings_api.ingest.pipeline.fetch_resource_bytes", new_callable=AsyncMock)
def test_run_analysis_pipeline(mock_fetch, client, tmp_path, monkeypatch):
    monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path))
    from findings_api.config import settings

    settings.session_data_dir = str(tmp_path)

    rows = ["state,value,year"]
    for i in range(40):
        state = "CA" if i % 2 == 0 else "NY"
        val = 10 + i * 0.5 if state == "CA" else 2 + i * 0.1
        rows.append(f"{state},{val},{2020 + (i % 5)}")
    csv = ("\n".join(rows) + "\n").encode()

    mock_fetch.return_value = (csv, "csv")

    resp = client.post("/sessions", json={"resource_ids": ["test:1"], "ml_enabled": False})
    session_id = resp.json()["id"]

    import time

    for _ in range(80):
        status = client.get(f"/sessions/{session_id}/status").json()
        if status["status"] in ("ready", "failed"):
            break
        time.sleep(0.05)

    run = client.post(f"/sessions/{session_id}/run")
    assert run.status_code == 200

    for _ in range(120):
        status = client.get(f"/sessions/{session_id}/status").json()
        if status["status"] in ("complete", "failed"):
            break
        time.sleep(0.05)

    assert client.get(f"/sessions/{session_id}/status").json()["status"] == "complete"
    results = client.get(f"/sessions/{session_id}/results").json()
    assert "findings" in results
    assert isinstance(results["findings"], list)
