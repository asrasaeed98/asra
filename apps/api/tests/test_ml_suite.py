"""Tests for ML suite inclusion in ranked results."""

import duckdb
import numpy as np
import pandas as pd

from findings_api.analysis.ml.clustering import run_ml_suite
from findings_api.analysis.profile import profile_dataframe
from findings_api.analysis.ranker import rank_findings, select_display_findings
from findings_api.analysis.types import Finding, TableProfile


def _profile_from_df(df: pd.DataFrame) -> TableProfile:
    return profile_dataframe(df, table="t", resource_id="ds:1", title="Synthetic")


def test_ml_suite_runs_multiple_models():
    rng = np.random.default_rng(42)
    n = 300
    cluster = rng.choice([0, 1, 2], size=n)
    x = rng.normal(cluster * 3, 1, size=n)
    y = rng.normal(cluster * 2, 1, size=n)
    df = pd.DataFrame({"x": x, "y": y, "z": x + y + rng.normal(0, 0.2, size=n)})
    conn = duckdb.connect()
    conn.register("tmp", df)
    conn.execute("CREATE TABLE t AS SELECT * FROM tmp")
    profile = _profile_from_df(df)
    profile.table = "t"
    profile.n_rows = len(df)

    findings = run_ml_suite(conn, profile)
    types = {f.type for f in findings}
    assert "kmeans_cluster" in types or "dbscan_cluster" in types
    assert "pca_structure" in types


def test_ml_findings_can_rank_in_display():
    findings = [
        Finding(
            "a",
            "group_comparison",
            "g",
            ["v", "c"],
            1.0,
            0.001,
            100,
            "welch_t",
            "",
            "",
            ["d"],
            score=5.0,
        ),
        Finding(
            "b",
            "kmeans_cluster",
            "ml",
            ["x", "y"],
            0.45,
            None,
            300,
            "kmeans",
            "",
            "",
            ["d"],
            score=4.5,
        ),
        Finding(
            "c",
            "spearman_correlation",
            "c",
            ["a", "b"],
            0.4,
            0.02,
            100,
            "spearman",
            "",
            "",
            ["d"],
            score=1.0,
        ),
    ]
    ranked = rank_findings(findings, limit=10)
    display = select_display_findings(ranked, 3)
    types = {f.type for f in display}
    assert "kmeans_cluster" in types
