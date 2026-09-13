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

## Agent Lab — learn agents with NYC Tonight

Interactive lab for learning how AI agents work. Chat with an NYC concierge agent while Lesson 1 notes explain the tool-use loop in plain language. Clone-and-run is free: Groq or Ollama for the LLM; NYC Open Data + Open-Meteo for tools (optional Ticketmaster for live events).

### Agent design

- **Tool-use loop** — the model chooses tools; the backend runs them and feeds results back until a final reply (with a structured `trace` for teaching).
- **Free data tools** — `search_restaurants` (NYC Open Data), `get_weather` (Open-Meteo), `search_events` (Ticketmaster or fixtures), `build_reservation_link` (OpenTable/Resy deep-link).
- **Learning UI** — notes left, chat center, “What’s happening” right; hamburger for lessons (Lesson 1 shipped).
- **Safe handoff** — reservations are deep-link only. Stateless; short-term context in the browser.

|              |                                                          |
| ------------ | -------------------------------------------------------- |
| **Frontend** | React + Vite                                             |
| **Backend**  | Python 3.12, FastAPI                                     |
| **AI**       | Groq (free tier) or Ollama — tool-use loop               |
| **Data**     | NYC Open Data, Open-Meteo, Ticketmaster (optional)       |
| **Status**   | In active development                                    |

**Code:** `nyc-tonight` · **Details:** [nyc-tonight/README.md](nyc-tonight/README.md)

---

## Repo structure

```
asra/
├── apps/
│   ├── web/              # Findings — Next.js frontend
│   └── api/              # Findings — FastAPI backend (+ analysis pipeline)
├── nyc-tonight/          # Agent Lab — tool-use agent (WIP)
│   ├── backend/          #   FastAPI + tool-use loop + data-source tools
│   └── frontend/         #   React (Vite) chat UI
├── docs/                 # Product & architecture docs
├── scripts/              # Deploy, catalog sync, ops tooling
└── package.json          # dev:web, dev:api, test:api
```

---

## Deployment

| Project      | Host              | URL                                                                      |
| ------------ | ----------------- | ------------------------------------------------------------------------ |
| Findings web | Vercel            | [findings.site](https://www.findings.site)                               |
| Findings API | Railway           | [asra-production.up.railway.app](https://asra-production.up.railway.app) |
| Agent Lab    | Railway + Vercel  | In active development                                                    |

Push to `main` auto-deploys Findings. See [docs/findings-ai/DEPLOY.md](docs/findings-ai/DEPLOY.md).

---

## License

Private portfolio code unless otherwise noted. Contact via [LinkedIn](https://www.linkedin.com/in/asrasaeed/) or GitHub.
