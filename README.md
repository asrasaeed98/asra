# asra

Monorepo for apps and experiments.

## Findings.ai (Phase 1)

**Findings.ai** — search curated public datasets, run trustworthy analysis, and explore results with visuals, an AI summary, and grounded chat.

- **Documentation:** [docs/findings-ai/README.md](docs/findings-ai/README.md)
- **Web app:** `apps/web`
- **API:** `apps/api`

### Quick start (local)

```bash
docker compose up -d
cp .env.example .env
# Set ANTHROPIC_API_KEY in .env

cd apps/api && pip install -e ".[dev]" && uvicorn findings_api.main:app --reload --port 8000
cd apps/web && npm install && npm run dev
```

- Web: http://localhost:3000  
- API: http://localhost:8000/docs  
