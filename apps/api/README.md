# Findings.ai API

FastAPI backend for catalog search, analysis sessions, and grounded chat.

## Setup

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

From repo root, copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY` when using LLM features.

## Run

```bash
uvicorn findings_api.main:app --reload --port 8000
```

Open http://localhost:8000/docs

## Tests

```bash
pytest
```
