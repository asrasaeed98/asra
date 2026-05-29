# FunFinds — agent handoff (May 2026)

Short “start here” for the next agent or session. Full planning docs remain in `docs/findings-ai/`.

## Repo state

| Item | Value |
|------|--------|
| Branch | `main` (pushed to `origin/main`) |
| Latest work | May 28 session: grounded chat + AI budget cap + dataset facts + API resilience + UX reorder + home/about (see `git log`) |
| Prior commits | `ba06814` analysis/join/ML/chart UX · `39cadda` catalog expansion |
| Working tree | Clean (untracked `.next/` at repo root is gitignored) |
| App name | **FunFinds** (`NEXT_PUBLIC_APP_NAME=FunFinds`) |

## Start local dev

**Prereqs:** `.env` at repo root (copy from `.env.example`; never commit). Needs `ANTHROPIC_API_KEY` for AI summaries and measure semantics.

**Terminal 1 — API (port 8000)**

```bash
cd /path/to/asra
pip install -e "apps/api[dev]"   # or use apps/api/.venv
uvicorn findings_api.main:app --reload --port 8000
```

**Terminal 2 — Web**

Production mode (recommended — dev on 3000 has been flaky):

```bash
cd apps/web
npm install
npm run build
npx next start --hostname 127.0.0.1 --port 3002
```

Open **http://127.0.0.1:3002** (not 3000 unless dev server is confirmed healthy).

**CORS:** `.env.example` includes origins for localhost/127.0.0.1 ports 3000–3002. Match in your `.env`.

**Catalog (once per DB):**

```bash
curl -X POST http://localhost:8000/admin/sync
# or: npm run sync:catalog:cli
```

