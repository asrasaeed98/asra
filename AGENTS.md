# AGENTS.md — Findings ops & codebase guide

**Read this file first** before exploring the repo. It covers production health, structure, logs, sessions, and the commands agents use most often.

Product: **Findings** (public-data search → analysis → results + grounded chat). Docs folder `docs/findings-ai/` still uses legacy name **FunFinds** in places.

---

## URLs

| Environment | Web | API | API docs |
|-------------|-----|-----|----------|
| **Production** | https://asra-eight.vercel.app | https://asra-production.up.railway.app | https://asra-production.up.railway.app/docs |
| **Local** | http://127.0.0.1:3000 (or 3002 if using `next start`) | http://127.0.0.1:8000 | http://127.0.0.1:8000/docs |

**Hosting:** Web on Vercel (project **asra**, root `apps/web`). API + Postgres on Railway (project **faithful-radiance**, service **asra**). Catalog automation via GitHub Actions ([catalog workflow](.github/workflows/catalog.yml)).

---

## Repo structure

```
asra/
├── apps/
│   ├── web/                 # Next.js 15 (App Router), TypeScript, Tailwind
│   │   └── src/app/         # Routes: /, /search, /explore, /review, /analyze, /results
│   └── api/                 # FastAPI + analysis pipeline
│       └── src/findings_api/
│           ├── routers/     # health, search, guided, datasets, sessions, admin
│           ├── catalog/     # CKAN, World Bank, FRED, NYC sync + probe
│           ├── ingest/      # Download → DuckDB per session
│           ├── analysis/    # Stats, ML, charts, AI summary, chat
│           └── guided/      # paths.yaml, topics.yaml
├── scripts/                 # Deploy, catalog, prod smoke, runs snapshot
├── docs/findings-ai/        # Product + architecture docs (deep dives)
├── docker-compose.yml       # Local Postgres 16 + Redis 7
├── .env.example             # All env vars (copy → .env; never commit)
└── package.json             # Root npm scripts (dev:web, dev:api, smoke:catalog, …)
```

**Stack:** Next.js · FastAPI · PostgreSQL (metadata) · DuckDB (per-session analytics) · Redis (queue, later) · Anthropic Claude (summary + chat).

---

## Local dev

**Prereqs:** `docker compose up -d`, `.env` at repo root (from `.env.example`), `ANTHROPIC_API_KEY` for AI features.

```bash
# Terminal 1 — API (port 8000)
npm run dev:api
# needs apps/api/.venv — install once: cd apps/api && python -m venv .venv && pip install -e ".[dev]"

# Terminal 2 — Web (port 3000)
npm run dev:web
# needs apps/web/node_modules — install once: cd apps/web && npm install
```

**If web is flaky in dev:** build + production server on 3002 (see `docs/findings-ai/HANDOFF.md`).

**Catalog:** Auto-syncs on first API start when DB is empty. Manual: `npm run sync:catalog` or `npm run sync:catalog:cli`.

**Tests:** `npm run test:api` (pytest in `apps/api`).

---

## Health checks (run these first)

### Production

```bash
# API liveness + catalog size
curl -s https://asra-production.up.railway.app/health | python3 -m json.tool

# Search smoke
curl -s "https://asra-production.up.railway.app/search?q=gdp&limit=3" | python3 -m json.tool

# Web pages
curl -s -o /dev/null -w "home: %{http_code}\n" https://asra-eight.vercel.app/
curl -s -o /dev/null -w "search: %{http_code}\n" https://asra-eight.vercel.app/search

# Full post-deploy checklist
npm run finish:deploy -- https://asra-eight.vercel.app
# or catalog-only:
npm run smoke:catalog
```

Expected `/health` shape:

```json
{
  "status": "ok",
  "service": "findings-api",
  "version": "0.1.0",
  "app_name": "Findings",
  "catalog_count": <number>
}
```

### Local

```bash
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
curl -s -o /dev/null -w "web: %{http_code}\n" http://127.0.0.1:3000/search
```

If unreachable: nothing is listening — start `npm run dev:api` and `npm run dev:web`. Check ports: `lsof -i :8000 -i :3000`.

---

## Logs

| Where | How |
|-------|-----|
| **Local API** | Stdout in terminal running `npm run dev:api` (uvicorn `--reload`). Key loggers: `findings_api.ingest`, `findings_api.analysis.runner`, `findings_api.catalog`. |
| **Production API** | Railway dashboard → service **asra** → Logs, or CLI: `npx railway logs --service asra` (requires `npx railway link` to project **faithful-radiance**). |
| **Production Web** | Vercel dashboard → project **asra** → Logs / Deployments. |
| **Catalog automation** | GitHub Actions → workflow **Catalog** (weekly sync Sun 03:00 UTC, daily grow 04:00 UTC). |

**Useful log patterns:** `Analysis failed for`, `Ingest failed for`, `Catalog sync`, `Progress ticker failed`, `Marked N stale session(s)`.

---

## Live sessions (analysis runs)

User flow: **Search/Explore → Review → Analyze → Results**. Each run is an `analysis_sessions` row.

### Session lifecycle

| status | Meaning |
|--------|---------|
| `created` | Session created, not started |
| `ingesting` | Downloading datasets |
| `ready` | Ingest done; waiting for analysis run |
| `analyzing` | Stats / ML / AI summary running |
| `complete` | Results available |
| `failed` | Error or stale timeout |

**Stale recovery:** Active sessions (`ingesting`, `analyzing`) with no heartbeat for **25 min** (60 min if `config.large_download`) are marked `failed` on status poll or API startup (`session_recovery.py`).

