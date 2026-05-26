from findings_api.analysis.ai_summary import (
    _parse_summary_json,
    generate_ai_summary,
    sanitize_summary_text,
    template_summary,
    template_summary_blocks,
    validate_summary_numbers,
)


def test_validate_rejects_hallucinated_number():
    findings = [
        {
            "title": "A differs across B",
            "n": 100,
            "value": 0.5,
            "p_value": 0.01,
            "details": {"impact": "Average is higher for X ($50,000) than Y ($30,000)."},
        }
    ]
    assert validate_summary_numbers(
        "Grants average $50,000 in group X and $30,000 in group Y across 100 rows.",
        findings,
    )
    assert not validate_summary_numbers(
        "Grants average $999,999 in group X.",
        findings,
    )


def test_template_summary_from_impacts():
    text = template_summary(
        [
            {
                "title": "Headline",
                "details": {"impact": "Amounts differ by program area."},
            }
        ],
        dataset_titles=["NEH Grants"],
    )
    assert "NEH Grants" in text
    assert "Amounts differ" in text


def test_template_summary_blocks_structure():
    blocks = template_summary_blocks(
        [{"title": "Headline", "details": {"impact": "Amounts differ by program area."}}],
        dataset_titles=["NEH Grants"],
    )
    assert blocks[0]["type"] == "paragraph"
    assert any(b.get("type") == "list" for b in blocks)


def test_parse_summary_json():
    raw = """{
      "intro": "NEH grants show clear regional patterns.",
      "highlights": [
        "Midwest awards are higher on average.",
        "Humanities programs dominate funding."
      ],
      "caveat": "These patterns do not prove causation."
    }"""
    blocks = _parse_summary_json(raw)
    assert blocks is not None
    assert blocks[0]["type"] == "paragraph"
    assert blocks[1]["type"] == "list"
    assert len(blocks[1]["items"]) == 2


def test_sanitize_summary_strips_markdown_title():
    raw = "# Executive Summary: NEH Grant Patterns (1990–1999)\n\nFirst paragraph here."
    assert sanitize_summary_text(raw) == "First paragraph here."


def test_generate_without_api_key_uses_template(monkeypatch):
    monkeypatch.setattr("findings_api.analysis.ai_summary.settings.anthropic_api_key", "")
    summary, source, blocks = generate_ai_summary(
        [{"title": "Test", "details": {"impact": "Something happened."}, "n": 10}],
        dataset_titles=["Dataset A"],
    )
    assert source == "template"
    assert "Something happened" in summary
    assert any(b.get("type") == "list" for b in blocks)
