# Accuracy and trust

## Golden rules

1. LLM **never** produces metrics (r, p, means, counts).
2. Analysis engine owns all numbers in Finding JSON.
3. Charts query same DuckDB tables as findings.
4. AI summary only rephrases Finding JSON; post-validate digits.
5. Chat: execute SQL or load Finding before narrative.
6. Store `sql`, `method`, `n`, `engine_version` on each finding.

## Chat grounded modes

| Mode | Source |
|------|--------|
| Factual | SQL → scalar/table in response |
| Explain finding | Finding JSON by id |
| Out of scope | Template refusal, no guess |

## SQL guardrails

- SELECT only
- Whitelisted session tables
- No multi-statement; 5s timeout; LIMIT 500

## UI

- **Computed results** — authoritative block
- **Executive summary (AI-generated)** — separate labeled section
- Collapsible **Source** (SQL or finding id)

## What we guarantee

- Displayed metrics match code run on declared row set (full or sample).

## What we do not guarantee

- “Best” statistical test for every domain
- Causal interpretation