### Session API (no auth for user sessions)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/sessions` | Create session (1–2 resource IDs) |
| GET | `/sessions/{id}` | Full detail + catalog metadata |
| PATCH | `/sessions/{id}` | Filters, sample, join config |
| POST | `/sessions/{id}/run` | Start ingest + analysis |
| GET | `/sessions/{id}/status` | Poll progress (`phase`, `percent`, `message`, `estimate_remaining_sec`) |
| GET | `/sessions/{id}/results` | Findings, charts, AI summary, chat state |
| POST | `/sessions/{id}/chat` | Grounded Q&A (after `complete`) |

**Inspect one session (prod or local):**

```bash
SESSION_ID="<uuid>"
curl -s "https://asra-production.up.railway.app/sessions/${SESSION_ID}/status" | python3 -m json.tool
curl -s "https://asra-production.up.railway.app/sessions/${SESSION_ID}" | python3 -m json.tool
```

### Admin: recent runs snapshot

Requires `ADMIN_SYNC_TOKEN` in root `.env` (same token as Railway `ADMIN_SYNC_TOKEN`).

```bash
# Last 50 sessions + AI usage by month
./scripts/prod-runs-snapshot.sh

# Or direct API
curl -s "https://asra-production.up.railway.app/admin/runs/snapshot?limit=50" \
  -H "Authorization: Bearer $ADMIN_SYNC_TOKEN" | python3 -m json.tool
```

Snapshot includes: `summary.by_status`, per-session `status`, `phase`, `error`, `duration_sec`, and `api_usage` (Anthropic spend).

---

## Catalog ops

| Task | Local | Production |
|------|-------|------------|
| Sync metadata | `npm run sync:catalog` | `npm run sync:catalog:prod` |
| Grow catalog | `npm run grow:catalog` | `npm run grow:catalog:prod` |
| Probe downloads | `npm run probe:catalog` | `npm run probe:catalog:prod` |
| Catalog health | — | `npm run health:catalog:prod` |
| Smoke test | `API_URL=http://127.0.0.1:8000 npm run smoke:catalog` | `npm run smoke:catalog` |

**Admin endpoints** (Bearer `ADMIN_SYNC_TOKEN`):

- `POST /admin/sync` — full catalog sync
- `POST /admin/catalog/probe-batch?limit=N` — verify pending rows
- `GET /admin/catalog/health` — ingestible vs blocked breakdown
- `GET /admin/runs/snapshot?limit=N` — recent sessions + AI usage

**CORS:** After new Vercel URL, run `./scripts/railway-cors.sh https://YOUR-APP.vercel.app`.

---

## Key environment variables

See `.env.example` for full list. Critical ones:

| Variable | Where | Purpose |
|----------|-------|---------|
| `DATABASE_URL` | API | Postgres connection |
| `ANTHROPIC_API_KEY` | API | AI summary + chat (never expose to browser) |
| `ADMIN_SYNC_TOKEN` | API + local `.env` | Protects `/admin/*` |
| `CORS_ORIGINS` | API (Railway) | Must include Vercel URL |
| `NEXT_PUBLIC_API_URL` | Web (Vercel build-time) | API base URL |
| `NEXT_PUBLIC_APP_NAME` | Web | Display name (`Findings`) |

**Local web default API:** `http://127.0.0.1:8000` (set in `apps/web/next.config.ts` when not on Vercel).

---

## Git & deploy

- **Remote:** `asrasaeed98/asra` on GitHub
- **Commit email:** Always `asra.saeed@outlook.com` / `Asra Saeed` (Vercel blocks other emails). See `.cursor/rules/git-commit-email.mdc`.
- **Deploy web:** Push to `main` → Vercel auto-deploys `apps/web`
- **Deploy API:** Push to `main` → Railway auto-deploys `apps/api`
- **Post-deploy:** `npm run finish:deploy -- https://asra-eight.vercel.app`

---

## Common issues

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Local API unreachable | Dev server not running | `npm run dev:api`; ensure `docker compose up -d` |
| Local search empty | Empty catalog | Wait for startup sync or `npm run sync:catalog` |
| Web CORS errors on prod | Missing Vercel origin | `./scripts/railway-cors.sh <vercel-url>` |
| Session stuck then failed | Stale timeout or Railway restart | Check `/sessions/{id}` `error`; re-run from search |
| `401` on admin routes | Missing/wrong token | Set `ADMIN_SYNC_TOKEN` in `.env` |
| Web 500 locally | Stale `.next` cache | `rm -rf apps/web/.next && npm run build` |

---

## Where to dig deeper

| Topic | Doc |
|-------|-----|
| Architecture & API sketch | `docs/findings-ai/ARCHITECTURE.md` |
| Deploy & Railway/Vercel | `docs/findings-ai/DEPLOY.md` |
| Recent session handoff notes | `docs/findings-ai/HANDOFF.md` |
| Catalog automation | `docs/findings-ai/CATALOG_AUTOMATION.md` |
| UX wizard flow | `docs/findings-ai/UX_FLOW.md` |
| Chat / AI | `docs/findings-ai/CHAT.md` |
| Full doc index | `docs/findings-ai/README.md` |

**Key source files:**

- API entry: `apps/api/src/findings_api/main.py`
- Sessions: `apps/api/src/findings_api/routers/sessions.py`
- Admin/ops: `apps/api/src/findings_api/routers/admin.py`
- Web API client: `apps/web/src/lib/api.ts`
- Session recovery: `apps/api/src/findings_api/session_recovery.py`
