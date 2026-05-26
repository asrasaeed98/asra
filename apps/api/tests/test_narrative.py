from findings_api.analysis.labels import column_label
from findings_api.analysis.narrative import enrich_finding, impact_for
from findings_api.analysis.types import Finding


def test_group_headline_and_impact():
    f = Finding(
        id="f_1",
        type="group_comparison",
        title="ApprovedOutright differs across Program",
        columns=["ApprovedOutright", "Program"],
        value=71000.0,
        p_value=1e-50,
        n=970,
        method="kruskal",
        caveat="",
        sql="",
        datasets=["x"],
        details={
            "group_means": {"Research": 120000.0, "Education": 50000.0},
            "highest_group": "Research",
            "lowest_group": "Education",
        },
    )
    enrich_finding(f)
    assert "Approved outright amount" in f.title
    assert "Program" in f.title
    assert "spread" not in f.title.lower()
    assert "p =" not in f.title
    impact = impact_for(f)
    assert impact
    assert "Research" in impact


def test_column_label_neh():
    assert column_label("ApprovedOutright") == "Approved outright amount"
    assert column_label("random_field") == "Random field"
