"""Tests for shared catalog theme config (topics.yaml)."""

from findings_api.catalog.topic_config import (
    all_topic_ids,
    load_topics,
    topic_by_id,
    wb_tag_to_topic_id,
)
from findings_api.guided.loader import load_guided_config, load_paths


def test_load_topics_has_five_themes():
    topics = load_topics()
    assert len(topics) == 5
    assert all_topic_ids() == {"economy", "health", "environment", "education", "poverty"}


def test_topic_has_classification_rules():
    health = topic_by_id("health")
    assert health is not None
    assert "Health" in health.wb_tags
    assert "life expectancy" in health.keywords


def test_wb_tag_maps_to_theme():
    assert wb_tag_to_topic_id("Economy & Growth") == "economy"
    assert wb_tag_to_topic_id("health") == "health"
    assert wb_tag_to_topic_id("Unknown Topic") is None


def test_paths_reference_valid_topics():
    topics, paths = load_guided_config()
    valid = {t.id for t in topics}
    for path in paths:
        assert path.topic in valid, f"path {path.id} has unknown topic {path.topic}"


def test_paths_yaml_no_embedded_topics():
    paths = load_paths()
    assert len(paths) >= 8
