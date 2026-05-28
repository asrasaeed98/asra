# Deploy — prototype (Vercel + Railway)

## Recommended layout

| Service | Host | Path |
|---------|------|------|
| Web (Next.js) | [Vercel](https://vercel.com) | `apps/web` |
| API (FastAPI) | [Railway](https://railway.app) | `apps/api` |
| Postgres | Railway plugin | — |
| Redis | Railway plugin (later worker) | — |

## Vercel (web)

1. Import GitHub repo `asrasaeed98/asra`
2. Root directory: **`apps/web`**
3. Environment: `NEXT_PUBLIC_API_URL=https://<your-railway-api>.up.railway.app`
4. Optional: `NEXT_PUBLIC_APP_NAME=FunFinds`

## Railway (API)

1. New service from repo, root: **`apps/api`**
2. Start command: `uvicorn findings_api.main:app --host 0.0.0.0 --port $PORT`
3. Variables:
   - `DATABASE_URL` (Postgres from Railway)
   - `REDIS_URL`
   - `ANTHROPIC_API_KEY` (secret)
   - `CORS_ORIGINS=https://<your-vercel-app>.vercel.app`
4. After deploy: run initial catalog sync (see **Catalog scheduler** below)

## Catalog scheduler

The catalog is **not** live-fetched on every search. Refresh it on a schedule (recommended: **weekly sync**, **daily probe batch**).

### Daily growth (recommended)

**Weekly** refresh metadata, **daily** promote pending rows to searchable:

| Schedule | Command | Purpose |
|----------|---------|---------|
| Weekly | `python -m findings_api.catalog.cli sync` | Re-index metadata from sources |
| Daily | `python -m findings_api.catalog.cli grow` | Probe ~200 pending rows → ingestible |

Or enable in-process schedulers (single API instance):

```env
CATALOG_SYNC_INTERVAL_HOURS=168
CATALOG_PROBE_INTERVAL_HOURS=24
CATALOG_PROBE_BATCH_SIZE=200
```

With `CKAN_SYNC_MAX_INDEXED=10000` and `CKAN_SYNC_MAX_PACKAGES=500`, each weekly sync indexes 10k data.gov rows but only probes 500; daily grow adds ~200 searchable datasets until the backlog clears.

### Option A — CLI (recommended for Railway Cron)

From `apps/api` with production `DATABASE_URL` in env:

```bash
# Full metadata sync (slow; hits upstream APIs)
python -m findings_api.catalog.cli sync

# Verify pending rows in smaller batches (run daily between full syncs)
python -m findings_api.catalog.cli probe --limit 500
```

Or from repo root: `npm run sync:catalog:cli` / `npm run probe:catalog`

Railway: add a **Cron** service with the sync command and the same env vars as the API.

### Option B — HTTP admin endpoints

Set `ADMIN_SYNC_TOKEN`, then:

```bash
curl -X POST -H "Authorization: Bearer $ADMIN_SYNC_TOKEN" \
  https://<api>/admin/sync

curl -X POST -H "Authorization: Bearer $ADMIN_SYNC_TOKEN" \
  "https://<api>/admin/catalog/probe-batch?limit=500"
```

### Option C — In-process interval (single-instance only)

```env
CATALOG_SYNC_INTERVAL_HOURS=168
```

Avoid on multi-replica deployments (duplicate syncs). Prefer Option A.

See [DATA_SOURCES.md](./DATA_SOURCES.md) for scaling toward large catalogs (100k–1M metadata rows).

## Local vs cloud DB

- Local: `docker compose up -d` + `.env` from `.env.example`
- Cloud: Railway Postgres URL replaces `DATABASE_URL`

## Post-deploy smoke test

1. `GET /health` → ok
2. `POST /admin/sync` → indexed rows > 0
3. `GET /search?q=gdp` → results with `source_url` and `attribution_text`
4. Open Vercel URL → search page loads
