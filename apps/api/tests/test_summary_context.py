"""Tests for summary context assembly."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from findings_api.analysis.summary_context import build_summary_context
from findings_api.analysis.types import ChartSpec, Finding, TableProfile
from findings_api.db import Base
from findings_api.models import CatalogResource


def test_build_summary_context_includes_sources_and_join():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    db.add(
        CatalogResource(
            id="wb:test",
            portal="world_bank",
            title="Life expectancy",
            license_normalized="CC_BY",
            license_display="CC BY 4.0",
            attribution_required=True,
            attribution_text="World Bank test",
            publisher="World Bank",
            source_url="https://example.com/wb",
            search_text="life expectancy",
        )
    )
    db.commit()

    profile = TableProfile(
        table="analysis_0",
        resource_id="wb:test",
        title="Life expectancy",
        n_rows=100,
        facts={"n_rows": 100},
    )
    finding = Finding(
        id="f_1",
        type="spearman_correlation",
        title="Test",
        columns=["value", "value_1"],
        value=0.5,
        p_value=0.01,
        n=100,
        method="spearman",
        caveat="test",
        sql="SELECT 1",
        datasets=["wb:test"],
        details={"headline": "Test headline", "impact": "Values move together."},
    )

    class FakeConn:
        pass

    context = build_summary_context(
        db,
        FakeConn(),
        profiles=[profile],
        all_findings=[finding],
        display_finding_ids=["f_1"],
        user_intent="Does education relate to income?",
        join_report={
            "join_on": [{"left": "country_code", "right": "country_code"}],
            "matched_rows": 95,
            "auto": True,
        },
        methods_run=["Spearman correlation", "Group comparison"],
        analysis_overview={"tests_planned": 12, "statistical_findings": 1},
        column_glossary=[{"name": "value", "label": "Education rate"}],
        charts=[
            ChartSpec(
                id="c1",
                finding_id="f_1",
                type="scatter",
                title="Education vs income",
                spec={},
            )
        ],
    )

    assert context["user_intent"] == "Does education relate to income?"
    assert context["datasets"][0]["source"]["publisher"] == "World Bank"
    assert context["join"]["succeeded"] is True
    assert context["methods_run"] == ["Spearman correlation", "Group comparison"]
    assert context["all_findings"][0]["details"]["chart_title"] == "Education vs income"
    db.close()
