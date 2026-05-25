# Build order — Phase 1

## Slice 0 — Documentation ✅

All files in `docs/findings-ai/`.

## Slice 1 — Monorepo scaffold

- [ ] `apps/web` — Next.js 15 App Router, Tailwind
- [ ] `apps/api` — FastAPI, health check, CORS
- [ ] `docker-compose.yml` — Postgres 16, Redis 7
- [ ] `.env.example` — `ANTHROPIC_API_KEY`, `DATABASE_URL`, etc.
- [ ] Root `package.json` workspaces (optional) or README run instructions

## Slice 2 — Catalog and search

- [ ] CKAN `package_search` / `package_show` sync job
- [ ] License normalization + reject unknown
- [ ] Postgres `catalog_resources` + FTS
- [ ] `GET /search` + search page UI

## Slice 3 — Session and ingest

- [ ] `POST /sessions` with 1–2 resource IDs
- [ ] Download → DuckDB ingest
- [ ] Review UI: filter, sample, join keys, ML toggle

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

- [ ] Finalize: Anthropic Haiku/Sonnet summary from Finding JSON
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
