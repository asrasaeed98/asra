"""Chat assistant behavior constraints."""

from findings_api.analysis.chat import SYSTEM_PROMPT, _looks_like_query_promise


def test_system_prompt_forbids_follow_ups_and_out_of_scope_offers():
    low = SYSTEM_PROMPT.lower()
    assert "do not ask follow-up" in low
    assert "do not offer to help" in low
    assert "markdown tables" in low
    assert "let me query" in low


def test_looks_like_query_promise():
    assert _looks_like_query_promise("Let me query the data for that recent period!", query_used=False)
    assert not _looks_like_query_promise("Bermuda leads GDP.", query_used=False)
    assert not _looks_like_query_promise("Let me query", query_used=True)
