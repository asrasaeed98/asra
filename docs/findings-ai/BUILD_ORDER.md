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

## Definition of done

See [README.md](./README.md#status) success criteria in master plan.
