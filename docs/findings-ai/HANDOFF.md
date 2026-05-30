# FunFinds — agent handoff (May 2026)

Short “start here” for the next agent or session. Full planning docs remain in `docs/findings-ai/`.

## Repo state

| Item | Value |
|------|--------|
| Branch | `main` (last push: `ba0a917` — May 28 chat/budget/ingest session) |
| Latest work | **May 29 session (uncommitted):** analysis output quality, guided paths (Slice 12a), explore UI polish |
| Prior commits | `ba0a917` chat/budget/facts · `ba06814` analysis/join/ML · `39cadda` catalog |
| Working tree | **Dirty** — API + web + docs changes from May 29; not yet committed |
| App name | **FunFinds** (`NEXT_PUBLIC_APP_NAME=FunFinds`) |
| Tests | `104 passed` in `apps/api` (includes `test_guided*.py`, `test_ranker_joined.py`) |

## Start local dev

**Prereqs:** `.env` at repo root (copy from `.env.example`; never commit). Needs `ANTHROPIC_API_KEY` for AI summaries and measure semantics.

**Terminal 1 — API (port 8000)**

```bash
cd /path/to/asra
pip install -e "apps/api[dev]"   # adds pyyaml for guided paths
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

**If web 500s:** `rm -rf apps/web/.next && npm run build && npx next start …`

**CORS:** `.env.example` includes origins for localhost/127.0.0.1 ports 3000–3002. Match in your `.env`.

**Catalog (once per DB):**

```bash
curl -X POST http://localhost:8000/admin/sync
# or: npm run sync:catalog:cli
```

Re-sync after pulling May 29 changes — six new World Bank curated indicators were added.

**Health check:**

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/search?q=gdp"
curl http://localhost:8000/guided/topics
curl -I http://127.0.0.1:3002/explore
```

## What was done (May 29, 2026 session — uncommitted)

### Analysis output quality (2-dataset / joined panels)

When users run curated pairs (GDP + life expectancy, etc.), correlation should lead the story — not tautological geo group comparisons.

| Area | Change |
|------|--------|
| `selector.py` | Skip geo group-comparison tests on joined 2-measure panels (duplicate “country differs” findings) |
| `tests/group_comparison.py` | Normalized scoring for group comparisons |
| `ranker.py` | Boost joined correlation in ranking; pin primary correlation #1 in display order |
| `runner.py` | Pass joined-panel context into ranker/selector |
| `narrative.py` | Headlines include Spearman *r* + *n*; “Key relationship” badge; grammar fix |
| `ai_summary.py` | Template ordering puts primary correlation first |
| `FindingCard.tsx` | Renders “Key relationship” badge |
| Tests | `test_ranker_joined.py`, updates to `test_selector_geo_dedupe.py` |

**Note:** Re-run old sessions to see new ranking/headlines; stored results are unchanged.

### Guided paths — Slice 12a (question-first discovery)

Dual entry: **Explore** (`/explore`) for question-first users, **Search** (`/search`) for catalog browse. Both converge at Review → Analyze → Results.

| Area | Change |
|------|--------|
| `guided/paths.yaml` | 11 curated paths across 5 topics (wealth-health, energy-access, poverty-gdp, literacy-internet, unemployment-growth, emissions-wealth, water-sanitation, US health/unemployment/inflation/gdp-unemployment) |
| `guided/loader.py` | YAML loader + path lookup |
| `routers/guided.py` | `GET /guided/topics`, `/paths`, `/paths/{id}`, `/suggest` |
| `catalog/search_rank.py` | Quality + relevance scoring for browse search |
| `routers/search.py` | Returns `quality_score`, `match_reason`, `relevance_score` |
| `worldbank_diversity.py` | +6 curated WB indicators |
| `pyproject.toml` | `pyyaml` dependency |
| **Web** | `/explore` page, home fork (Ask a question / Browse datasets), nav Explore + Search, search quality hints, Review pre-fill via `?pair=` + `?intent=` |
| `lib/api.ts` | Guided API client types/functions |
| Tests | `test_guided.py`, `test_guided_api.py` |

Full product spec: [GUIDED_PATHS.md](./GUIDED_PATHS.md). Build checklist: [BUILD_ORDER.md § Slice 12](./BUILD_ORDER.md).

### Explore UI polish (same session)

`/explore` was crowded (question + topic pills + full cards + individual datasets). Redesigned:

- Single-line question input; example questions as inline text links
- **Topic filter** as a dropdown in the pairings section header (not a row of pills)
- Compact pair cards — title, description, dataset line; “Why this example” in `<details>`
- Search results: individual datasets collapsed under “Other individual datasets”
- Unified list for browse mode (“Example analyses”) and search mode (“Best matches”)

## What was done (May 28, 2026 session — committed `ba0a917`)

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

### Done May 29 (was pending)
- ✅ **Joined-panel output quality** — correlation leads; geo group comparisons suppressed on 2-measure joins
- ✅ **Slice 12a guided paths** — `/guided/*` API, `paths.yaml`, `/explore`, search quality ranking, home fork
- ✅ **Explore UI** — less crowded; topic dropdown filter on pairings

