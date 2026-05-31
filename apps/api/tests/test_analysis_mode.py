"""Explicit explore vs compare analysis modes."""

from findings_api.analysis.mode import resolve_analysis_mode, table_sets_for_mode
from findings_api.analysis.selector import plans_for_table
from findings_api.analysis.types import ColumnProfile, TableProfile


def test_resolve_analysis_mode():
    assert resolve_analysis_mode(1) == "explore"
    assert resolve_analysis_mode(2) == "compare"
    assert resolve_analysis_mode(3) == "explore"


def test_table_sets_explore_single():
    ctx, test = table_sets_for_mode(
        mode="explore",
        table_names=["left_t"],
        joined_table=None,
        joined_ok=False,
    )
    assert ctx == ["left_t"]
    assert test == ["left_t"]


def test_table_sets_compare_join_ok():
    ctx, test = table_sets_for_mode(
        mode="compare",
        table_names=["left_t", "right_t"],
        joined_table="analysis_joined",
        joined_ok=True,
    )
    assert ctx == ["analysis_joined"]
    assert test == ["analysis_joined"]


def test_table_sets_compare_join_failed_runs_both_tables():
    ctx, test = table_sets_for_mode(
        mode="compare",
        table_names=["left_t", "right_t"],
        joined_table=None,
        joined_ok=False,
    )
    assert ctx == ["left_t", "right_t"]
    assert test == ["left_t", "right_t"]


def _col(name: str, kind: str, nunique: int) -> ColumnProfile:
    return ColumnProfile(name=name, dtype="x", kind=kind, nunique=nunique, null_pct=0.0)


def test_joined_table_skips_geo_groups_with_two_measures():
    profile = TableProfile(
        table="analysis_joined",
        resource_id="a+b",
        title="Joined",
        n_rows=500,
        columns=[
            _col("country", "categorical", 50),
            _col("date", "datetime", 10),
            _col("measure_a", "numeric", 50),
            _col("measure_b", "numeric", 50),
        ],
    )
    explore_plans = plans_for_table(profile, joined=False)
    joined_plans = plans_for_table(profile, joined=True)
    assert any(p.kind == "group_comparison" for p in explore_plans)
    group_cats = {p.columns[1] for p in joined_plans if p.kind == "group_comparison"}
    assert "country" not in group_cats


def test_compare_source_table_gets_full_explore_plans():
    profile = TableProfile(
        table="left_t",
        resource_id="a",
        title="Unemployment",
        n_rows=200,
        columns=[
            _col("country", "categorical", 50),
            _col("date", "datetime", 10),
            _col("value", "numeric", 50),
        ],
    )
    plans = plans_for_table(profile, joined=False)
    assert any(p.kind == "group_comparison" for p in plans)
    assert any(p.kind == "trend" for p in plans)


def test_methods_compare_includes_cross_measure_and_ml():
    from findings_api.analysis.methods import summarize_methods_run

    labels = summarize_methods_run(
        [],
        ml_enabled=True,
        analysis_mode="compare",
        cross_measure_ran=True,
    )
    assert "Harmonized cross-dataset correlation" in labels
    assert "K-means clustering" in labels
