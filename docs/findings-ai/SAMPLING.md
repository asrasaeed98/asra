# Sampling and row limits

## Constants (defaults)

| Constant | Value |
|----------|-------|
| `ROW_CAP` | 100,000 |
| `MIN_SAMPLE` | 10,000 |
| `SAMPLE_PCT` | 0.05 (5%) |
| `RANDOM_SEED` | 42 |

## Formula

```text
analysis_n = min(ROW_CAP, max(MIN_SAMPLE, round(SAMPLE_PCT * available_rows)))
```

Example: 1M rows, no filter → 50,000 row sample.

## Tiers

| Rows | UX |
|------|-----|
| ≤ 100,000 | Analyze full table (within byte cap) |
| 100,001 – 1,000,000 | Recommend filter; user chooses filter / sample / both |
| > 1,000,000 | Require filter and/or sample |

## Global floors

| analysis_n | Behavior |
|------------|----------|
| < 50 | Block run |
| 50 – 999 | Descriptive + simple stats; skip ML |
| ≥ 1,000 | ML allowed with caution |
| ≥ 10,000 | Normal pipeline |

## Per-test minimums

See [ANALYSIS.md](./ANALYSIS.md).

## Disclosure (on every affected finding)

> Based on N = {analysis_n} rows (random sample of {total}, seed 42). Rare groups may be underrepresented.

## Stratified sample (optional)

Stratify on detected geo/state column when present.

## DuckDB

Use `TABLE SAMPLE` or bounded `read_csv` — avoid loading full 1M into RAM when sampling.
