from fastapi.testclient import TestClient

from findings_api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "findings-api"


def test_search_stub():
    r = client.get("/search?q=unemployment")
    assert r.status_code == 200
    assert "results" in r.json()
