# Asra's Projects

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

*Home — search public datasets and start an analysis*

*Results — AI-generated summary (labeled) and grounded Q&A over session data*

**Docs:** [docs/findings-ai/README.md](docs/findings-ai/README.md) · **Code:** `apps/web` · `apps/api`

---

## TokenTrim — leaner prompts, lower token cost *(in development)*

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
│   ├── api/              # Findings — FastAPI backend
│   └── tokentrim/        # TokenTrim — Next.js app (WIP)
├── docs/
│   ├── findings-ai/      # Findings product & architecture docs
│   ├── tokentrim/        # TokenTrim vision
│   └── screenshots/      # README screenshots
├── scripts/              # Deploy, catalog sync, ops tooling
└── package.json          # dev:web, dev:api, dev:tokentrim, test:api
```

---

## Quick start (Findings, local)

**Prereqs:** Docker, Node 20+, Python 3.12

```bash
docker compose up -d
cp .env.example .env
# Set ANTHROPIC_API_KEY in .env (required for AI features)

npm run dev:api   # http://127.0.0.1:8000
npm run dev:web   # http://127.0.0.1:3000
```

### TokenTrim (local)

```bash
npm run dev:tokentrim   # http://127.0.0.1:3001
```

---

## Deployment


| Service      | Host    | URL                                                                      |
| ------------ | ------- | ------------------------------------------------------------------------ |
| Findings web | Vercel  | [findings.site](https://www.findings.site)                               |
| Findings API | Railway | [asra-production.up.railway.app](https://asra-production.up.railway.app) |


Push to `main` auto-deploys Findings. See [docs/findings-ai/DEPLOY.md](docs/findings-ai/DEPLOY.md).

---

## License

Private portfolio code unless otherwise noted. Contact via [LinkedIn](https://www.linkedin.com/in/asrasaeed/) or GitHub.
