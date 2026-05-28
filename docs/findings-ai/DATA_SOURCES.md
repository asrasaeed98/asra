# Data sources — Phase 1

## Active sync path

| Portal | Module | License | Notes |
|--------|--------|---------|-------|
| **data.gov Catalog API** | `sync_datagov.py` | CC0 / US PD / US Gov Work | Primary US source — replaces deprecated CKAN API (404 as of 2026) |
| **World Bank** | `sync_worldbank.py` | CC BY (attribution) | Indicator metadata + paginated JSON API |
| **FRED** | `sync_fred.py` | US Gov Work (citation requested) | Economic time series via FRED API (`FRED_API_KEY` required) |

Legacy CKAN sync (`sync_ckan.py`) remains for other CKAN portals but is **not** used for data.gov.

## Quality gates (all sources)

Every resource passes three gates before it appears in search:

1. **License gate** — allowlist per portal ([LICENSING.md](./LICENSING.md))
2. **Format probe** — sample download; reject HTML, ZIP, nested JSON, GeoJSON
3. **Row-count gate** — `CATALOG_MIN_ROWS` (default **20**); World Bank uses API `total` metadata

Blocked resources stay in the DB for admin review (`GET /admin/catalog/health`). Search shows **`ingestible=true` only**.

At ingest, `validate_table()` re-checks row/column quality before analysis runs.

## Config

