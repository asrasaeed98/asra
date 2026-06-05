"""Group-comparison planning should not duplicate name + code geo columns."""

from __future__ import annotations

from findings_api.analysis.field_relevance import dedupe_geo_columns
from findings_api.analysis.selector import plans_for_table
from findings_api.analysis.types import ColumnProfile, TableProfile


def test_dedupe_prefers_name_over_code():
    assert dedupe_geo_columns(["country", "countryiso3code", "region"]) == ["country", "region"]
    assert dedupe_geo_columns(["Country", "Country code"]) == ["Country"]
    assert dedupe_geo_columns(["state_name", "state_code", "sector"]) == ["state_name", "sector"]


def test_dedupe_keeps_code_when_name_absent():
    assert dedupe_geo_columns(["countryiso3code"]) == ["countryiso3code"]


def _col(name: str, kind: str, nunique: int) -> ColumnProfile:
    return ColumnProfile(name=name, dtype="x", kind=kind, nunique=nunique, null_pct=0.0)


def test_no_group_comparison_on_country_code_when_country_present():
    profile = TableProfile(
        table="t",
        resource_id="r",
        title="ATMs",
        n_rows=300,
        columns=[
            _col("country", "categorical", 200),
            _col("countryiso3code", "categorical", 200),
            _col("atms_per_100k", "numeric", 250),
        ],
    )
    plans = plans_for_table(profile)
    group_cats = {p.columns[1] for p in plans if p.kind == "group_comparison"}
    assert "country" in group_cats
    assert "countryiso3code" not in group_cats


def test_joined_multi_measure_skips_geo_group_comparisons():
    profile = TableProfile(
        table="analysis_joined",
        resource_id="a+b",
        title="GDP + Life expectancy",
        n_rows=17000,
        columns=[
            _col("country", "categorical", 200),
            _col("date", "datetime", 65),
            _col("gdp_per_capita", "numeric", 200),
            _col("life_expectancy", "numeric", 200),
        ],
    )
    plans = plans_for_table(profile, joined=True)
    assert any(p.kind == "correlation" for p in plans)
    group_cats = {p.columns[1] for p in plans if p.kind == "group_comparison"}
    assert "country" not in group_cats
