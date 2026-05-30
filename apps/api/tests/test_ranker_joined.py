"""Ranking and display priorities for joined two-dataset sessions."""

from findings_api.analysis.narrative import enrich_finding
from findings_api.analysis.ranker import (
    apply_ranking_context,
    rank_findings,
    select_display_findings,
)
from findings_api.analysis.types import Finding


def _finding(
    ftype: str,
    *,
    score: float,
    columns: list[str] | None = None,
    value: float | None = None,
) -> Finding:
    return Finding(
        id="x",
        type=ftype,
        title=ftype,
        columns=columns or ["a", "b"],
        value=value,
        p_value=0.001,
        n=1000,
        method="test",
        caveat="",
        sql="SELECT 1",
        datasets=["d1"],
        score=score,
    )


def test_joined_boost_puts_correlation_first():
    findings = [
        _finding("group_comparison", score=20.0, columns=["gdp", "country"], value=50000),
        _finding("spearman_correlation", score=17.6, columns=["gdp", "life"], value=0.88),
        _finding("time_trend", score=12.0, columns=["gdp", "date"], value=0.96),
    ]
    apply_ranking_context(findings, joined=True)
    ranked = rank_findings(findings)
    assert ranked[0].type == "spearman_correlation"


def test_joined_display_pins_correlation_and_skips_geo_groups():
    findings = [
        _finding("group_comparison", score=20.0, columns=["gdp", "country"], value=50000),
        _finding("spearman_correlation", score=44.0, columns=["gdp", "life"], value=0.88),
        _finding("time_trend", score=12.0, columns=["gdp", "date"], value=0.96),
        _finding("chi_square", score=8.0, columns=["region", "sector"]),
    ]
    ranked = rank_findings(findings)
    display = select_display_findings(ranked, 3, joined=True)
    assert display[0].type == "spearman_correlation"
    assert not any(f.type == "group_comparison" and f.columns[1] == "country" for f in display)


def test_correlation_headline_includes_r_and_n():
    finding = _finding(
        "spearman_correlation",
        score=1.0,
        columns=["gdp_per_capita", "life_expectancy"],
        value=0.8837,
    )
    finding.details = {
        "direction": "positive",
        "column_labels": {
            "gdp_per_capita": "GDP per capita (current US$)",
            "life_expectancy": "Life expectancy at birth, total (years)",
        },
    }
    finding = enrich_finding(finding)
    assert "Spearman r =" in finding.title
    assert "0.883" in finding.title
    assert "n = 1,000" in finding.title
    assert "Strong positive association" in finding.title
    assert finding.details.get("badge") is None
