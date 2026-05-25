# Architecture — Findings.ai Phase 1

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js (App Router), TypeScript, Tailwind |
| API | Python 3.12, FastAPI |
| Worker | Same codebase; Redis-backed jobs |
| Session analytics | DuckDB (per analysis session) |
| Metadata | PostgreSQL 16 |
| Queue | Redis 7 |
| Object storage | S3-compatible (optional Phase 1 local disk) |
| LLM | Anthropic Claude API |
| Charts | Vega-Lite (JSON specs) |

## High-level diagram

```mermaid
flowchart TB
  Browser[Next.js apps/web]
  API[FastAPI apps/api]
  Worker[Analysis worker]
  PG[(PostgreSQL)]
  Redis[(Redis)]
  Duck[DuckDB per session]
  S3[(Object storage)]
  Anthropic[Anthropic API]
  CKAN[data.gov CKAN]
  Browser --> API
  API --> PG
  API --> Redis
  Redis --> Worker
  Worker --> PG
  Worker --> Duck
  Worker --> S3
  Worker --> Anthropic
  API --> CKAN
```

## Core entities

- **catalog_resources** — searchable metadata (license-filtered at index time)
- **analysis_sessions** — user run: datasets, filters, sample config, status
- **findings** — JSON blobs keyed by `finding_id`
- **chart_specs** — Vega-Lite linked to `finding_id`
- **chat_messages** — role, content, citations payload
- **ai_summaries** — optional column on session

## API sketch

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |
| GET | `/search` | Catalog search |
| GET | `/datasets/{id}` | Preview metadata |
| POST | `/sessions` | Create session, attach 1–2 resources |
| PATCH | `/sessions/{id}` | Filter, sample, join config |
| POST | `/sessions/{id}/run` | Start analysis job |
| GET | `/sessions/{id}/status` | Progress phases |
| GET | `/sessions/{id}/results` | Findings, charts, AI summary |
| POST | `/sessions/{id}/chat` | Grounded chat (SSE stream) |

## Job status payload

```json
{
  "phase": "analyze",
  "substep": "clustering",
  "message": "K-means on 6 numeric columns",
  "percent": 65,
  "estimate_remaining_sec": 45,
  "estimate_range_sec": [30, 90],
  "rows_analyzed": 50000
}
```

## Environment variables

```bash
DATABASE_URL=postgresql://findings:findings@localhost:5432/findings
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL_SUMMARY=claude-haiku-4-5
ANTHROPIC_MODEL_CHAT=claude-sonnet-4-6
DATA_GOV_CKAN_API=https://catalog.data.gov/api/3/action
ROW_CAP=100000
MIN_SAMPLE=10000
SAMPLE_PCT=0.05
RANDOM_SEED=42
CORS_ORIGINS=http://localhost:3000
```

## Security

- API key never exposed to browser
- SQL chat: SELECT-only, table whitelist, timeout 5s, LIMIT 500
- Session ownership check on all session routes

## Deploy (prototype)

- **web:** Vercel → `apps/web`
- **api + worker:** Railway or Render → `apps/api`
- **Postgres + Redis:** managed add-ons or docker-compose locally
