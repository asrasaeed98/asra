"""Tests for column name quality heuristics."""

from findings_api.catalog.column_quality import is_generic_column, score_columns


def test_generic_column_patterns():
    assert is_generic_column("column1")
    assert is_generic_column("column08")
    assert is_generic_column("Column_12")
    assert is_generic_column("Unnamed: 0")
    assert is_generic_column("field3")
    assert not is_generic_column("ApprovedOutright")
    assert not is_generic_column("unemployment_rate")
    assert not is_generic_column("value")
    assert not is_generic_column("date")


def test_score_columns_rejects_mostly_generic():
    ok, reason, stats = score_columns(["column1", "column2", "column3", "state"])
    assert not ok
    assert "generic" in reason.lower()
    assert stats["meaningful"] == 1


def test_score_columns_accepts_descriptive_headers():
    ok, reason, stats = score_columns(["year", "state", "unemployment_rate", "population"])
    assert ok
    assert reason == "ok"
    assert stats["meaningful"] == 4
