# Presentation — results

## Layout order

1. Provenance + row/sample disclosure
2. **Executive summary (AI-generated)** — auto after analysis
3. **Key results (computed)** — top 5–8 finding cards
4. Charts (max 6), linked by `finding_id`
5. More findings + filters
6. Chat panel

## AI summary pipeline

- Input: top 5 Finding JSON + optional `user_intent`
- Model: Haiku (summary) recommended
- Validate: reject output with numbers not in input
- Fallback: template bullets or hide AI block with banner

## Chart map (deterministic)

| finding.type | Chart |
|--------------|-------|
| correlation | Scatter + trend |
| group_comparison | Box or bar |
| chi_square | Heatmap / stacked bar |
| time_trend | Line |
| join_report | Matched vs unmatched bar |
| kmeans_cluster | PCA scatter by cluster |
| anomaly_top_rows | Table + score scatter |

## Template headline (no LLM)

Example: `Strong negative association: unemployment_rate vs median_income (Spearman r = -0.62, n = 48)`

## User controls

- Filter findings: All / Statistics / ML
- Show SQL per card
- Optional per-card “Explain” (Haiku)
