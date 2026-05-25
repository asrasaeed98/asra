# Chat — Anthropic, grounded

## Not raw API calls

Orchestrator routes each message:

1. **SQL path** — LLM generates SQL → validate → DuckDB execute → optional phrasing
2. **Finding path** — load Finding by id → rephrase
3. **Refuse** — causation, prediction without data, out-of-session

## Configuration

- `ANTHROPIC_API_KEY` server-only
- Summary: Haiku; Chat/SQL: Sonnet
- Stream SSE to browser
- Last 4–6 turns in context; never full CSV

## Response shape

```json
{
  "reply": "...",
  "grounded": true,
  "citations": { "sql": "...", "finding_ids": [], "columns": [] },
  "data": { "type": "scalar", "value": 0.042 }
}
```

## Rate limits (prototype)

- 20 messages / session
- 30 messages / hour / user (when auth exists)

## Token logging

Log `tokens_in`, `tokens_out` per session for cost tracking.
