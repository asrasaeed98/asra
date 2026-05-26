from findings_api.analysis.descriptive import analysis_notes, descriptive_findings
from findings_api.analysis.profile import profile_dataframe
from findings_api.analysis.types import Finding
import pandas as pd


def test_descriptive_findings_for_numeric_csv():
    df = pd.DataFrame({"state": ["CA", "NY", "TX"] * 10, "amount": list(range(30))})
    profile = profile_dataframe(df, table="t", resource_id="x", title="Grants")

    class Conn:
        def execute(self, sql):
            return self

        def fetchdf(self):
            return df

    findings = descriptive_findings(profile, Conn())
    assert findings
    assert any(f.type == "descriptive" for f in findings)


def test_analysis_notes_when_no_stats():
    df = pd.DataFrame({"value": [1, 2, None], "date": [2020, 2021, 2022]})
    profile = profile_dataframe(df, table="t", resource_id="wb", title="Indicator")
    notes = analysis_notes([profile], tests_planned=6, statistical=0)
    assert notes
    assert any("significance" in n.lower() or "numeric" in n.lower() for n in notes)
