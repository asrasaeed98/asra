"""Tests for catalog theme classification."""

from findings_api.catalog.topic_classifier import (
    classify_resource,
    filter_by_topic,
    primary_theme,
    resource_matches_topic,
)
from findings_api.models import CatalogResource


def _row(**kwargs) -> CatalogResource:
    defaults = dict(
        id="wb:TEST",
        portal="world_bank",
        title="Test indicator",
        description=None,
        organization="World Bank",
        tags=[],
        format="JSON_WORLDBANK",
        license_normalized="CC_BY",
        license_raw=None,
        license_display="CC BY",
        attribution_required=True,
        attribution_text="WB",
        publisher="World Bank",
        source_url="https://example.com",
        resource_url="https://example.com/data",
        search_text="test indicator",
        ingestible=True,
    )
    defaults.update(kwargs)
    return CatalogResource(**defaults)


def test_classify_worldbank_health_by_tag():
    row = _row(
        id="wb:SP.DYN.LE00.IN",
        title="Life expectancy at birth, total (years)",
        tags=["Health"],
        search_text="life expectancy at birth health mortality",
    )
    themes = classify_resource(row)
    assert themes[0] == "health"
    assert resource_matches_topic(row, "health")
    assert not resource_matches_topic(row, "economy")


def test_classify_worldbank_economy_by_tag():
    row = _row(
        id="wb:NY.GDP.PCAP.CD",
        title="GDP per capita (current US$)",
        tags=["Economy & Growth"],
        search_text="gdp per capita economy growth income",
    )
    assert primary_theme(row) == "economy"


def test_classify_fred_unemployment_by_title():
    row = _row(
        id="fred:UNRATE",
        portal="fred",
        title="Unemployment Rate",
        tags=["Monthly", "Percent"],
        search_text="unemployment rate labor fred",
        format="JSON",
    )
    themes = classify_resource(row)
    assert "economy" in themes
    assert resource_matches_topic(row, "economy")


def test_classify_datagov_education_by_keyword():
    row = _row(
        id="datagov:schools",
        portal="data_gov",
        title="Public school enrollment by district",
        tags=["education", "schools"],
        search_text="public school enrollment district education",
        format="CSV",
    )
    assert "education" in classify_resource(row)
    assert resource_matches_topic(row, "education")


def test_classify_environment_energy():
    row = _row(
        id="wb:EG.ELC.ACCS.ZS",
        title="Access to electricity (% of population)",
        tags=["Environment"],
        search_text="access to electricity energy population",
        description="Electricity access indicator",
    )
    themes = classify_resource(row)
    assert "environment" in themes


def test_filter_by_topic():
    health = _row(id="wb:H", tags=["Health"], title="Infant mortality rate")
    economy = _row(id="wb:E", tags=["Economy & Growth"], title="GDP growth")
    other = _row(id="wb:X", tags=[], title="Miscellaneous administrative code", search_text="misc")
    filtered = filter_by_topic([health, economy, other], "health")
    assert [r.id for r in filtered] == ["wb:H"]


def test_count_primary_themes():
    from findings_api.catalog.topic_classifier import count_primary_themes

    health = _row(id="wb:H", tags=["Health"], title="Infant mortality rate")
    economy = _row(id="wb:E", tags=["Economy & Growth"], title="GDP growth")
    counts = count_primary_themes([health, economy])
    assert counts["health"] == 1
    assert counts["economy"] == 1
