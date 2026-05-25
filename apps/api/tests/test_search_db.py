def test_search_finds_record(client):
    r = client.get("/search?q=unemployment")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    hit = data["results"][0]
    assert hit["source_url"]
    assert hit["publisher"]
    assert "attribution_text" in hit
