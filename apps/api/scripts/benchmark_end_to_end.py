#!/usr/bin/env python3
"""End-to-end wait-time benchmark: "Run analysis" click -> results ready.

Measures the server-side wall time a user waits between starting an analysis
and the results page becoming available, broken down into phases:

    download   - HTTP fetch of dataset rows (parallel across 2 datasets)
    load       - DuckDB load + profile + validate (rest of ingest)
    compute    - statistical tests (analysis minus ML and AI summary)
    ml         - ML suite (clustering/anomaly), when ml_enabled
    ai         - Anthropic executive summary (network; ~constant vs size)
    -------------------------------------------------------------------
    total      - ingest + analysis = what the user actually waits for

The full size/source matrix runs with AI disabled (free + reproducible, so the
size/source scaling is clean). A small set of cases is then re-run with the
real Anthropic summary to price the (roughly constant) AI overhead.

Frontend overhead (3 sequential setup calls + up to ~1.5s status-poll
detection) is NOT included here; it is small and independent of dataset size.

Usage (from apps/api):
  .venv/bin/python scripts/benchmark_end_to_end.py
  .venv/bin/python scripts/benchmark_end_to_end.py --reps 2
  .venv/bin/python scripts/benchmark_end_to_end.py --ai-samples 4
  .venv/bin/python scripts/benchmark_end_to_end.py --json /tmp/e2e.json
  .venv/bin/python scripts/benchmark_end_to_end.py --only wb-large,nyc-large
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from findings_api.config import settings  # noqa: E402
from findings_api.db import get_session_factory  # noqa: E402
from findings_api.ingest import pipeline as pipeline_mod  # noqa: E402
from findings_api.ingest import download as download_mod  # noqa: E402
from findings_api.analysis import runner as runner_mod  # noqa: E402
from findings_api.ingest.duckdb_store import connect, session_db_path  # noqa: E402
from findings_api.models import AnalysisSession, CatalogResource  # noqa: E402


@dataclass(frozen=True)
class Case:
    name: str
    resource_ids: list[str]
    ml: bool = True


# Single-dataset cases span small -> large per portal; dual cases mirror the
# real product (max 2 datasets, compare mode + auto-join).
CASES: list[Case] = [
    # World Bank (per_page now 20000)
    Case("wb-small", ["wb:1.0.HCount.1.90usd"]),
    Case("wb-medium", ["wb:SI.POV.MDIM"]),
    Case("wb-large", ["wb:SN.SH.STA.MALN.ZS"]),
    # FRED
    Case("fred-small", ["fred:DDDM01USA156NWDB"]),
    Case("fred-medium", ["fred:INDPRO"]),
    Case("fred-large", ["fred:DGS10"]),
    # NYC Open Data (Socrata; large is row_cap-truncated)
    Case("nyc-small", ["nyc:6up2-gnw8"]),
    Case("nyc-medium", ["nyc:gdk4-mbsv"]),
    Case("nyc-large", ["nyc:43nn-pn8j"]),
    # data.gov (direct CSV)
    Case("datagov-small", ["datagov:blm-ut-designated-wild-and-scenic-river-corridors-polygon"]),
    Case("datagov-medium", ["datagov:blm-ak-conflicted-areas"]),
    Case(
        "datagov-large",
        ["datagov:data-and-code-from-electron-beam-irradiation-for-management-of-in-shell-pecan-weevil-larva"],
    ),
    # Dual-dataset (compare mode) — the headline 2-dataset scenario
    Case("dual-wb-wb", ["wb:SI.POV.MDIM", "wb:SP.POP.TOTL.ZS"]),
    Case("dual-wb-fred", ["wb:SI.POV.MDIM", "fred:INDPRO"]),
    Case("dual-nyc-nyc", ["nyc:gdk4-mbsv", "nyc:i2im-iqtt"]),
]

# Representative subset to re-run with real Anthropic summary (cost control).
AI_SAMPLE_NAMES = ["wb-small", "nyc-medium", "dual-wb-wb"]


# --- instrumentation (module-global, reset per run) -------------------------
class _Probe:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.downloads: list[dict] = []  # {start, end, bytes}
        self.ml_seconds = 0.0
        self.ai_seconds = 0.0
        self.ai_source: str | None = None


PROBE = _Probe()


async def _soda2_fetch(url, *, client=None, on_progress=None, on_heartbeat=None, title="", row_count_hint=None):  # noqa: ANN001
    """SODA2 GET fallback for NYC (SODA3 /query.json now requires an app token -> 403).

    Mirrors the product's chunked pagination so timings are representative of a
    fixed download path. Returns the same JSON-list bytes the pipeline expects.
    """
    import re
    from urllib.parse import parse_qs, urlparse

    m = re.search(r"/views/([^/]+)/query\.json", url)
    dsid = m.group(1) if m else url.rstrip("/").split("/")[-1].split(".")[0]
    qs = parse_qs(urlparse(url).query)
    soql = (qs.get("socrata_soql") or qs.get("$query") or [""])[0]
    select = None
    sm = re.search(r"select\s+(.*?)(?:\s+limit\s+\d+)?\s*$", soql, re.IGNORECASE)
    if sm and sm.group(1).strip():
        select = sm.group(1).strip()

    base = f"https://data.cityofnewyork.us/resource/{dsid}.json"
    chunk = max(1, settings.socrata_download_chunk_rows)
    cap = settings.row_cap
    owns = client is None
    if owns:
        client = httpx.AsyncClient(follow_redirects=True, trust_env=False)
    rows: list[dict] = []
    offset = 0
    try:
        while len(rows) < cap:
            take = min(chunk, cap - len(rows))
            params = {"$limit": take, "$offset": offset}
            if select:
                params["$select"] = select
            resp = await client.get(base, params=params, timeout=settings.download_chunk_timeout_sec)
            if resp.status_code >= 400:
                if rows:
                    break
                raise download_mod.DownloadError(f"NYC Open Data SODA2 HTTP {resp.status_code}")
            page = resp.json()
            if not isinstance(page, list) or not page:
                break
            rows.extend(page)
            offset += len(page)
            if on_progress:
                on_progress(f"Downloaded {len(rows):,} rows")
            if len(page) < take:
                break
        if not rows:
            raise download_mod.DownloadError("NYC Open Data query returned no rows")
        return json.dumps(rows).encode("utf-8")
    finally:
        if owns:
            await client.aclose()


def _install_instrumentation(*, soda2: bool) -> None:
    if soda2:
        download_mod.fetch_socrata_json = _soda2_fetch  # type: ignore[assignment]

    orig_fetch = pipeline_mod.fetch_resource_bytes
    orig_ml = runner_mod.run_ml_suite
    orig_ai = runner_mod.generate_ai_summary

    async def timed_fetch(*args, **kwargs):  # noqa: ANN001
        t0 = time.perf_counter()
        data, kind = await orig_fetch(*args, **kwargs)
        PROBE.downloads.append(
            {"start": t0, "end": time.perf_counter(), "bytes": len(data) if data else 0}
        )
        return data, kind

    def timed_ml(*args, **kwargs):  # noqa: ANN001
        t0 = time.perf_counter()
        out = orig_ml(*args, **kwargs)
        PROBE.ml_seconds += time.perf_counter() - t0
        return out

    def timed_ai(*args, **kwargs):  # noqa: ANN001
        t0 = time.perf_counter()
        out = orig_ai(*args, **kwargs)
        PROBE.ai_seconds += time.perf_counter() - t0
        try:
            PROBE.ai_source = out[1]  # (text, source, blocks, reason)
        except Exception:
            pass
        return out

    pipeline_mod.fetch_resource_bytes = timed_fetch  # type: ignore[assignment]
    runner_mod.run_ml_suite = timed_ml  # type: ignore[assignment]
    runner_mod.generate_ai_summary = timed_ai  # type: ignore[assignment]


@dataclass
class RunResult:
    download_wall: float = 0.0   # parallel wall time of downloads
    load: float = 0.0            # ingest minus download
    compute: float = 0.0         # analysis minus ml minus ai
    ml: float = 0.0
    ai: float = 0.0
    ai_source: str | None = None
    total: float = 0.0           # ingest + analysis (user wait)
    rows: dict[str, int] = field(default_factory=dict)
    total_bytes: int = 0
    ok: bool = False
    error: str | None = None


async def _run_once(case: Case, *, allow_ai: bool) -> RunResult:
    PROBE.reset()
    res = RunResult()
    factory = get_session_factory()
    db = factory()
    session_id = str(uuid.uuid4())

    saved_key = settings.anthropic_api_key
    if not allow_ai:
        settings.anthropic_api_key = ""  # forces template summary, no network/cost

    try:
        # Validate resources exist (avoid noisy failures mid-run).
        for rid in case.resource_ids:
            if not db.get(CatalogResource, rid):
                res.error = f"unknown resource {rid}"
                return res

        session = AnalysisSession(
            id=session_id,
            status="created",
            phase="pending",
            resource_ids=case.resource_ids,
            user_intent="benchmark wait-time analysis",
            config={"ml_enabled": case.ml, "filters": {}, "join_keys": []},
        )
        db.add(session)
        db.commit()

        # --- ingest (download + load) ---
        t_ing = time.perf_counter()
        await pipeline_mod.run_ingest(db, session_id)
        ingest_wall = time.perf_counter() - t_ing

        session = db.get(AnalysisSession, session_id)
        if not session or session.status != "ready":
            res.error = (session.error if session else None) or "ingest did not reach ready"
            return res

        # download wall = span from first fetch start to last fetch end (parallel)
        if PROBE.downloads:
            d0 = min(d["start"] for d in PROBE.downloads)
            d1 = max(d["end"] for d in PROBE.downloads)
            res.download_wall = d1 - d0
            res.total_bytes = sum(d["bytes"] for d in PROBE.downloads)
        res.load = max(0.0, ingest_wall - res.download_wall)

        # --- analysis (compute + ml + ai) ---
        t_an = time.perf_counter()
        await runner_mod.run_analysis_pipeline(db, session_id)
        analysis_wall = time.perf_counter() - t_an

        session = db.get(AnalysisSession, session_id)
        if not session or session.status != "complete":
            res.error = (session.error if session else None) or "analysis did not complete"
            return res

        res.ml = PROBE.ml_seconds
        res.ai = PROBE.ai_seconds
        res.ai_source = PROBE.ai_source
        res.compute = max(0.0, analysis_wall - res.ml - res.ai)
        res.total = ingest_wall + analysis_wall

        if session_db_path(session_id).exists():
            conn = connect(session_id)
            try:
                for idx in range(len(case.resource_ids)):
                    for table in (f"raw_{idx}", f"analysis_{idx}"):
                        try:
                            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                            res.rows[table] = int(n)
                        except Exception:
                            pass
            finally:
                conn.close()
        res.ok = True
        return res
    except Exception as exc:  # noqa: BLE001
        res.error = f"{type(exc).__name__}: {exc}"
        return res
    finally:
        settings.anthropic_api_key = saved_key
        try:
            obj = db.get(AnalysisSession, session_id)
            if obj:
                db.delete(obj)
                db.commit()
        except Exception:
            db.rollback()
        db.close()
        session_db_path(session_id).unlink(missing_ok=True)


@dataclass
class CaseSummary:
    name: str
    resource_ids: list[str]
    ml: bool
    reps: int
    ok: bool
    error: str | None
    rows_raw: int
    download_wall: float
    load: float
    compute: float
    ml_s: float
    total_no_ai: float
    ai_s: float | None = None
    ai_source: str | None = None
    total_with_ai: float | None = None


def _median(values: list[float]) -> float:
    return round(statistics.median(values), 2) if values else 0.0


async def run_matrix(*, reps: int, ai_samples: int, only: set[str] | None, soda2: bool) -> list[CaseSummary]:
    _install_instrumentation(soda2=soda2)
    cases = [c for c in CASES if not only or c.name in only]
    summaries: list[CaseSummary] = []

    for case in cases:
        runs: list[RunResult] = []
        for _ in range(reps):
            runs.append(await _run_once(case, allow_ai=False))
            await asyncio.sleep(0.5)  # be polite to external APIs
        ok_runs = [r for r in runs if r.ok]
        last = runs[-1]
        rows_raw = max((sum(v for k, v in r.rows.items() if k.startswith("raw_")) for r in ok_runs), default=0)

        summ = CaseSummary(
            name=case.name,
            resource_ids=case.resource_ids,
            ml=case.ml,
            reps=reps,
            ok=bool(ok_runs),
            error=None if ok_runs else last.error,
            rows_raw=rows_raw,
            download_wall=_median([r.download_wall for r in ok_runs]),
            load=_median([r.load for r in ok_runs]),
            compute=_median([r.compute for r in ok_runs]),
            ml_s=_median([r.ml for r in ok_runs]),
            total_no_ai=_median([r.total for r in ok_runs]),
        )
        summaries.append(summ)
        status = "OK" if summ.ok else f"FAIL ({summ.error})"
        print(
            f"  [no-ai] {case.name:<16} rows={rows_raw:<8,} dl={summ.download_wall:>5.1f}s "
            f"load={summ.load:>5.1f}s compute={summ.compute:>5.1f}s ml={summ.ml_s:>5.1f}s "
            f"total={summ.total_no_ai:>5.1f}s  {status}"
        )

    # Price the AI summary on a representative subset.
    sample_names = AI_SAMPLE_NAMES[:ai_samples]
    by_name = {s.name: s for s in summaries}
    print("\n  --- AI summary overhead (real Anthropic calls) ---")
    for name in sample_names:
        case = next((c for c in cases if c.name == name), None)
        if not case or name not in by_name:
            continue
        r = await _run_once(case, allow_ai=True)
        await asyncio.sleep(0.5)
        s = by_name[name]
        if r.ok:
            s.ai_s = round(r.ai, 2)
            s.ai_source = r.ai_source
            s.total_with_ai = round(r.total, 2)
            print(
                f"  [+ai]  {name:<16} ai={r.ai:>5.1f}s ({r.ai_source})  "
                f"total_with_ai={r.total:>5.1f}s (vs {s.total_no_ai:.1f}s no-ai)"
            )
        else:
            print(f"  [+ai]  {name:<16} FAIL ({r.error})")

    return summaries


def print_report(summaries: list[CaseSummary]) -> None:
    print("\n" + "=" * 104)
    print("END-TO-END WAIT TIME  (server-side: Run analysis -> results ready)")
    print(
        f"wb_per_page={settings.wb_download_per_page}  row_cap={settings.row_cap:,}  "
        f"socrata_chunk={settings.socrata_download_chunk_rows:,}"
    )
    print("=" * 104)
    print(
        f"{'Case':<16} {'rows':>8} {'download':>9} {'load':>7} {'compute':>8} "
        f"{'ml':>6} {'total':>7} {'+ai':>6} {'wait*':>7}"
    )
    print("-" * 104)
    for s in summaries:
        if not s.ok:
            print(f"{s.name:<16} {'-':>8}  FAIL: {s.error}")
            continue
        ai = f"{s.ai_s:.1f}" if s.ai_s is not None else "-"
        wait = s.total_with_ai if s.total_with_ai is not None else s.total_no_ai
        print(
            f"{s.name:<16} {s.rows_raw:>8,} {s.download_wall:>8.1f}s {s.load:>6.1f}s "
            f"{s.compute:>7.1f}s {s.ml_s:>5.1f}s {s.total_no_ai:>6.1f}s {ai:>6} {wait:>6.1f}s"
        )
    print("-" * 104)
    print("* wait = total_with_ai where measured, else total_no_ai. Add ~1-2s frontend/poll overhead.")


def main() -> int:
    parser = argparse.ArgumentParser(description="End-to-end wait-time benchmark")
    parser.add_argument("--reps", type=int, default=1, help="Repetitions per case (median reported)")
    parser.add_argument("--ai-samples", type=int, default=len(AI_SAMPLE_NAMES), help="How many cases to re-run with real AI")
    parser.add_argument("--only", type=str, default="", help="Comma-separated case names to run")
    parser.add_argument("--no-soda2", action="store_true", help="Use product SODA3 path (currently 403s)")
    parser.add_argument("--json", metavar="PATH", help="Write JSON results")
    args = parser.parse_args()

    only = {n.strip() for n in args.only.split(",") if n.strip()} or None
    summaries = asyncio.run(
        run_matrix(reps=args.reps, ai_samples=args.ai_samples, only=only, soda2=not args.no_soda2)
    )
    print_report(summaries)

    if args.json:
        Path(args.json).write_text(
            json.dumps([asdict(s) for s in summaries], indent=2, default=str), encoding="utf-8"
        )
        print(f"\nWrote {args.json}")
    return 0 if all(s.ok for s in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
