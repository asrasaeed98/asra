# Catalog quality — scaling datasets without breaking ingest

## Problem

Open data portals expose heterogeneous formats: CSV, nested JSON, HTML landing pages, ZIP geodatabases, GeoJSON, Excel, API envelopes. Indexing everything and fixing failures one-by-one does not scale.

**Current catalog snapshot (local dev):** 250 World Bank indicators (structured API) + 4 data.gov Catalog API entries that all pointed at the same EPA `.gdb.zip` — not ingestible. That is why search felt empty or ingest failed.

## Strategy: three gates

| Gate | When | Outcome |
|------|------|---------|
| **1. Index** | Catalog sync | Only store resources that pass license + format probe |
| **2. Normalize** | Ingest | Source adapters flatten to tabular rows (e.g. World Bank) |
| **3. Validate** | Before analysis | Row/column checks; clear user errors |

Search shows **`ingestible=true` only**. Blocked resources stay in DB for admin review (`GET /admin/catalog/health`).

## What we built (Gate 1)

- **`catalog/probe.py`** — sample download + classify: CSV, flat JSON, World Bank envelope, or reject (HTML, ZIP, nested JSON, GeoJSON)
- **CKAN sync** replaces Catalog API sync for data.gov — per-resource URL + declared format (CSV/JSON)
- **`ingestible`, `detected_format`, `ingest_block_reason`** on `catalog_resources`
- **`POST /admin/sync`** — sync + probe
- **`GET /admin/catalog/health`** — totals, blocked reasons

### Config

| Env | Default | Purpose |
|-----|---------|---------|
| `CATALOG_PROBE_ENABLED` | `true` | Probe URLs during sync |
| `CATALOG_PROBE_MAX_BYTES` | `256000` | Sample size for probe |
| `CATALOG_PROBE_TIMEOUT_SEC` | `20` | Probe timeout |
| `CKAN_SYNC_MAX_PACKAGES` | `40` | data.gov package cap |
| `WB_SYNC_MAX_INDICATORS` | `250` | World Bank cap |

After pulling this code, run **`POST /admin/sync`** (or delete local DB) so old non-ingestible rows are replaced.

---

## Portal options (ranked)

### Tier 1 — add next (license fits, tabular, API/CSV)

| Portal | License | Format | Why |
|--------|---------|--------|-----|
| **data.gov CKAN** | CC0 / US PD / US Gov Work | CSV, JSON per resource | Already wired; probe filters bad URLs |
| **World Bank** | CC BY (attribution) | JSON API | Already wired + flatten adapter |
| **FRED** (St. Louis Fed) | Public domain | CSV/API | Clean economic time series |
| **BLS** | US Gov Work | CSV/API | Employment, CPI, wages |
| **Census** (data.census.gov) | US Gov Work | CSV/API | Demographics, ACS tables |

### Tier 2 — good demos, needs adapters

| Portal | Notes |
|--------|-------|
| **CDC / data.cdc.gov** | Health stats; mostly CSV |
| **NOAA NCEI** | Climate; mix of CSV and ZIP |
| **EPA ECHO** | Environmental; many ZIP/geospatial — probe will block until unpack |
| **USASpending** | Federal spending JSON — may need flatten adapter |

### Tier 3 — defer

| Portal | Blocker |
|--------|---------|
| Kaggle, Hugging Face | License + auth |
| Eurostat, OECD | Often CC-BY-SA / restrictive |
| Arbitrary URLs | No license gate |
| PDF, HTML-only, GeoJSON, XLSX | No adapter yet |

**License rule (unchanged):** data.gov = CC0/PD/US Gov Work only. World Bank = CC BY with attribution. Do not mix CC-BY portals into data.gov without legal review.

---

## Robust process (operational)

### 1. Sync pipeline

```text
Portal fetcher → license gate → format allowlist → URL probe → upsert catalog
```

- **Fetcher:** one module per portal (`sync_ckan`, `sync_worldbank`, future `sync_fred`)
- **Probe:** every new URL before `ingestible=true`
- **Re-probe:** nightly sync refreshes `probed_at`; broken links auto-drop from search

### 2. Ingest adapters (Gate 2)

```text
ingest/adapters/
  csv.py
  json_records.py
  worldbank.py
  (future: fred.py, census.py)
```

Each adapter returns flat `{column: scalar}` rows. New source = new adapter + fixture test, not changes in `profile.py`.

### 3. Pre-analysis validation (Gate 3 — next)

After load, before tests:

- ≥ 20 rows
- ≥ 1 numeric or categorical column
- No 100% null columns
- User-readable failure messages

### 4. Golden fixtures

Per portal, commit a **50-row sample file** in `apps/api/tests/fixtures/catalog/` and test:

- `probe_bytes(sample)` → ingestible
- `normalize(sample)` → expected columns
- `validate(table)` → passes

### 5. Catalog health review

Weekly (or after sync):

```bash
curl http://localhost:8000/admin/catalog/health
```

Watch `top_block_reasons`. Common fixes:

| Reason | Fix |
|--------|-----|
| HTML page | Pick a different distribution in CKAN |
| ZIP archive | Add unzip adapter or exclude format |
| nested JSON | Add portal adapter |
| HTTP 403/404 | Drop resource or update URL |

---

## Expanding catalog size safely

1. **Increase caps gradually** — `CKAN_SYNC_MAX_PACKAGES=200`, then `500`; monitor health ratio (target ≥70% ingestible for data.gov).
2. **One portal at a time** — implement fetcher + probe rules + adapter + fixtures before enabling in production sync.
3. **Prefer resource-level URLs** — never index package landing pages (old Catalog API bug).
4. **Bias CKAN query** — `license_id:cc-zero OR license_id:us-pd` + tags like `csv`, `statistics`, `economy`.
5. **Do not index XLS/XLSX** until an explicit adapter exists.

---

## Next implementation slices

1. Extract ingest adapters from `pipeline.py`
2. `validate_table()` before analysis
3. FRED or Census sync module (Tier 1 portal)
4. ZIP: download, pick largest CSV inside, probe inner file
5. Optional: pre-compute `columns` + row hints at sync for richer search

See also [DATA_SOURCES.md](./DATA_SOURCES.md), [FEASIBILITY.md](./FEASIBILITY.md), [LICENSING.md](./LICENSING.md).
