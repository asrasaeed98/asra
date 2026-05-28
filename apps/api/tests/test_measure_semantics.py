import duckdb
import pandas as pd

from findings_api.analysis.measure_semantics import (
    format_measure_disclosure,
    infer_measure_label_with_ai,
    resolve_measure_label,
)
from findings_api.analysis.profile import profile_table


def test_resolve_measure_from_constant_indicator_column():
    conn = duckdb.connect()
    df = pd.DataFrame(
        {
            "country": ["USA", "CAN"],
            "indicator": ["Access to clean fuels (% of population)"] * 2,
            "indicator_id": ["EG.CFT.ACCS.ZS"] * 2,
            "date": ["2020", "2021"],
            "value": [50.0, 51.0],
        }
    )
    conn.register("t", df)
    conn.execute("CREATE TABLE wb AS SELECT * FROM t")
    resolved = resolve_measure_label(
        conn,
        "wb",
        "value",
        catalog_title="Catalog title fallback",
        use_ai=False,
    )
    assert resolved["label"] == "Access to clean fuels (% of population)"
    assert resolved["source"] == "indicator_column"
    assert "AI determined" not in (resolved.get("disclosure") or "")


def test_resolve_measure_falls_back_to_catalog_title_without_ai():
    conn = duckdb.connect()
    df = pd.DataFrame({"state": ["CA", "NY"], "value": [1.0, 2.0]})
    conn.register("t", df)
    conn.execute("CREATE TABLE t AS SELECT * FROM t")
    resolved = resolve_measure_label(
        conn,
        "t",
        "value",
        catalog_title="Unemployment rate (%)",
        use_ai=False,
    )
    assert resolved["label"] == "Unemployment rate (%)"
    assert resolved["source"] == "catalog_title"


def test_ai_inference_marks_disclosure(monkeypatch):
    def fake_ai(**kwargs):
        return {"label": "Youth unemployment rate", "unit": "percent"}

    monkeypatch.setattr(
        "findings_api.analysis.measure_semantics.infer_measure_label_with_ai",
        fake_ai,
    )
    conn = duckdb.connect()
    df = pd.DataFrame({"state": ["CA", "NY"], "year": [2020, 2021], "value": [5.1, 5.3]})
    conn.register("t", df)
    conn.execute("CREATE TABLE t AS SELECT * FROM t")
    resolved = resolve_measure_label(
        conn,
        "t",
        "value",
        catalog_title="Labor force survey extract",
        use_ai=True,
    )
    assert resolved["source"] == "ai_inferred"
    assert resolved["label"] == "Youth unemployment rate"
    disclosure = format_measure_disclosure(resolved)
    assert "`value`" in disclosure
    assert "AI determined" in disclosure


def test_profile_table_attaches_measure_context():
    conn = duckdb.connect()
    df = pd.DataFrame(
        {
            "country": ["USA"] * 3,
            "indicator": ["GDP growth (annual %)"] * 3,
            "date": ["2018", "2019", "2020"],
            "value": [2.0, 2.5, 3.0],
        }
    )
    conn.register("t", df)
    conn.execute("CREATE TABLE wb AS SELECT * FROM t")
    profile = profile_table(conn, "wb", resource_id="wb:1", title="Catalog GDP")
    assert "value" in profile.measure_contexts
    assert profile.measure_contexts["value"]["label"] == "GDP growth (annual %)"
    assert profile.measure_context("value")["source"] == "indicator_column"


def test_parse_ai_measure_response():
    from findings_api.analysis.measure_semantics import _parse_ai_measure_response

    parsed = _parse_ai_measure_response('{"label": "GDP per capita", "unit": "USD"}')
    assert parsed == {"label": "GDP per capita", "unit": "USD"}


def test_infer_measure_label_with_ai_no_key(monkeypatch):
    monkeypatch.setattr(
        "findings_api.analysis.measure_semantics.settings.anthropic_api_key",
        "",
    )
    assert infer_measure_label_with_ai(
        column="value",
        catalog_title="Test",
        column_names=["value"],
        sample_rows=[{"value": 1}],
        metadata_hints={},
    ) is None
