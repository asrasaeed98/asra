# Asra's Projects

Personal monorepo for full-stack apps and experiments. Built and maintained by [Asra Saeed](https://github.com/asrasaeed98).

---

## Projects

### Findings — public data → analysis → insights

**[findings.site](https://www.findings.site)** · Live product

Search curated open datasets (data.gov, World Bank, FRED, NYC Open Data), run automated statistical analysis, and explore results with charts, an AI summary, and grounded chat.

| | |
|---|---|
| **Web** | Next.js 15, TypeScript, Tailwind |
| **API** | Python 3.12, FastAPI |
| **Data** | PostgreSQL (catalog), DuckDB (per-session analytics), Redis |
| **AI** | Anthropic Claude (summary + chat, server-side only) |

**User flow:** Search → Review → Analyze → Results

**Docs:** [docs/findings-ai/README.md](docs/findings-ai/README.md) · **Code:** `apps/web` · `apps/api`

### TokenTrim — same intent, fewer tokens *(in development)*

**Token efficiency first.** Paste a bloated prompt, get three lean rewrites optimized to cut tokens without losing intent. Built for developers who pay per API call.

| | |
|---|---|
| **Web** | Next.js 15, TypeScript, Tailwind |
| **AI** | Anthropic Claude (server-side) |
| **Value prop** | Token-efficient prompt compression |
| **Status** | Early scaffold — not deployed |

**Code:** `apps/tokentrim` · **Vision:** [docs/tokentrim/VISION.md](docs/tokentrim/VISION.md)

---

## Repo structure

```
asra/
├── apps/
│   ├── web/              # Findings — Next.js frontend
│   ├── api/              # Findings — FastAPI backend
│   └── tokentrim/        # TokenTrim — Next.js app
├── docs/
│   ├── findings-ai/      # Findings product & architecture docs
│   └── tokentrim/        # TokenTrim vision & product docs
├── scripts/              # Deploy, catalog sync, ops tooling
├── docker-compose.yml    # Local Postgres + Redis
└── package.json          # Root npm scripts (dev:web, dev:api, test:api, …)
```

Findings uses `apps/web` and `apps/api`. **TokenTrim** is a standalone Next.js app at `apps/tokentrim` (port 3001 locally).

---

## Quick start (Findings, local)

**Prereqs:** Docker, Node 20+, Python 3.12

```bash
docker compose up -d
cp .env.example .env
# Set ANTHROPIC_API_KEY in .env (required for AI features)

# Terminal 1 — API (http://127.0.0.1:8000)
cd apps/api && python -m venv .venv && pip install -e ".[dev]"
npm run dev:api

# Terminal 2 — Web (http://127.0.0.1:3000)
cd apps/web && npm install
npm run dev:web
```

Catalog metadata syncs automatically on first API start when the DB is empty.

**Tests:** `npm run test:api` (211 pytest cases)

### TokenTrim (local)

```bash
# Needs ANTHROPIC_API_KEY in root .env
npm run dev:tokentrim
# → http://127.0.0.1:3001
```

---

## Deployment

| Service | Host | URL |
|---------|------|-----|
| Web | Vercel | [findings.site](https://www.findings.site) |
| API | Railway | [asra-production.up.railway.app](https://asra-production.up.railway.app) |

Push to `main` auto-deploys both. See [docs/findings-ai/DEPLOY.md](docs/findings-ai/DEPLOY.md) for details.

---

## License

Private portfolio code unless otherwise noted. Contact via GitHub for questions.
