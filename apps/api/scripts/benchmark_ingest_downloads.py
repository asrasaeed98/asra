#!/usr/bin/env python3
"""Live benchmark: download + optional full ingest across portals and sizes.

Usage (from apps/api):
  .venv/bin/python scripts/benchmark_ingest_downloads.py
  .venv/bin/python scripts/benchmark_ingest_downloads.py --ingest
  .venv/bin/python scripts/benchmark_ingest_downloads.py --json /tmp/bench.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx

# Allow running as `python scripts/benchmark_ingest_downloads.py`
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from findings_api.config import settings  # noqa: E402
from findings_api.db import get_session_factory  # noqa: E402
from findings_api.ingest.download import DownloadError, fetch_resource_bytes  # noqa: E402
from findings_api.ingest.duckdb_store import connect, session_db_path  # noqa: E402
from findings_api.models import AnalysisSession, CatalogResource  # noqa: E402


@dataclass(frozen=True)
class Case:
    name: str
    resource_ids: list[str]
    """When len > 1: compare parallel vs sequential unless sequential_only."""
    sequential_only: bool = False
    run_ingest: bool = False


CASES: list[Case] = [
    # World Bank — size tiers
    Case("wb-tiny", ["wb:1.0.HCount.1.90usd"]),
    Case("wb-medium", ["wb:SE.ADT.LITR.ZS"]),
    Case("wb-dual-sequential", ["wb:SE.ADT.LITR.ZS", "wb:EG.CFT.ACCS.ZS"], sequential_only=True),
    Case("wb-dual-parallel", ["wb:SE.ADT.LITR.ZS", "wb:EG.CFT.ACCS.ZS"]),
    # FRED
    Case("fred-tiny", ["fred:DDDM01USA156NWDB"]),
    Case("fred-medium", ["fred:PAYEMS"]),
    # NYC Open Data (Socrata)
    Case("nyc-tiny", ["nyc:6up2-gnw8"]),
    Case("nyc-medium", ["nyc:qhkz-4dqm"]),
    # data.gov (direct CSV)
    Case("datagov-csv", ["datagov:hhs-covid-19-monthly-outcome-survey-wave-14"]),
    # Cross-portal parallel
    Case("mixed-wb-fred", ["wb:1.0.HCount.1.90usd", "fred:DDDM01USA156NWDB"]),
]


@dataclass
class ResourceResult:
    id: str
    portal: str
    row_hint: int | None
    bytes: int = 0
    rows: int | None = None
    seconds: float = 0.0
    ok: bool = False
    error: str | None = None


@dataclass
class CaseResult:
    name: str
    mode: str
    resource_ids: list[str]
    ok: bool = False
    seconds: float = 0.0
    total_bytes: int = 0
    resources: list[ResourceResult] = field(default_factory=list)
    ingest_seconds: float | None = None
    duckdb_rows: dict[str, int] | None = None
    error: str | None = None
    speedup_vs_sequential: float | None = None


def _count_rows(data: bytes, portal: str) -> int | None:
    try:
        if portal == "fred":
            payload = json.loads(data.decode("utf-8"))
            obs = payload.get("observations")
            return len(obs) if isinstance(obs, list) else None
        if portal == "world_bank":
            payload = json.loads(data.decode("utf-8"))
            if isinstance(payload, list) and len(payload) >= 2 and isinstance(payload[1], list):
                return len(payload[1])
            return None
        if portal == "nyc_open_data":
            payload = json.loads(data.decode("utf-8"))
            if isinstance(payload, list):
                return len(payload)
            return None
        text = data.decode("utf-8", errors="replace")
        if text.lstrip().startswith("{") or text.lstrip().startswith("["):
            payload = json.loads(text)
            if isinstance(payload, list):
                return len(payload)
            return 1
        # CSV / plain text
        lines = [ln for ln in text.splitlines() if ln.strip()]
        return max(0, len(lines) - 1) if lines else 0
    except Exception:
        return None


async def _download_one(client: httpx.AsyncClient, resource: CatalogResource) -> ResourceResult:
    result = ResourceResult(
        id=resource.id,
        portal=resource.portal,
        row_hint=resource.row_count_hint,
    )
    t0 = time.perf_counter()
    try:
        data, _kind = await fetch_resource_bytes(
            resource.resource_url or "",
            client=client,
            portal=resource.portal,
            title=resource.title,
            row_count_hint=resource.row_count_hint,
        )
        result.bytes = len(data)
        result.rows = _count_rows(data, resource.portal)
        result.ok = True
    except DownloadError as exc:
        result.error = str(exc)
    except Exception as exc:
        result.error = f"{type(exc).__name__}: {exc}"
    result.seconds = time.perf_counter() - t0
    return result


async def _download_multi(
    resources: list[CatalogResource],
    *,
    parallel: bool,
) -> tuple[list[ResourceResult], float]:
    async with httpx.AsyncClient(follow_redirects=True, trust_env=False) as client:
        t0 = time.perf_counter()
        if len(resources) == 1:
            results = [await _download_one(client, resources[0])]
        elif parallel:
            results = list(await asyncio.gather(*[_download_one(client, r) for r in resources]))
        else:
            results = []
            for resource in resources:
                results.append(await _download_one(client, resource))
        elapsed = time.perf_counter() - t0
    return results, elapsed


async def _run_ingest_case(resource_ids: list[str]) -> tuple[float, dict[str, int] | None, str | None]:
    from findings_api.ingest.pipeline import run_ingest

    session_id = str(uuid.uuid4())
    factory = get_session_factory()
    db = factory()
    try:
        session = AnalysisSession(
            id=session_id,
            status="ingesting",
            phase="ingest",
            resource_ids=resource_ids,
            user_intent="benchmark",
            config={"ml_enabled": False},
        )
        db.add(session)
        db.commit()

        t0 = time.perf_counter()
        await run_ingest(db, session_id)
        elapsed = time.perf_counter() - t0

        session = db.get(AnalysisSession, session_id)
        if not session or session.status == "failed":
            return elapsed, None, session.error if session else "session missing"

        row_counts: dict[str, int] = {}
        if session_db_path(session_id).exists():
            conn = connect(session_id)
            try:
                for idx in range(len(resource_ids)):
                    for table in (f"raw_{idx}", f"analysis_{idx}"):
                        try:
                            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                            row_counts[table] = int(n)
                        except Exception:
                            pass
            finally:
                conn.close()
        return elapsed, row_counts or None, None
    finally:
        db.close()
        path = session_db_path(session_id)
        if path.exists():
            path.unlink(missing_ok=True)


def _load_resources(db, resource_ids: list[str]) -> list[CatalogResource]:
    resources: list[CatalogResource] = []
    for rid in resource_ids:
        row = db.get(CatalogResource, rid)
        if not row:
            raise KeyError(f"Unknown catalog resource: {rid}")
        if not row.resource_url:
            raise KeyError(f"No resource_url for {rid}")
        resources.append(row)
    return resources


async def run_benchmark(*, include_ingest: bool, skip_sequential: bool = False) -> list[CaseResult]:
    factory = get_session_factory()
    db = factory()
    results: list[CaseResult] = []
    sequential_times: dict[frozenset[str], float] = {}

    try:
        for case in CASES:
            if skip_sequential and case.sequential_only:
                continue
            resources = _load_resources(db, case.resource_ids)
            parallel = len(resources) > 1 and not case.sequential_only
            mode = "sequential" if case.sequential_only else ("parallel" if len(resources) > 1 else "single")

            cr = CaseResult(name=case.name, mode=mode, resource_ids=case.resource_ids)
            try:
                resource_results, elapsed = await _download_multi(resources, parallel=parallel)
                cr.resources = resource_results
                cr.seconds = elapsed
                cr.total_bytes = sum(r.bytes for r in resource_results)
                cr.ok = all(r.ok for r in resource_results)
                if not cr.ok:
                    cr.error = "; ".join(r.error for r in resource_results if r.error)

                if case.sequential_only:
                    sequential_times[frozenset(case.resource_ids)] = elapsed
                elif len(resources) > 1 and not case.sequential_only:
                    seq = sequential_times.get(frozenset(case.resource_ids))
                    if seq and elapsed > 0:
                        cr.speedup_vs_sequential = round(seq / elapsed, 2)

                if include_ingest and (case.run_ingest or case.name in {
                    "wb-tiny",
                    "wb-dual-parallel",
                    "nyc-medium",
                    "fred-medium",
                    "mixed-wb-fred",
                }):
                    try:
                        ingest_sec, duckdb_rows, ingest_err = await _run_ingest_case(case.resource_ids)
                        cr.ingest_seconds = ingest_sec
                        cr.duckdb_rows = duckdb_rows
                        if ingest_err:
                            cr.ok = False
                            cr.error = ingest_err if not cr.error else f"{cr.error}; ingest: {ingest_err}"
                    except Exception as exc:
                        cr.ok = False
                        cr.error = f"ingest {type(exc).__name__}: {exc}" if not cr.error else f"{cr.error}; ingest: {exc}"
            except KeyError as exc:
                cr.ok = False
                cr.error = str(exc)
            except Exception as exc:
                cr.ok = False
                cr.error = f"{type(exc).__name__}: {exc}"

            results.append(cr)
    finally:
        db.close()

    return results


def _fmt_rows(n: int | None, hint: int | None) -> str:
    if n is None:
        return "?"
    if hint:
        delta = n - hint
        if abs(delta) <= max(5, hint * 0.02):
            return f"{n:,} (≈hint)"
        return f"{n:,} (hint {hint:,}, Δ{delta:+,})"
    return f"{n:,}"


def print_report(results: list[CaseResult]) -> None:
    print()
    print("=" * 100)
    print("INGEST DOWNLOAD BENCHMARK")
    print(f"wb_download_per_page={settings.wb_download_per_page}  row_cap={settings.row_cap:,}  "
          f"fred_key={'yes' if settings.fred_api_key else 'NO'}")
    print("=" * 100)

    ok_n = sum(1 for r in results if r.ok)
    print(f"\nDownload: {ok_n}/{len(results)} cases passed\n")

    print(f"{'Case':<22} {'Mode':<12} {'Time':>7} {'Bytes':>10} {'Status':<6}  Details")
    print("-" * 100)
    for r in results:
        status = "OK" if r.ok else "FAIL"
        details = []
        for res in r.resources:
            details.append(
                f"{res.id.split(':')[-1][:12]} rows={_fmt_rows(res.rows, res.row_hint)} "
                f"{res.seconds:.1f}s"
            )
        if r.speedup_vs_sequential:
            details.append(f"speedup={r.speedup_vs_sequential}x vs sequential")
        if r.ingest_seconds is not None:
            ingest_status = "ok" if r.ok else "fail"
            details.append(f"ingest={r.ingest_seconds:.1f}s ({ingest_status})")
            if r.duckdb_rows:
                raw = {k: v for k, v in r.duckdb_rows.items() if k.startswith("raw_")}
                details.append(f"duckdb={raw}")
        if r.error:
            details.append(f"ERR: {r.error[:80]}")
        print(
            f"{r.name:<22} {r.mode:<12} {r.seconds:>6.2f}s {r.total_bytes:>10,} "
            f"{status:<6}  {' | '.join(details)}"
        )

    print("\n--- Portal summary ---")
    by_portal: dict[str, list[CaseResult]] = {}
    for r in results:
        for res in r.resources:
            by_portal.setdefault(res.portal, []).append(r)
    for portal in sorted(by_portal):
        portal_results = by_portal[portal]
        passed = sum(1 for r in portal_results if r.ok)
        avg = sum(r.seconds for r in portal_results) / max(1, len(portal_results))
        print(f"  {portal:<16} cases={len(portal_results)}  avg_wall={avg:.2f}s")

    dual = next((r for r in results if r.name == "wb-dual-parallel"), None)
    dual_seq = next((r for r in results if r.name == "wb-dual-sequential"), None)
    if dual and dual_seq and dual.ok and dual_seq.ok:
        print(
            f"\n--- WB dual-dataset ---\n"
            f"  Sequential: {dual_seq.seconds:.2f}s  |  Parallel: {dual.seconds:.2f}s  |  "
            f"Speedup: {dual_seq.seconds / max(dual.seconds, 0.01):.2f}x"
        )

    failed = [r for r in results if not r.ok]
    if failed:
        print("\n--- Failures ---")
        for r in failed:
            print(f"  {r.name}: {r.error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark ingest downloads across sources")
    parser.add_argument("--ingest", action="store_true", help="Also run full ingest (download + DuckDB load)")
    parser.add_argument("--json", metavar="PATH", help="Write JSON results to file")
    parser.add_argument(
        "--skip-sequential",
        action="store_true",
        help="Skip wb-dual-sequential (slow; hammers World Bank API)",
    )
    args = parser.parse_args()

    if not settings.fred_api_key:
        print("WARNING: FRED_API_KEY not set — FRED and mixed cases will fail.", file=sys.stderr)

    results = asyncio.run(run_benchmark(include_ingest=args.ingest, skip_sequential=args.skip_sequential))
    print_report(results)

    if args.json:
        Path(args.json).write_text(
            json.dumps([asdict(r) for r in results], indent=2, default=str),
            encoding="utf-8",
        )
        print(f"\nWrote {args.json}")

    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
