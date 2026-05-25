# UX flow

## Step 1 — Search

- Cart 0/2, preview drawer, starter collections
- Strip: “What happens next” (brief)

## Step 2 — Review

- Dataset summaries, optional intent
- Join key picker (2 datasets)
- Filter / sample controls + live `analysis_n`
- ML checkbox (clustering & anomalies)
- **Estimated time: 2–4 minutes** (range)
- CTA: **Run analysis**

## Step 3 — Analyze (progress)

| Phase | Label |
|-------|--------|
| ingest | Loading your data |
| prepare | Preparing table |
| join | Combining datasets |
| analyze | Running analysis |
| finalize | Building results / Writing summary |

Time: range until ingest done; then “About X left.”

## Step 4 — Results

See [PRESENTATION.md](./PRESENTATION.md).

## Failure copy

- Join too few rows → offer analyze separately
- Ingest timeout → suggest filter or smaller dataset
- ML skipped → banner with reason
