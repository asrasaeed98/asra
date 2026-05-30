"""API tests for guided explore endpoints."""

from findings_api.models import CatalogResource


def test_guided_topics(client):
    resp = client.get("/guided/topics")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 4
    assert any(t["id"] == "health" for t in data)


def test_guided_paths_lists_curated(client, monkeypatch):
    from findings_api.db import get_session_factory

    factory = get_session_factory()
    s = factory()
    s.add(
        CatalogResource(
            id="wb:NY.GDP.PCAP.CD",
            portal="world_bank",
            title="GDP per capita (current US$)",
            description="GDP",
            organization="WB",
            tags=["Economy"],
            format="JSON_WORLDBANK",
            license_normalized="CC_BY",
            license_raw="CC-BY",
            license_display="CC BY",
            attribution_required=True,
            attribution_text="WB",
            publisher="WB",
            source_url="https://data.worldbank.org/indicator/NY.GDP.PCAP.CD",
            resource_url="https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.CD?format=json",
            search_text="gdp per capita",
            ingestible=True,
            row_count_hint=20000,
        )
    )
    s.add(
        CatalogResource(
            id="wb:SP.DYN.LE00.IN",
            portal="world_bank",
            title="Life expectancy at birth, total (years)",
            description="Life expectancy",
            organization="WB",
            tags=["Health"],
            format="JSON_WORLDBANK",
            license_normalized="CC_BY",
            license_raw="CC-BY",
            license_display="CC BY",
            attribution_required=True,
            attribution_text="WB",
            publisher="WB",
            source_url="https://data.worldbank.org/indicator/SP.DYN.LE00.IN",
            resource_url="https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.IN?format=json",
            search_text="life expectancy",
            ingestible=True,
            row_count_hint=20000,
        )
    )
    s.commit()
    s.close()

    resp = client.get("/guided/paths")
    assert resp.status_code == 200
    paths = resp.json()
    wealth = next((p for p in paths if p["path_id"] == "wealth-health"), None)
    assert wealth is not None
    assert len(wealth["resource_ids"]) == 2


def test_guided_suggest_question(client):
    from findings_api.db import get_session_factory

    factory = get_session_factory()
    s = factory()
    for rid, title, text in (
        ("wb:NY.GDP.PCAP.CD", "GDP per capita (current US$)", "gdp per capita"),
        ("wb:SP.DYN.LE00.IN", "Life expectancy at birth, total (years)", "life expectancy"),
    ):
        s.merge(
            CatalogResource(
                id=rid,
                portal="world_bank",
                title=title,
                description=title,
                organization="WB",
                tags=[],
                format="JSON_WORLDBANK",
                license_normalized="CC_BY",
                license_raw="CC-BY",
                license_display="CC BY",
                attribution_required=True,
                attribution_text="WB",
                publisher="WB",
                source_url=f"https://data.worldbank.org/indicator/{rid.split(':')[1]}",
                resource_url="https://api.worldbank.org/v2/country/all/indicator/x?format=json",
                search_text=text,
                ingestible=True,
                row_count_hint=20000,
            )
        )
    s.commit()
    s.close()

    resp = client.get("/guided/suggest?q=life+expectancy+and+gdp")
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommended_pairs"]
    assert data["recommended_pairs"][0]["path_id"] == "wealth-health"


def test_search_returns_quality_scores(client):
    resp = client.get("/search?q=unemployment")
    assert resp.status_code == 200
    data = resp.json()
    if data["results"]:
        assert data["results"][0].get("quality_score") is not None


def test_search_topic_filter(client):
    from findings_api.db import get_session_factory

    factory = get_session_factory()
    s = factory()
    s.add(
        CatalogResource(
            id="wb:SP.DYN.LE00.IN",
            portal="world_bank",
            title="Life expectancy at birth, total (years)",
            description="Health indicator",
            organization="WB",
            tags=["Health"],
            format="JSON_WORLDBANK",
            license_normalized="CC_BY",
            license_raw="CC-BY",
            license_display="CC BY",
            attribution_required=True,
            attribution_text="WB",
            publisher="WB",
            source_url="https://data.worldbank.org/indicator/SP.DYN.LE00.IN",
            resource_url="https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.IN?format=json",
            search_text="life expectancy health mortality",
            ingestible=True,
            row_count_hint=20000,
        )
    )
    s.add(
        CatalogResource(
            id="wb:NY.GDP.PCAP.CD",
            portal="world_bank",
            title="GDP per capita (current US$)",
            description="Economy indicator",
            organization="WB",
            tags=["Economy & Growth"],
            format="JSON_WORLDBANK",
            license_normalized="CC_BY",
            license_raw="CC-BY",
            license_display="CC BY",
            attribution_required=True,
            attribution_text="WB",
            publisher="WB",
            source_url="https://data.worldbank.org/indicator/NY.GDP.PCAP.CD",
            resource_url="https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.CD?format=json",
            search_text="gdp per capita economy",
            ingestible=True,
            row_count_hint=20000,
        )
    )
    s.commit()
    s.close()

    resp = client.get("/search?topic=health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["topic"] == "health"
    assert data["total"] >= 1
    ids = {r["id"] for r in data["results"]}
    assert "wb:SP.DYN.LE00.IN" in ids
    assert "wb:NY.GDP.PCAP.CD" not in ids


def test_search_unknown_topic_returns_400(client):
    resp = client.get("/search?topic=not-a-theme")
    assert resp.status_code == 400


def test_search_topics_returns_counts(client):
    from findings_api.db import get_session_factory

    factory = get_session_factory()
    s = factory()
    s.add(
        CatalogResource(
            id="wb:SP.DYN.LE00.IN",
            portal="world_bank",
            title="Life expectancy at birth, total (years)",
            description="Health indicator",
            organization="WB",
            tags=["Health"],
            format="JSON_WORLDBANK",
            license_normalized="CC_BY",
            license_raw="CC-BY",
            license_display="CC BY",
            attribution_required=True,
            attribution_text="WB",
            publisher="WB",
            source_url="https://example.com/le",
            resource_url="https://example.com/le.json",
            search_text="life expectancy health",
            ingestible=True,
        )
    )
    s.add(
        CatalogResource(
            id="wb:NY.GDP.PCAP.CD",
            portal="world_bank",
            title="GDP per capita (current US$)",
            description="Economy indicator",
            organization="WB",
            tags=["Economy & Growth"],
            format="JSON_WORLDBANK",
            license_normalized="CC_BY",
            license_raw="CC-BY",
            license_display="CC BY",
            attribution_required=True,
            attribution_text="WB",
            publisher="WB",
            source_url="https://example.com/gdp",
            resource_url="https://example.com/gdp.json",
            search_text="gdp per capita economy",
            ingestible=True,
        )
    )
    s.commit()
    s.close()

    resp = client.get("/search/topics")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5
    health = next(t for t in data if t["id"] == "health")
    economy = next(t for t in data if t["id"] == "economy")
    assert health["dataset_count"] >= 1
    assert economy["dataset_count"] >= 1