| Env | Default | Purpose |
|-----|---------|---------|
| `CKAN_SYNC_MAX_PACKAGES` | 200 | Target **probed ingestible** data.gov resources |
| `CKAN_SYNC_MAX_INDEXED` | 0 | Max metadata rows indexed (0 = same as MAX_PACKAGES) |
| `CKAN_SYNC_ROWS` | 100 | CKAN page size |
| `CKAN_SYNC_MAX_PAGES` | 20 | Max pages per CKAN query (auto-raised when MAX_INDEXED is high) |
| `WB_SYNC_MAX_INDICATORS` | 2000 | Target ingestible World Bank indicators |
| `WB_SYNC_MAX_INDEXED` | 0 | Max WB metadata rows (0 = same as MAX_INDICATORS) |
| `WB_SYNC_MAX_PER_FAMILY` | 2 | Max indicators sharing the same normalized title family |
| `WB_SYNC_MAX_PER_TOPIC` | 250 | Max indicators per World Bank topic (spreads across themes) |
| `FRED_API_KEY` | — | Required for FRED sync ([free registration](https://fred.stlouisfed.org/docs/api/api_key.html)) |
| `FRED_SYNC_MAX_SERIES` | 150 | Target ingestible FRED series |
| `FRED_SYNC_MAX_INDEXED` | 0 | Max FRED metadata rows (0 = same as MAX_SERIES) |
| `CATALOG_SYNC_INTERVAL_HOURS` | 0 | Full metadata refresh interval (168 = weekly) |
| `CATALOG_PROBE_INTERVAL_HOURS` | 0 | Daily probe interval (24 = grow searchable count) |
| `CATALOG_PROBE_BATCH_SIZE` | 500 | Rows probed per grow run (~200/day is a gentle ramp) |
| `CATALOG_MIN_ROWS` | 20 | Minimum rows at sync probe |
| `ANALYSIS_MIN_ROWS` | 20 | Minimum rows after ingest |
| `CATALOG_PROBE_*` | see `.env.example` | Probe sample size and timeout |

Trigger sync: `POST /admin/sync` or `python -m findings_api.catalog.cli sync`

Probe pending metadata: `POST /admin/catalog/probe-batch` or `python -m findings_api.catalog.cli probe`

---

## Scaling toward 1M catalog rows

**Your understanding is correct:** sync is an offline ops job; user analysis only downloads data when a session starts.

**1M is achievable but not by probing everything in one sync.** Each probe hits upstream APIs (~seconds per row). Strategy:

1. **Two-tier indexing**
   - `*_MAX_INDEXED` — store metadata (title, URL, license) up to ~1M
   - `*_MAX_*` (ingestible targets) — how many get download-probed per sync
   - Rows beyond the ingestible target are stored with `ingest_block_reason: "pending probe"`

2. **Weekly full sync** — refresh metadata (`cli sync`)

3. **Daily probe batches** — `cli probe --limit 5000` gradually promotes pending rows to searchable ingestible

4. **Source ceilings (approx.)**
   - FRED: ~800k series (best path to bulk metadata via `/fred/series` pagination)
   - data.gov Catalog API: ~300k+ datasets
   - World Bank: ~16k indicators (not a 1M source alone)

Example production env for a large catalog:

```env
CKAN_SYNC_MAX_PACKAGES=50000
CKAN_SYNC_MAX_INDEXED=400000
WB_SYNC_MAX_INDICATORS=16000
WB_SYNC_MAX_INDEXED=16000
FRED_SYNC_MAX_SERIES=50000
FRED_SYNC_MAX_INDEXED=500000
CATALOG_PROBE_BATCH_SIZE=5000
```

**Future work before true 1M search UX:** Postgres full-text search (replace `search_text.contains`), incremental sync (avoid delete-all), optional lazy probe-on-select.

---

## Why the catalog felt small (~274 datasets)

Previous limits were conservative for local dev:

- **data.gov:** Catalog API sync capped at 40 datasets and often indexed bad URLs (landing pages, ZIP). CKAN sync was implemented but not wired.
- **World Bank:** 250 indicators indexed without row-count filtering; sparse indicators passed probe automatically.

**Fixes shipped:**

- CKAN sync is now primary for data.gov (paginated, license-biased queries)
- World Bank indicators probed for `total >= CATALOG_MIN_ROWS`
- Caps raised (200 data.gov + 500 World Bank targets)
- World Bank ingest paginates all API pages (not just first 500 rows)

---

## World Bank “1 row” issue

**Root cause:** Not a flatten bug for major indicators — popular series (e.g. GDP, unemployment) have 10k+ observations. The 1-row experience came from:

1. **No row gate at sync** — sparse indicators were indexed as ingestible
2. **Single-page ingest** — only first API page loaded (up to 500 rows; truncation, not 1 row)
3. **Possible user filters** — review-step SQL can reduce rows dramatically

**Now:** sparse indicators blocked at sync; ingest paginates; `validate_table()` fails fast with a clear error if a dataset is too thin.

---

## Portal options — ranked

### Tier 1 — add next (stable, tabular, clear license)

| Portal | License | Format | Integration effort | Stability |
|--------|---------|--------|-------------------|-----------|
| **data.gov CKAN** | CC0 / US PD | CSV, JSON | Done | High — mature API, millions of resources |
| **World Bank** | CC BY | JSON API | Done | High — stable REST, documented schema |
| **FRED** (St. Louis Fed) | Public domain | CSV/API | Low — similar to World Bank | High — economic time series |
| **BLS** | US Gov Work | CSV/API | Medium — registration for some endpoints | High |
| **Census** (data.census.gov) | US Gov Work | CSV/API | Medium — table IDs, API keys for some | High |

**Recommendation:** Add **FRED** next — public domain, clean CSV/API, no auth for basic series, excellent for demos.

### Tier 2 — viable with adapters

| Portal | Notes |
|--------|-------|
| **CDC / data.cdc.gov** | Health stats; mostly CSV |
| **NOAA NCEI** | Climate; mix of CSV and ZIP |
| **USASpending** | Federal spending JSON — flatten adapter needed |
| **EPA ECHO** | Many ZIP/geospatial — probe blocks until unzip adapter |

### Tier 3 — defer (auth, cost, or license friction)

| Portal | Blocker | Verdict |
|--------|---------|---------|
| **Google BigQuery Public Datasets** | Requires GCP project + billing account; queries cost after 1 TB/mo; export to CSV needs GCS bucket; per-dataset licenses vary (many CC BY, some custom) | **Defer** — powerful but ops-heavy; better as Phase 2 “power user” connector |
| **Airtable** | No public dataset catalog; each base needs API key; rate limits; terms restrict redistribution | **Not suitable** for anonymous public catalog |
| **Supabase** | Some projects expose public REST (`/rest/v1/`) with anon key, but no central registry; stability depends on individual project owners | **Curated list only** — could wrap 5–10 known public tables with hardcoded URLs + keys in env, not open-ended sync |
| **Kaggle, Hugging Face** | License + auth | Defer |
| **Eurostat, OECD** | Often CC-BY-SA / restrictive | Legal review first |

---

## Evaluated alternatives (detail)

### Google BigQuery Public Datasets

- **Access:** `bigquery-public-data` project; query via SQL or REST API
- **Cost:** Storage free; queries billed (1 TB/month free tier)
- **Export path:** Query → temp table → export to GCS → download CSV — not a direct file URL
- **License:** Per-dataset; must check each (e.g. NOAA, GitHub, CMS vary)
- **Fit for FunFinds:** Poor for Phase 1 “click and analyze” — needs GCP credentials, export pipeline, and per-table legal review. Consider later as optional connector for users who bring their own GCP project.

### Airtable

- **Access:** Personal access token + base ID per dataset
- **Stability:** Depends on base owner; no SLA for third-party bases
- **License:** Base creator’s terms; not uniformly open
- **Fit for FunFinds:** Not a public catalog source. Could support “paste your Airtable URL + token” in a future paid tier.

### Supabase

- **Access:** Project URL + anon/service key; PostgREST API returns JSON
- **Public examples:** Some tutorials expose read-only anon keys; no official public dataset program
- **Stability:** Project-dependent; keys can be rotated/revoked
- **Fit for FunFinds:** Only viable as a **curated allowlist** (e.g. 10 known public projects with env-stored keys). Not suitable for open-ended crawl.

---

## Index document (per resource)

```json
{
  "id": "ckan:{package_id}:{resource_id}",
  "title": "",
  "portal": "data_gov",
  "format": "CSV",
  "license_normalized": "CC0",
  "resource_url": "",
  "row_count_hint": 1500,
  "ingestible": true,
  "ingest_block_reason": null
}
```

## Sync schedule

- On first API start when catalog empty (local dev)
- Manual: `POST /admin/sync`
- Production target: nightly re-probe for broken links

## Not in Phase 1

- Kaggle, Hugging Face, arbitrary URLs, PDF-only resources
- BigQuery connector (Phase 2 candidate)
- Airtable open crawl

See also [CATALOG_QA.md](./CATALOG_QA.md), [LICENSING.md](./LICENSING.md), [FEASIBILITY.md](./FEASIBILITY.md).
