#!/usr/bin/env python3
"""Probe NYC Open Data (Socrata) compatibility with Findings catalog + ingest.

Usage (from repo root):
  cd apps/api && .venv/bin/python ../../scripts/nyc-open-data-probe.py
  cd apps/api && .venv/bin/python ../../scripts/nyc-open-data-probe.py --dataset h9gi-n95z
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

# Allow running from repo root without installing the package globally.
_API_SRC = Path(__file__).resolve().parents[1] / "apps" / "api" / "src"
if str(_API_SRC) not in sys.path:
    sys.path.insert(0, str(_API_SRC))

import duckdb
import httpx

from findings_api.catalog.probe import probe_bytes, probe_url
from findings_api.licensing import is_allowed, normalize_license

NYC_BASE = "https://data.cityofnewyork.us"
DEFAULT_DATASET = "5uac-w243"  # NYPD Complaint Data Current (YTD)


async def _fetch(client: httpx.AsyncClient, dataset_id: str) -> dict[str, tuple[int, bytes]]:
    out: dict[str, tuple[int, bytes]] = {}
    soda2 = f"{NYC_BASE}/resource/{dataset_id}.json?$limit=50"
    soda3 = f"{NYC_BASE}/api/v3/views/{dataset_id}/query.json"
    csv = f"{NYC_BASE}/api/views/{dataset_id}/rows.csv?accessType=DOWNLOAD&$limit=200"

    r = await client.get(soda2)
    out["soda2_json"] = (r.status_code, r.content)

    r = await client.post(
        soda3,
        json={"query": "SELECT boro_nm, ofns_desc, law_cat_cd, pd_desc LIMIT 50"},
    )
    out["soda3_json"] = (r.status_code, r.content)

    r = await client.get(csv)
    out["csv_limited"] = (r.status_code, r.content)

    return out


def _duckdb_smoke(csv_bytes: bytes, json_bytes: bytes) -> None:
    conn = duckdb.connect(":memory:")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(csv_bytes)
        csv_path = tmp.name
    conn.execute(
        "CREATE TABLE csv_data AS SELECT * FROM read_csv_auto(?, sample_size=20000)",
        [csv_path],
    )
    Path(csv_path).unlink(missing_ok=True)

    rows = json.loads(json_bytes)
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        json.dump(rows, tmp)
        json_path = tmp.name
    conn.execute("CREATE TABLE json_data AS SELECT * FROM read_json_auto(?)", [json_path])
    Path(json_path).unlink(missing_ok=True)

    csv_n, json_n = conn.execute("SELECT (SELECT COUNT(*) FROM csv_data), (SELECT COUNT(*) FROM json_data)").fetchone()
    print(f"\nDuckDB ingest smoke: CSV {csv_n} rows, SODA3 JSON {json_n} rows")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Probe NYC Open Data compatibility")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Socrata 4x4 dataset id")
    args = parser.parse_args()
    ds = args.dataset

    async with httpx.AsyncClient(follow_redirects=True, trust_env=False, timeout=60) as client:
        meta_resp = await client.get(f"{NYC_BASE}/api/views/{ds}.json")
        if meta_resp.status_code != 200:
            print(f"Metadata fetch failed: HTTP {meta_resp.status_code}")
            return 1
        meta = meta_resp.json()
        print(f"Dataset: {meta.get('name')} ({ds})")
        print(f"License field: {meta.get('license')!r}")
        for label in ("Public Domain", "US Government Work"):
            norm = normalize_license(label)
            print(f"  If treated as {label!r}: {norm}, allowed={is_allowed(norm, 'data_gov')}")

        payloads = await _fetch(client, ds)
        for label, (status, body) in payloads.items():
            print(f"\n[{label}] HTTP {status}, {len(body)} bytes")
            if status != 200:
                print(body[:300].decode(errors="replace"))
                continue
            probe = probe_bytes(body[:524_288], url=label)
            print(
                f"  catalog probe: ingestible={probe.ingestible}, "
                f"format={probe.detected_format}, reason={probe.reason}"
            )
            if probe.columns:
                print(f"  columns ({len(probe.columns)}): {probe.columns[:8]}")

        soda2_url = f"{NYC_BASE}/resource/{ds}.json?$limit=50"
        network = await probe_url(soda2_url, client=client)
        print(
            f"\nprobe_url(SODA2): ingestible={network.ingestible}, "
            f"format={network.detected_format}, reason={network.reason}"
        )

        _duckdb_smoke(payloads["csv_limited"][1], payloads["soda3_json"][1])

    print(
        "\nSummary: use CSV export or SODA3 POST query URLs (not raw SODA2 JSON). "
        "Add a Socrata sync module + nyc_open_data portal with US_GOV_WORK licensing."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
