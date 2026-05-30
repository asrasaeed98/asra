# FunFinds — Phase 1

**FunFinds** helps anyone search curated public datasets, run trustworthy automated analysis, and explore results through clear visuals, an AI summary, and grounded chat.

## Principles

1. **Easy to use** — Search → Review → Analyze → Results (linear wizard).
2. **Accurate** — All metrics come from deterministic code; AI is labeled and supplementary.
3. **Digestible** — Ranked finding cards, rule-based charts, executive AI summary.

## Phase 1 scope

- **Sources:** Whitelisted open-data portals (start [data.gov](https://data.gov) CKAN).
- **Licenses:** Strict allowlist (CC0, public domain, vetted US government open terms).
- **Selection:** 1–2 datasets per session.
- **Analysis:** Classical stats + K-means clustering + Isolation Forest anomalies.
- **Presentation:** Computed findings + automatic Anthropic AI summary.
- **Chat:** Server-side, SQL/findings-grounded (Claude).

## Documentation index

| Doc | Topic |
|-----|--------|
| [PRODUCT_NOTES.md](./PRODUCT_NOTES.md) | Original idea and locked decisions |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Stack, APIs, deployment |
| [BUILD_ORDER.md](./BUILD_ORDER.md) | Implementation slices |
| [FEASIBILITY.md](./FEASIBILITY.md) | Why curated portals vs any URL |
| [DATA_SOURCES.md](./DATA_SOURCES.md) | Portals and CKAN mapping |
| [LICENSING.md](./LICENSING.md) | License gate and attribution |
| [SEARCH.md](./SEARCH.md) | Catalog index and search UX |
| [SAMPLING.md](./SAMPLING.md) | Large data filters and samples |
| [ANALYSIS.md](./ANALYSIS.md) | Stats rules engine |
| [ML.md](./ML.md) | Clustering and anomalies |
| [ACCURACY.md](./ACCURACY.md) | Trust and Finding schema |
| [PRESENTATION.md](./PRESENTATION.md) | Results UI, charts, AI summary |
| [UX_FLOW.md](./UX_FLOW.md) | Wizard and progress copy |
| [GUIDED_PATHS.md](./GUIDED_PATHS.md) | Question-first discovery (dual entry with search) |
| [CHAT.md](./CHAT.md) | Anthropic orchestration |
| [COSTS.md](./COSTS.md) | API and infra estimates |
| [MARKET_RESEARCH.md](./MARKET_RESEARCH.md) | Competitors and positioning |
| [LAUNCH_LEGAL_CHECKLIST.md](./LAUNCH_LEGAL_CHECKLIST.md) | Pre-launch legal hygiene |

## Repo layout (implementation)

```
apps/web/          # Next.js frontend
apps/api/          # FastAPI backend + worker hooks
packages/          # Shared types (optional)
docker-compose.yml # Postgres, Redis
docs/FunFinds/  # This folder
```

## Status

Phase 1 implementation in progress. See [BUILD_ORDER.md](./BUILD_ORDER.md).
