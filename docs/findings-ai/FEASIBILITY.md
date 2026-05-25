# Feasibility — curated open data vs “anything online”

## Phase 1 is feasible

Auto-analysis on **tabular open data with documented metadata and permissive license** is feasible with size caps and a rules engine.

## What size limits fix

- Server memory and download time
- Job duration and LLM cost (profile aggregates, not full CSV in prompts)

## What size limits do not fix

| Blocker | Why |
|---------|-----|
| Format heterogeneity | HTML, PDF, nested JSON, ZIP bundles need custom ETL per source |
| Unstable schema | Columns change without notice |
| Semantic ambiguity | Columns like `value`, `id` need domain context |
| Multi-table packages | Wrong table choice without metadata |
| Joining arbitrary datasets | No shared keys → unreliable merges |
| License ≠ public | Visible download ≠ unrestricted use |
| Access mechanics | Rate limits, keys, broken links |

## Phase 1 avoids these

- Whitelist portals (CKAN API)
- License gate at **index** and **ingest**
- 1–2 datasets, user-confirmed join keys
- Schema from portal + validate on parse
- Row cap + disclosed sampling

## Honest limits

- Automated test **choice** can be wrong for edge cases
- **Numbers** match ingested copy; **causation** is never implied
- Source data may contain errors from publishers
