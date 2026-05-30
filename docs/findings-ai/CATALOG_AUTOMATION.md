# Catalog automation (Hobby / $5 budget)

Production catalog refresh is **not** live-fetched on search. Metadata is synced on a schedule; **grow** promotes rows to searchable.

## Architecture

| Component | Host | Cost |
|-----------|------|------|
| API + Postgres | Railway | ~$5/mo Hobby (included usage credit) |
| Weekly sync + daily grow | **GitHub Actions** | $0 (within free minutes) |

Do **not** run separate Railway cron services for catalog — they duplicate Docker builds and burn credits.

## Phase 1 — One-time fill (local terminal)

Keep the terminal open until `SYNC_DONE` (~15–30 min with prod caps):

```bash
cd /path/to/asra
./scripts/railway-catalog.sh sync 2>&1 | tee /tmp/prod-sync.log
./scripts/railway-catalog.sh grow
./scripts/catalog-smoke.sh
```

Or trigger GitHub Actions → **Catalog** → **Run workflow** → `sync`, then `grow`.

## Phase 2 — GitHub Actions

Workflow: [`.github/workflows/catalog.yml`](../../.github/workflows/catalog.yml)

| Schedule (UTC) | Job |
|----------------|-----|
| Sun 03:00 | Full sync |
| Daily 04:00 | Grow (~100 rows) |

### Required GitHub secrets

| Secret | Value |
|--------|--------|
| `DATABASE_URL` | Railway Postgres **`DATABASE_PUBLIC_URL`** (not `.internal`) |
| `FRED_API_KEY` | From [FRED API key page](https://fred.stlouisfed.org/docs/api/api_key.html) |

Settings → Secrets and variables → Actions → New repository secret.

Or run locally for URLs/instructions:

```bash
npm run setup:github-catalog
```

## Phase 3 — Prod catalog limits

Set on **Railway `asra`** (and mirrored in the GitHub workflow `env` block):

```env
CKAN_SYNC_MAX_INDEXED=3000
CKAN_SYNC_MAX_PACKAGES=300
WB_SYNC_MAX_INDEXED=5000
FRED_SYNC_MAX_SERIES=200
CATALOG_PROBE_BATCH_SIZE=100
CATALOG_SYNC_INTERVAL_HOURS=0
CATALOG_PROBE_INTERVAL_HOURS=0
```

Local dev can keep larger caps in root `.env` (e.g. 10k indexed).

## Phase 4 — Railway cleanup

Railway project should only have:

- **asra** — API (Dockerfile + entrypoint, `CATALOG_JOB` unset → web)
- **Postgres**

Remove legacy `catalog-sync` / `catalog-grow` services if present:

```bash
npx railway service delete catalog-sync --yes
npx railway service delete catalog-grow --yes
```

## Phase 5 — Monitor

```bash
npm run smoke:catalog          # health + search + admin breakdown
npm run health:catalog:prod    # admin catalog stats only
```

GitHub → **Actions** → **Catalog** for job pass/fail.

Railway → **Usage** to stay within $5 included credit.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|--------|-----|
| `catalog_count: 0` after aborted sync | Sync deletes portal rows first | Re-run full sync to completion |
| GitHub Action DB error | Used `postgres.railway.internal` URL | Set secret to `DATABASE_PUBLIC_URL` |
| Search empty, high total | Metadata synced, not probed | Run `grow` or wait for daily job |
| Local sync stops early | Shell closed / laptop sleep | Use GitHub Actions or keep terminal open |
