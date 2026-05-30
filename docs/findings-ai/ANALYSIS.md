# Analysis engine

## Libraries

- **DuckDB / Polars / Pandas** — data
- **SciPy** — correlations, tests
- **statsmodels** — optional simple OLS
- **scikit-learn** — K-means, Isolation Forest

## Pipeline

```text
profile.py → selector.py → tests/* → runner.py → ranker.py → Finding JSON
```

## Selector rules (not “run all tests”)

| Situation | Tests |
|-----------|-------|
| ≥2 numeric columns | Spearman correlation matrix; top \|r\| pairs |
| 1 numeric + low-card categorical | Group means; Welch t or Kruskal-Wallis / ANOVA |
| Numeric + datetime | Trend / rolling |
| 2 categoricals | Chi-square (or skip if cell counts too low) |
| 2 datasets + confirmed join | Same on joined table + join_report |
| 2 datasets, no join | Per-dataset menu; comparison only if column semantics match (not yet implemented) |

**Defaults:** Spearman when unsure; max **5–8** findings; \|r\| ≥ 0.3 and p < 0.05 (tunable).

**Join improvements (backlog):** Phase 1 = deterministic geo/name normalization before join scoring; Phase 2 = curated joinable pairs + optional fuzzy geo match. See [BUILD_ORDER.md § Slice 11](./BUILD_ORDER.md#slice-11--join-hygiene-phase-15-backlog).

## ML gate

Run ML only if `analysis_n ≥ 1000` and user enabled ML on Review. See [ML.md](./ML.md).

## Finding schema

```json
{
  "id": "f_12",
  "type": "spearman_correlation",
  "columns": ["a", "b"],
  "value": -0.62,
  "p_value": 0.001,
  "n": 48,
  "method": "spearman",
  "caveat": "correlation is not causation",
  "sql": "SELECT ...",
  "datasets": ["ds_a"]
}
```

## Module layout

```text
apps/api/analysis/
  profile.py
  selector.py
  ranker.py
  runner.py
  tests/
    correlation.py
    group_comparison.py
    chi_square.py
    trend.py
    join_report.py
  ml/
    clustering.py
    anomaly.py
```
