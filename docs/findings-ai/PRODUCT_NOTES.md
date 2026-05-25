# Product notes — FunFinds

## Original idea (verbatim intent)

There are many publicly available datasets online. The app provides an easy interface where users search and select datasets (1–2 for Phase 1). After selection, the app automatically runs analysis (statistical models, correlations, clustering) on whitelisted open data, optionally guided by user context. Results show interesting findings with fun, clear visuals. Users can ask questions about the data via chat.

## Locked Phase 1 decisions

| Topic | Decision |
|-------|----------|
| **Name** | FunFinds (display); docs folder `FunFinds` |
| **Data access** | Specific portals only — no arbitrary URLs |
| **Licenses** | Strictest route: CC0, public domain, vetted gov open only |
| **Datasets per run** | 1–2 |
| **Large tables** | User filter preferred; else reproducible random sample (disclosed) |
| **ML** | Option A: K-means + Isolation Forest only |
| **Presentation** | Always: computed findings + AI executive summary (labeled) |
| **LLM** | Anthropic Claude, server-side API key only |
| **Trust** | Numbers from engine/SQL only; AI never invents metrics |

## User priorities

1. Very easy to use.
2. Accurate findings to build trust.
3. Meaningful, easy-to-digest presentation.

## Out of scope (Phase 1)

- Arbitrary URL ingestion, AutoML, deep learning, forecasting
- CC-BY / share-alike datasets
- Supervised prediction ML
- Production billing (optional auth for public deploy)

## Alternates considered

- **OpenFindings**, **DataBrief**, **Claridata** — use if FunFinds domain/trademark blocked.
