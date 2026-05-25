from fastapi.testclient import TestClient

from findings_api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "findings-api"
    assert "catalog_count" in data
    assert data["catalog_count"] >= 0
