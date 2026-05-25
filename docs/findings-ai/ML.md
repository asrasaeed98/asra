# ML — Phase 1 Option A

## In scope

| Task | Method | When |
|------|--------|------|
| Clustering | K-means + silhouette | ≥2 numeric features, n ≥ 50 (gate ≥1000 for session) |
| Anomalies | Isolation Forest | n ≥ 100 |

## Out of scope

- Supervised prediction, AutoML, deep learning, NLP, forecasting

## Outputs

1. **Cluster profile** — size, means of top numeric columns per cluster
2. **PCA 2D scatter** — colored by cluster
3. **Representative rows** — closest to centroids (computed distances)
4. **Anomaly card** — top rows by anomaly score

## Labels

Use **Cluster 1 (n=12,400)** — not invented names as facts. Optional AI nickname labeled “suggested.”

## CV / reproducibility

`random_state=42` on all sklearn fits.

## Max ML load

At most **2 ML finding types** per session alongside classical stats.
