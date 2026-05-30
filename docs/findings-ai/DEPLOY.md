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
4. After deploy: set up catalog automation — see **[CATALOG_AUTOMATION.md](./CATALOG_AUTOMATION.md)** (GitHub Actions weekly sync + daily grow; fits Hobby ~$5/mo)

Quick one-time fill from your machine:

```bash
./scripts/railway-catalog.sh sync
./scripts/railway-catalog.sh grow
npm run smoke:catalog
```

See [DATA_SOURCES.md](./DATA_SOURCES.md) for scaling toward large catalogs (100k–1M metadata rows).

## Local vs cloud DB

- Local: `docker compose up -d` + `.env` from `.env.example`
- Cloud: Railway Postgres URL replaces `DATABASE_URL`

## Post-deploy smoke test

1. `GET /health` → ok
2. `POST /admin/sync` → indexed rows > 0
3. `GET /search?q=gdp` → results with `source_url` and `attribution_text`
4. Open Vercel URL → search page loads