### Action required (you)
- **Commit & push** May 29 work when ready (large uncommitted diff across API + web + docs)
- **Rotate the FRED API key** — it was exposed in an error URL earlier; redaction is now in place but rotate to be safe
- **Catalog re-sync** locally (and prod after deploy) for new WB curated indicators

### P1 — Deploy to production

Code on GitHub is behind local work. After commit:

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
| Guided path CI smoke tests | Run every `paths.yaml` entry ingest → join → analyze in CI against live catalog |

### P2 — Join hygiene & cross-dataset correlation (backlog — Slice 11)

When no **safe** join exists, the app analyzes datasets separately — no cross-dataset correlation. Full probabilistic / neural record linkage is **out of scope** (trust risk, wrong fit for macro catalog).

| Phase | Item | Status | Notes |
|-------|------|--------|-------|
| **0** | Join failure telemetry | Not started | Log `% sessions` join ok / fail by reason; optional `GET /admin/join/stats` |
| **1** | **Lookup normalization** | Not started | Country names → ISO3, US states → USPS/FIPS; trim, case-fold |
| **1** | Match disclosure in Review UI | Not started | Match rate, unmatched samples, normalized-key label |
| **2** | Curated “pairs that work” | **Partial** | Shipped via `/explore` + `paths.yaml`; not yet in search cards / join badges |
| **2** | Fuzzy string match on geo keys | Not started | Jaro-Winkler with confidence gate |
| **2** | Ecological correlation fallback | Not started | Country means with explicit caveat card |
| **3** | Cross-dataset semantic comparison | Not started | Suggest join keys — no *r* without alignment |
| — | ~~Full probabilistic linkage~~ | Deferred | Person/address domains |
| — | ~~Neural cross-dataset correlation~~ | Not planned | Does not create observational units |

**Implementation touchpoints:** `join.py`, `ingest/pipeline.py`, Review UI join picker, `tests/test_join_normalization.py`.

### P2 — Guided paths — remaining (Slice 12b/12c)

| Phase | Item | Status |
|-------|------|--------|
| **12a** | Curated paths + `/guided/suggest` + `/explore` UI | ✅ Done |
| **12b** | Search empty-state topic tiles; funnel metrics (guided vs browse) | Not started |
| **12c** | Guarded LLM query expansion; join-aware pair badges | After Slice 11 |

Full spec: [GUIDED_PATHS.md](./GUIDED_PATHS.md).

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
| Guided paths | `apps/api/src/findings_api/guided/paths.yaml`, `guided/loader.py`, `routers/guided.py` |
| Search ranking | `apps/api/src/findings_api/catalog/search_rank.py`, `routers/search.py` |
| Ranker / selector | `apps/api/src/findings_api/analysis/ranker.py`, `selector.py`, `narrative.py` |
| WB download | `apps/api/src/findings_api/ingest/download.py` |
| Ingest pipeline | `apps/api/src/findings_api/ingest/pipeline.py` |
| Profile / runner | `apps/api/src/findings_api/analysis/profile.py`, `runner.py` |
| ML | `apps/api/src/findings_api/analysis/ml/clustering.py` |
| Charts | `apps/api/src/findings_api/analysis/charts.py` |
| Join | `apps/api/src/findings_api/analysis/join.py` |
| Measure semantics | `apps/api/src/findings_api/analysis/measure_semantics.py` |
| Explore UI | `apps/web/src/app/explore/page.tsx` |
| Review UI | `apps/web/src/app/review/page.tsx` |
| Results UI | `apps/web/src/app/results/page.tsx`, `KeyFindingsContent.tsx` |
| Catalog sync | `apps/api/src/findings_api/catalog/` |

## Tests to run before shipping

```bash
cd apps/api
pytest -q   # 104 tests including guided + ranker_joined

cd ../web && npm run build
```

Spot-check manually:
- `/explore` — browse examples, topic filter, search a question, use a pair → Review
- Run a verified pair (wealth-health) → Results should show correlation first with *r* in headline

## Secrets (never commit)

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | AI summary + measure semantics inference |
| `FRED_API_KEY` | FRED catalog/ingest |
| `DATABASE_URL` | Postgres in prod; SQLite ok locally |
| `ADMIN_SYNC_TOKEN` | Production catalog sync endpoints |

## What to tell the next agent

> “Read `docs/findings-ai/HANDOFF.md`. May 29 work is **uncommitted**: joined-panel output quality (ranker/selector/narrative), Slice 12a guided paths (`/explore`, `/guided/*`, search quality ranking), and explore UI polish. **104 API tests pass.** Next: commit & push, catalog re-sync for new WB indicators, rotate FRED key, deploy (DEPLOY.md). Backlog: Slice 11 join normalization, guided path CI smoke tests, Slice 12b polish.”

## Doc index

| Doc | When to read |
|-----|----------------|
| [BUILD_ORDER.md](./BUILD_ORDER.md) | Slice roadmap (12a checked off) |
| [GUIDED_PATHS.md](./GUIDED_PATHS.md) | Explore vs Search product spec |
| [DEPLOY.md](./DEPLOY.md) | Vercel + Railway |
| [DATA_SOURCES.md](./DATA_SOURCES.md) | Catalog sources |
| [CATALOG_QA.md](./CATALOG_QA.md) | Quality gates |
| [ANALYSIS.md](./ANALYSIS.md) | Analysis design |
| [ML.md](./ML.md) | ML models and gates |
