# Deploy — prototype (Vercel + Railway)

## Status (prod)

| Component | Status | URL |
|-----------|--------|-----|
| API + Postgres | Live | https://asra-production.up.railway.app |
| Catalog automation | GitHub Actions | [Catalog workflow](../../.github/workflows/catalog.yml) |
| Web (Next.js) | Live (Git → Vercel **asra**) | https://asra-eight.vercel.app |

## Recommended layout

| Service | Host | Path |
|---------|------|------|
| Web (Next.js) | [Vercel](https://vercel.com) | `apps/web` |
| API (FastAPI) | [Railway](https://railway.app) | `apps/api` |
| Postgres | Railway plugin | — |
| Redis | Railway plugin (later worker) | — |

## Finish deployment (web + CORS)

API and catalog automation are done. Remaining step is Vercel:

```bash
npm run setup:vercel-deploy
# After Vercel gives you a URL:
npm run setup:vercel-deploy -- https://YOUR-APP.vercel.app
npm run finish:deploy -- https://YOUR-APP.vercel.app
```

Or `./scripts/railway-cors.sh https://YOUR-APP.vercel.app` alone to allow the web origin on the API.

## Vercel (web)

1. Import GitHub repo `asrasaeed98/asra`
2. Root directory: **`apps/web`**
3. Environment (Production):
   - `NEXT_PUBLIC_API_URL=https://asra-production.up.railway.app`
   - `NEXT_PUBLIC_APP_NAME=Findings` (optional)
4. Deploy, then run `npm run setup:vercel-deploy -- <your-vercel-url>`

## Railway (API)

Already deployed as **asra** on project **faithful-radiance**.

Variables to verify on Railway **asra**:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres (internal URL) |
| `ANTHROPIC_API_KEY` | Analysis / chat |
| `FRED_API_KEY` | Catalog sync |
| `CORS_ORIGINS` | Must include your Vercel URL (see `scripts/railway-cors.sh`) |

Catalog automation: **[CATALOG_AUTOMATION.md](./CATALOG_AUTOMATION.md)** (GitHub Actions; not Railway cron).

Quick catalog ops from your machine:

```bash
./scripts/railway-catalog.sh sync
./scripts/railway-catalog.sh grow
npm run smoke:catalog
./scripts/catalog-bootstrap-prod.sh   # copy local DB catalog → prod
```

See [DATA_SOURCES.md](./DATA_SOURCES.md) for scaling toward large catalogs (100k–1M metadata rows).

## Local vs cloud DB

- Local: `docker compose up -d` + `.env` from `.env.example`
- Cloud: Railway Postgres URL replaces `DATABASE_URL`

## Post-deploy smoke test

```bash
npm run finish:deploy
# with web:
npm run finish:deploy -- https://YOUR-APP.vercel.app
```

Manual checks:

1. `GET /health` → ok
2. `GET /search?q=gdp` → results with `source_url` and `attribution_text`
3. Open Vercel URL → `/search` loads and queries work (no CORS errors)
