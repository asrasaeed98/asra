from findings_api.db import Base, get_engine


def test_record_visit(client):
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    res = client.post(
        "/metrics/visit",
        json={
            "visitor_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "path": "/search",
        },
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_record_visit_rejects_bad_uuid(client):
    res = client.post(
        "/metrics/visit",
        json={
            "visitor_id": "00000000-0000-6000-8000-000000000000",
            "path": "/",
        },
    )
    assert res.status_code == 400
