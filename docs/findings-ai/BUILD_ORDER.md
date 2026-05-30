# Build order — Phase 1

## Slice 0 — Documentation ✅

All files in `docs/findings-ai/`.

## Slice 1 — Monorepo scaffold ✅

- [x] `apps/web` — Next.js 15 App Router, Tailwind
- [x] `apps/api` — FastAPI, health check, CORS
- [x] `docker-compose.yml` — Postgres 16, Redis 7
- [x] `.env.example` — `ANTHROPIC_API_KEY`, `DATABASE_URL`, etc.
- [x] Root `package.json` workspaces (optional) or README run instructions

## Slice 2 — Catalog and search ✅

- [x] data.gov Catalog API + World Bank sync
- [x] License normalization + reject unknown
- [x] `catalog_resources` + search
- [x] `GET /search` + search page UI

## Slice 3 — Session and ingest ✅

- [x] `POST /sessions` with 1–2 resource IDs
- [x] Download → DuckDB ingest
- [x] Review UI: filter, sample, join keys, ML toggle

## Slice 4 — Analysis engine

- [ ] `profile` → `selector` → `runner` → Finding JSON
- [ ] Stats tests + ML (k-means, isolation forest)
- [ ] Rank and cap findings (5–8)

## Slice 5 — Progress and jobs

- [ ] Worker + Redis queue
- [ ] `GET /sessions/{id}/status` phase/substep/estimate
- [ ] Analyze page stepper

## Slice 6 — Results UI

- [ ] Finding cards + Vega-Lite charts (max 6)
- [ ] Provenance bar, sample disclosure

## Slice 7 — AI summary

- [x] Finalize: Anthropic Haiku summary from top Finding JSON + digit validation + template fallback
- [ ] Numeric validation + fallback template

## Slice 8 — Chat

- [ ] Orchestrator: SQL path + finding path
- [ ] `POST /sessions/{id}/chat` streaming
- [ ] Chat panel + Source expander

## Slice 9 — Hardening

- [ ] Rate limits, token logging, error states
- [ ] Stuck-job messaging

## Slice 10 — Deploy

- [ ] Staging on Vercel + Railway/Render
- [ ] Smoke test script

## Slice 11 — Join hygiene (Phase 1.5 backlog)

Improve cross-dataset correlation success **without** unsafe joins or neural “magic” correlation. Full detail: [HANDOFF.md § Join hygiene](./HANDOFF.md#p2--join-hygiene--cross-dataset-correlation-backlog).

### Phase 0 — Measure first

- [ ] Join outcome telemetry (ok / fail reason / matched_rows) per session
- [ ] Baseline dashboard or admin endpoint before building matchers

### Phase 1 — Lookup normalization (recommended first ship)

- [ ] Country name → ISO3 lookup (static table / `pycountry`)
- [ ] US state name ↔ abbreviation ↔ FIPS normalization
- [ ] Apply in join overlap scoring (`join.py`) on geo key columns
- [ ] Review UI: match rate, unmatched examples, “normalized key” disclosure
- [ ] Tests: `test_join_normalization.py` (USA/United States, California/CA)

### Phase 2 — Product & optional fuzzy

- [ ] Curated “pairs that work” hints in search / review (e.g. WB macro pairs)
- [ ] Optional fuzzy string match on geo keys (confidence gate; no auto-recommend below threshold)
- [ ] Ecological correlation card when only country-level grain aligns (explicit caveat)

### Explicitly not in scope

- Probabilistic record linkage (Fellegi–Sunter) as default
- Neural / embedding entity matching without human review
- Cross-dataset correlation without row alignment

## Slice 12 — Guided paths (question-first discovery)

Dual entry: **Explore** (guided) + **Search** (browse). Same Review → Analyze → Results pipeline.

Full plan: [GUIDED_PATHS.md](./GUIDED_PATHS.md).

### 12a — MVP

- [x] Curated path registry (`paths.yaml`) + 11 example paths / 5 topics
- [x] `GET /guided/suggest`, `GET /guided/topics`, `GET /guided/paths`
- [x] `/explore` page + home fork (Ask a question / Browse datasets)
- [x] Review pre-fill: `intent`, `pair` → join hint
- [x] Search quality ranking (`quality_score`, `match_reason`) for browse users
- [x] Expanded World Bank `CURATED_INDICATORS` (+6 macro series)
- [ ] Smoke-test every path in CI against live catalog

### 12b — Polish

- [x] Explore UI de-crowding (compact cards, topic dropdown, collapsible extras)
- [ ] Starter collections on search empty state
- [ ] Funnel metrics (guided vs browse)

### 12c — Later

- [ ] Guarded LLM query expansion; join-aware pair badges (with Slice 11)

## Definition of done

See [README.md](./README.md#status) success criteria in master plan.