**Health check:**

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/search?q=gdp"
curl -I http://127.0.0.1:3002/
```

## What was done (May 28, 2026 session)

### API resilience & security (`ingest/download.py`, `pipeline.py`, `config.py`)
- **World Bank pagination P0 fixed:** per-page retry with backoff; deep-page 4xx returns partial data with a warning; only page 1 / empty is fatal.
- Retry with exponential backoff for FRED + resource fetches on 429/5xx/network errors.
- **API key redaction:** `redact_secrets` strips keys/tokens from URLs and error messages before they reach the session/UI. Rotate the exposed FRED key.
- Config: `download_max_retries`, `download_backoff_base_sec`.
- Tests: `test_worldbank_download.py`.

### Measure semantics for joins (`labels.py`, `measure_semantics.py`, `profile.py`, `join.py`, `runner.py`, `narrative.py`, `charts.py`, test runners)
- Generic `value` / `value_1` columns are resolved to indicator labels **before** the join, aliased to unique slugs via DuckDB `SELECT * RENAME`, and threaded through findings/charts/titles.
- Tests: `test_measure_join_labels.py`.

### Grounded chat — Slice 8 (`analysis/chat.py`, `routers/sessions.py`, `schemas.py`, web `ChatPanel.tsx`)
- `POST /sessions/{id}/chat`, placed **after the findings** on the results page (evidence-first UX).
- **5-question/session cap** (server-enforced; failed/budget calls don't consume a question).
- Grounded only in compact findings + AI summary + **dataset facts** (never raw data); last 4 turns; `max_tokens=400`.
- Config: `chat_max_questions`, `chat_max_tokens`, `chat_history_turns`, `chat_context_char_cap` (16000).

### AI budget cap (`analysis/ai_usage.py`, `models.py` `ApiUsage`, `config.py`)
- Monthly USD ledger of token spend; both summary + chat check it and **degrade gracefully** ("ran out of AI budget") when over.
- Reactive handling of credit/rate-limit errors too.
- `AI_MONTHLY_BUDGET_USD` (default **100**; `<=0` disables). `ai_paused` surfaced to the chat UI.
- Tests: `test_ai_budget.py`.

### Dataset facts for chat (`analysis/profile.py`, `runner.py`, `chat.py`)
- Per-table facts sheet (row count, column types, year/time coverage, numeric min/max/mean, **full value lists** for categoricals ≤300 distinct) stored in `results.dataset_facts` and fed to chat, so it can answer "what years?", value ranges, and membership ("is the US in here?") cheaply.

### Analysis quality + UX
- **Geo dedupe** (`selector.py`): when both `country` and `countryiso3code` exist, only the name is used for group comparisons (no more duplicate "across Country / Country code" findings).
- **Results page reorder:** Summary → Key results + charts → Chat → Analysis report (technical details collapsed). Friendly plain-language analysis-report summary; jargon moved into a "Technical details" dropdown.
- **Search page:** fixed React setState-during-render console error.

### Marketing pages (web)
- Rewrote **home page** (positioning: verifiable stats on authoritative data) and added an **About page** + top-nav (`Home · About · Search datasets`).

### Note on existing sessions
Chart/label/facts/dedupe changes apply to **new analyses**. Old sessions need a re-run. (ATMs session `e3697ba9` was regenerated this session for testing.)

## What was done (prior session)

### Committed & pushed to GitHub

**Catalog (`39cadda`)**
- FRED sync, World Bank diversity grouping, column quality, probe batch, scheduler/CLI, validation
- Ingest helpers for FRED/World Bank JSON

**Analysis & UX (`ba06814`)**
- **Panel datasets:** World Bank `country` + `date` + `value` profiling, geo-as-categorical, year aggregation for trends
- **Join v2:** ranked suggestions, composite keys, semantic aliases; Review UI `joinOn` picker
- **Charts:** top-10 category trim, horizontal bars for high-cardinality geo, skip duplicate ISO charts
- **Measure semantics:** `measure_semantics.py` — metadata/AI labels for generic `value` columns
- **ML suite:** K-means, DBSCAN, PCA, Isolation Forest, LOF; ML included in key-results ranking (not excluded)
- **Review UI:** ML checkbox defaults **on**; home page step reorder (search → select → analyze)
- **Results UI:** measure notes, finding labels, VegaChart component
- Tests: `test_join.py`, `test_charts.py`, `test_ml_suite.py`, `test_worldbank_panel.py`, `test_measure_semantics.py`

### Operational fixes (in code)
- CORS expanded for ports 3000–3002
- Session schema: `ml_enabled` defaults true

## Pending items (priority order)

### Done this session (was pending)
- ✅ **P0 World Bank pagination 400s** — fixed in `fetch_worldbank_json` (per-page retry + partial data).
- ✅ **Slice 8 grounded chat** — shipped with 5-question cap + budget guard.
- ✅ **Join-time value renaming** — measure labels resolved pre-join and aliased.

### Action required (you)
- **Rotate the FRED API key** — it was exposed in an error URL earlier; redaction is now in place but rotate to be safe.

### P1 — Deploy to production

Code is on GitHub but **not deployed** this session.

See [DEPLOY.md](./DEPLOY.md):
- **Web:** Vercel, root `apps/web`, set `NEXT_PUBLIC_API_URL`
- **API:** Railway, root `apps/api`, set `DATABASE_URL`, `ANTHROPIC_API_KEY`, `CORS_ORIGINS`

After deploy: run catalog sync on production DB.

### P2 — Discussed but not started

| Item | Notes |
|------|--------|
| Pearson vs Spearman auto-select | Correlation test choice based on distribution |
| WB trailing-page edge cases | Some indicators report optimistic `meta.pages`; validate against empty responses (largely mitigated by retry/partial-data fix) |
| Chat SQL path | Safe aggregate lookups for questions facts can't answer (e.g. "which country had the most ATMs in 2015"); membership on columns >300 distinct |
| Chat discoverability | Chat now sits below findings; consider a "jump to chat" nudge |

### Background catalog growth (scheduler)

In-process scheduler (`catalog/scheduler.py`) grows the searchable catalog. **Off by default.**

- Enable recurring growth via env, then restart the API:
  - `CATALOG_PROBE_INTERVAL_HOURS=24` (probe pending rows daily; `CATALOG_PROBE_BATCH_SIZE=500`)
  - `CATALOG_SYNC_INTERVAL_HOURS=168` (weekly full re-sync; optional)
- One-off growth now (no restart): `cd apps/api && .venv/bin/python -m findings_api.catalog.cli grow --limit 500`
- Full re-sync: `... cli sync`

## Key files

| Area | Path |
|------|------|
| WB download | `apps/api/src/findings_api/ingest/download.py` |
| Ingest pipeline | `apps/api/src/findings_api/ingest/pipeline.py` |
| Profile / selector | `apps/api/src/findings_api/analysis/profile.py`, `selector.py` |
| Analysis runner | `apps/api/src/findings_api/analysis/runner.py` |
| ML | `apps/api/src/findings_api/analysis/ml/clustering.py` |
| Charts | `apps/api/src/findings_api/analysis/charts.py` |
| Join | `apps/api/src/findings_api/analysis/join.py` |
| Measure semantics | `apps/api/src/findings_api/analysis/measure_semantics.py` |
| Review UI | `apps/web/src/app/review/page.tsx` |
| Results UI | `apps/web/src/app/results/page.tsx`, `KeyFindingsContent.tsx` |
| Catalog sync | `apps/api/src/findings_api/catalog/` |

## Tests to run before shipping

```bash
cd apps/api
pytest tests/test_join.py tests/test_charts.py tests/test_ml_suite.py \
       tests/test_worldbank_panel.py tests/test_measure_semantics.py \
       tests/test_sessions.py tests/test_descriptive.py -q

cd ../web && npm run build
```

## Secrets (never commit)

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | AI summary + measure semantics inference |
| `FRED_API_KEY` | FRED catalog/ingest |
| `DATABASE_URL` | Postgres in prod; SQLite ok locally |
| `ADMIN_SYNC_TOKEN` | Production catalog sync endpoints |

## What to tell the next agent

> “Read `docs/findings-ai/HANDOFF.md`. Grounded chat, AI budget cap, dataset facts, and WB pagination are done. Next: rotate the FRED key, then deploy (DEPLOY.md). Optionally enable the catalog growth scheduler.”

## Doc index

| Doc | When to read |
|-----|----------------|
| [BUILD_ORDER.md](./BUILD_ORDER.md) | Slice roadmap (many slices now partially done) |
| [DEPLOY.md](./DEPLOY.md) | Vercel + Railway |
| [DATA_SOURCES.md](./DATA_SOURCES.md) | Catalog sources |
| [CATALOG_QA.md](./CATALOG_QA.md) | Quality gates |
| [ANALYSIS.md](./ANALYSIS.md) | Analysis design |
| [ML.md](./ML.md) | ML models and gates |
