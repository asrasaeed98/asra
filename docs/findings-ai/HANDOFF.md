# FunFinds — handoff (resume later)

Use this when you return to the project after a break.

## Open this workspace?

**Yes.** Open the same repo/workspace (`asra` on GitHub). Your code, docs, and branch history live there.

- **Branch with latest work:** `cursor/findings-ai-slice3-ee9c` (slice 3) or `main` after merge
- **PR (draft):** open from slice 3 branch when pushed

## Do you need a handoff doc?

**Not strictly** — planning is already in `docs/findings-ai/`. This file is the **short “start here”** checklist.

| Doc | When to read |
|-----|----------------|
| [HANDOFF.md](./HANDOFF.md) | Resuming after a break (this file) |
| [BUILD_ORDER.md](./BUILD_ORDER.md) | What’s done vs what to build next |
| [UI_DESIGN.md](./UI_DESIGN.md) | Cream/beige + pink accents, loader |
| [DEPLOY.md](./DEPLOY.md) | Vercel + Railway (when ready for users) |
| [README.md](./README.md) | Full doc index |

## Start local dev (every session)

**Terminal 1 — Web (port 3000)**

```bash
cd apps/web
npm install          # first time only
npm run dev
```

Open http://localhost:3000 — if you see `ERR_CONNECTION_REFUSED`, this server is not running.

**Terminal 2 — API (port 8000)**

```bash
cd /workspace   # or repo root
cp .env.example .env   # first time; add ANTHROPIC_API_KEY (never commit .env)
pip install -e "apps/api[dev]"
uvicorn findings_api.main:app --reload --port 8000
```

**Populate search catalog (once per DB)**

```bash
curl -X POST http://localhost:8000/admin/sync
```

**Optional — Postgres/Redis**

```bash
docker compose up -d
# Set DATABASE_URL in .env (Postgres) or keep SQLite default for local
```

## What’s done (Phase 1)

- [x] Planning docs
- [x] FunFinds web wizard UI (cream/beige + pink accents, loader)
- [x] FastAPI: health, search, sessions (stubs), admin sync
- [x] Catalog: data.gov Catalog API + World Bank, license + attribution in UI
- [x] Slice 3 — session + DuckDB ingest + review filters (API + web)
- [ ] **Next:** Slice 4 — analysis engine (`profile` → `selector` → `runner`)

## What to tell the agent next

> “Continue FunFinds slice 4: analysis engine on `main`.”

## Secrets (do not commit)

| Variable | Where |
|----------|--------|
| `ANTHROPIC_API_KEY` | `.env` locally, Railway secrets in cloud |
| Rotate key if it was ever pasted in chat |

## App name

**FunFinds** — `NEXT_PUBLIC_APP_NAME=FunFinds` in `.env`.

## Quick health check

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/search?q=gdp"
curl -I http://localhost:3000/
```

All should respond (not connection refused).
