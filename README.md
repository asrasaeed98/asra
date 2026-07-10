# Asra's Projects

[![CI](https://github.com/asrasaeed98/asra/actions/workflows/ci.yml/badge.svg)](https://github.com/asrasaeed98/asra/actions/workflows/ci.yml)

I'm a builder at heart. I enjoy building fun projects in my free time, experimenting with ideas, trying new tech, and learning as I go. This repo is where those experiments live: real apps, shipped to production, with room to keep tinkering.

**[LinkedIn](https://www.linkedin.com/in/asrasaeed/)** · **[GitHub](https://github.com/asrasaeed98)** 

---

## Findings — public data → analysis → insights

**[findings.site](https://www.findings.site)** · Live product

Search curated open datasets (data.gov, World Bank, FRED, NYC Open Data), run automated statistical analysis, and explore results with charts, an AI summary, and grounded chat.

### AI architecture

- **LLMs never compute metrics** — all numbers come from deterministic analysis (stats, ML, SQL on DuckDB).
- **AI summary only rephrases validated findings** — post-checked against source results.
- **Grounded chat** — answers route through SQL on session data or loaded finding records; out-of-scope questions get template refusals.
- **Cost-aware model tiering** — Haiku for summaries, Sonnet for chat; monthly API budget cap in production.

|           |                                                             |
| --------- | ----------------------------------------------------------- |
| **Web**   | Next.js 15, TypeScript, Tailwind                            |
| **API**   | Python 3.12, FastAPI                                        |
| **Data**  | PostgreSQL (catalog), DuckDB (per-session analytics), Redis |
| **AI**    | Anthropic Claude (server-side only)                         |
| **Tests** | 211 pytest cases                                            |

**User flow:** Search → Review → Analyze → Results

**Docs:** [docs/findings-ai/README.md](docs/findings-ai/README.md) · **Code:** `apps/web` · `apps/api`

---

## NYC Tonight — AI concierge for New York *(currently building)*

An agent I'm actively working on. Ask in plain English — *"cheap dinner in Chinatown around 7pm"* or *"something fun near Williamsburg tonight"* — and a Claude tool-use agent searches live data sources, reasons over the results, and replies with a short answer plus result cards (restaurants with a reservation deep-link, events with a ticket link).

### Agent design

- **Tool-use loop** — Claude decides which tools to call; the backend executes the real API calls and feeds results back until Claude returns a final reply.
- **Real data tools** — `search_restaurants` (Yelp Fusion → Google Places fallback), `search_events` (Ticketmaster Discovery), `build_reservation_link` (OpenTable/Resy deep-link).
- **Graceful degradation** — boots with no keys; each unavailable tool reports back so the agent still works with whatever data it can reach.
- **Safe handoff** — reservations are deep-link only, never automated bookings (ToS). Stateless (no DB); short-term context is passed per page session.

|              |                                              |
| ------------ | -------------------------------------------- |
| **Frontend** | React + Vite                                 |
| **Backend**  | Python 3.12, FastAPI                         |
| **AI**       | Anthropic Claude (tool-use loop)             |
| **Data**     | Yelp Fusion, Google Places, Ticketmaster     |
| **Status**   | In active development                        |

**Code:** `nyc-tonight` · **Details:** [nyc-tonight/README.md](nyc-tonight/README.md)

---

## TokenTrim — leaner prompts, lower token cost *(early scaffold)*

Token-efficient prompt compression for developers who pay per API call. Paste a bloated prompt → get three lean rewrites (Concise · Structured · Context-aware).

|            |                                  |
| ---------- | -------------------------------- |
| **Web**    | Next.js 15, TypeScript, Tailwind |
| **AI**     | Anthropic Claude (server-side)   |
| **Status** | Early scaffold — not deployed    |

**Code:** `apps/tokentrim` · **Vision:** [docs/tokentrim/VISION.md](docs/tokentrim/VISION.md)

---

## Repo structure

```
asra/
├── apps/
│   ├── web/              # Findings — Next.js frontend
│   ├── api/              # Findings — FastAPI backend (+ analysis pipeline)
│   └── tokentrim/        # TokenTrim — Next.js app (early scaffold)
├── nyc-tonight/          # NYC Tonight — Claude agent (WIP)
│   ├── backend/          #   FastAPI + tool-use loop + data-source tools
│   └── frontend/         #   React (Vite) chat UI
├── docs/                 # Product & architecture docs
├── scripts/              # Deploy, catalog sync, ops tooling
└── package.json          # dev:web, dev:api, dev:tokentrim, test:api
```

---

## Quick start

**Prereqs:** Docker, Node 20+, Python 3.12

### Findings

```bash
docker compose up -d
cp .env.example .env
# Set ANTHROPIC_API_KEY in .env (required for AI features)

npm run dev:api   # http://127.0.0.1:8000
npm run dev:web   # http://127.0.0.1:3000
```

### NYC Tonight

```bash
# Backend (FastAPI)
cd nyc-tonight/backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && cp .env.example .env   # add your API keys
uvicorn main:app --reload --port 8000

# Frontend (Vite) — in a second terminal
cd nyc-tonight/frontend && npm install && npm run dev   # http://127.0.0.1:5173
```

See [nyc-tonight/README.md](nyc-tonight/README.md) for required API keys and deploy steps.

### TokenTrim

```bash
npm run dev:tokentrim   # http://127.0.0.1:3001
```

---

## Deployment

| Project      | Host              | URL                                                                      |
| ------------ | ----------------- | ------------------------------------------------------------------------ |
| Findings web | Vercel            | [findings.site](https://www.findings.site)                               |
| Findings API | Railway           | [asra-production.up.railway.app](https://asra-production.up.railway.app) |
| NYC Tonight  | Railway + Vercel  | In active development                                                    |

Push to `main` auto-deploys Findings. See [docs/findings-ai/DEPLOY.md](docs/findings-ai/DEPLOY.md).

---

## License

Private portfolio code unless otherwise noted. Contact via [LinkedIn](https://www.linkedin.com/in/asrasaeed/) or GitHub.
