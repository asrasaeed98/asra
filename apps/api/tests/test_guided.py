"""Tests for curated guided paths and search quality ranking."""

from findings_api.catalog.search_rank import catalog_quality_score, rank_catalog_rows
from findings_api.guided.loader import load_guided_config, match_paths, path_by_id
from findings_api.models import CatalogResource


def _row(**kwargs) -> CatalogResource:
    defaults = dict(
        id="wb:TEST",
        portal="world_bank",
        title="Test indicator",
        description=None,
        organization="WB",
        tags=[],
        format="JSON_WORLDBANK",
        license_normalized="CC_BY",
        license_raw=None,
        license_display="CC BY",
        attribution_required=True,
        attribution_text="WB",
        publisher="WB",
        source_url="https://example.com",
        resource_url="https://example.com/data",
        search_text="gdp per capita income growth",
        ingestible=True,
        row_count_hint=15000,
    )
    defaults.update(kwargs)
    return CatalogResource(**defaults)


def test_load_guided_paths():
    topics, paths = load_guided_config()
    assert len(topics) >= 4
    assert len(paths) >= 8
    wealth = path_by_id("wealth-health")
    assert wealth is not None
    assert len(wealth.resource_ids) == 2


def test_match_paths_life_expectancy():
    matched = match_paths("does wealth relate to life expectancy")
    assert matched
    assert matched[0][0].id == "wealth-health"


def test_search_ranks_featured_higher_with_same_match():
    featured = _row(id="wb:NY.GDP.PCAP.CD", title="GDP per capita (current US$)")
    other = _row(id="wb:OTHER.X", title="Other GDP metric", row_count_hint=50)
    ranked = rank_catalog_rows([other, featured], "gdp")
    assert ranked[0][0].id == "wb:NY.GDP.PCAP.CD"


def test_search_empty_query_sorts_by_quality():
    low = _row(id="wb:LOW", row_count_hint=10, search_text="obscure")
    high = _row(id="wb:NY.GDP.PCAP.CD", row_count_hint=20000)
    ranked = rank_catalog_rows([low, high], "")
    assert ranked[0][0].row_count_hint >= ranked[1][0].row_count_hint or ranked[0][0].id == "wb:NY.GDP.PCAP.CD"
