"""Joined datasets resolve distinct, accurate measure labels (not value/value_1)."""

import duckdb

from findings_api.analysis.join import build_joined_table_on
from findings_api.analysis.measure_semantics import (
    format_measure_disclosure,
    measure_slug,
    resolve_measure_label,
)
from findings_api.analysis.narrative import enrich_finding
from findings_api.analysis.profile import profile_table
from findings_api.analysis.tests.correlation import run_correlation
from findings_api.analysis.tests.group_comparison import run_group_comparison

SLUMS = "Population living in slums (% of urban population)"
SOCIAL = "Adequacy of social protection and labor programs (% of total welfare)"


def _wb_panel(conn, table: str, indicator: str, value_expr):
    rows = []
    for i in range(20):
        rows.append((f"C{i:02d}", "2020", indicator, float(value_expr(i))))
    conn.execute(
        f"CREATE TABLE {table} (country VARCHAR, date VARCHAR, indicator VARCHAR, value DOUBLE)"
    )
    conn.executemany(f"INSERT INTO {table} VALUES (?, ?, ?, ?)", rows)


def _build_joined(conn):
    _wb_panel(conn, "left_t", SLUMS, lambda i: i)
    _wb_panel(conn, "right_t", SOCIAL, lambda i: 100 - i)  # strong negative corr

    used: set[str] = set()
    renames = {}
    injected = {}
    for tbl, side in (("left_t", "left"), ("right_t", "right")):
        ctx = resolve_measure_label(conn, tbl, "value", catalog_title="", use_ai=False)
        slug = measure_slug(str(ctx["label"]), fallback=f"{side}_value", used=used)
        renames[tbl] = ("value", slug)
        nctx = dict(ctx)
        nctx["column"] = slug
        nctx["disclosure"] = format_measure_disclosure(nctx)
        injected[slug] = nctx

    left_rename = {renames["left_t"][0]: renames["left_t"][1]}
    right_rename = {renames["right_t"][0]: renames["right_t"][1]}
    build_joined_table_on(
        conn,
        "left_t",
        "right_t",
        [("country", "country"), ("date", "date")],
        left_renames=left_rename,
        right_renames=right_rename,
    )
    return injected, renames["left_t"][1], renames["right_t"][1]


def test_indicator_resolves_measure_label():
    conn = duckdb.connect()
    _wb_panel(conn, "t", SLUMS, lambda i: i)
    ctx = resolve_measure_label(conn, "t", "value", catalog_title="", use_ai=False)
    assert ctx["label"] == SLUMS
    assert ctx["source"] == "indicator_column"


def test_measure_slug_unique_and_safe():
    used: set[str] = set()
    a = measure_slug(SLUMS, fallback="left_value", used=used)
    b = measure_slug(SLUMS, fallback="right_value", used=used)
    assert a != b  # collision avoided
    assert a.replace("_", "").isalnum()
    assert not a[0].isdigit()


def test_joined_columns_are_aliased_not_value_1():
    conn = duckdb.connect()
    injected, slug_l, slug_r = _build_joined(conn)
    cols = [r[0] for r in conn.execute("DESCRIBE analysis_joined").fetchall()]
    assert slug_l in cols
    assert slug_r in cols
    assert "value_1" not in cols
    assert slug_l != slug_r


def test_correlation_title_uses_indicator_labels():
    conn = duckdb.connect()
    injected, slug_l, slug_r = _build_joined(conn)
    profile = profile_table(
        conn,
        "analysis_joined",
        resource_id="a+b",
        title="joined",
        extra_measure_contexts=injected,
    )
    assert slug_l in profile.numeric and slug_r in profile.numeric
    findings = run_correlation(
        conn,
        "analysis_joined",
        [slug_l, slug_r],
        resource_id="a+b",
        dataset_title="joined",
        finding_offset=0,
        measure_contexts=profile.measure_contexts,
    )
    assert findings, "expected a significant correlation"
    f = enrich_finding(findings[0])
    assert "slums" in f.title.lower()
    assert "social protection" in f.title.lower()
    assert "value" not in f.title.lower()


def test_single_table_group_comparison_uses_indicator_label():
    conn = duckdb.connect()
    rows = []
    for i in range(24):
        region = "Asia" if i % 2 == 0 else "Europe"
        rows.append((f"C{i:02d}", SLUMS, region, float(i + (10 if region == "Asia" else 0))))
    conn.execute(
        "CREATE TABLE t (country VARCHAR, indicator VARCHAR, region VARCHAR, value DOUBLE)"
    )
    conn.executemany("INSERT INTO t VALUES (?, ?, ?, ?)", rows)
    profile = profile_table(conn, "t", resource_id="t", title="Slums")
    findings = run_group_comparison(
        conn,
        "t",
        "value",
        "region",
        resource_id="t",
        dataset_title="Slums",
        finding_offset=0,
        measure_contexts=profile.measure_contexts,
    )
    assert findings
    f = enrich_finding(findings[0])
    assert f.title.lower().startswith("population living in slums")
    assert "value differs" not in f.title.lower()
