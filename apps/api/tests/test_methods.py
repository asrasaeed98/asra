from findings_api.analysis.methods import summarize_methods_run
from findings_api.analysis.profile import profile_dataframe
import pandas as pd


def test_summarize_methods_includes_stats_and_ml():
    df = pd.DataFrame(
        {
            "country": ["US", "CA", "MX"] * 10,
            "amount": list(range(30)),
            "score": [i * 1.5 for i in range(30)],
            "year": [2020, 2021, 2022] * 10,
        }
    )
    profile = profile_dataframe(df, table="t", resource_id="x", title="Grants")
    methods = summarize_methods_run([profile], ml_enabled=True, joined_ok=False)
    assert "Spearman correlation" in methods
    assert "Group comparison" in methods
    assert "K-means clustering" in methods


def test_summarize_methods_omits_ml_when_disabled():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    profile = profile_dataframe(df, table="t", resource_id="x", title="Small")
    methods = summarize_methods_run([profile], ml_enabled=False, joined_ok=False)
    assert "K-means clustering" not in methods
