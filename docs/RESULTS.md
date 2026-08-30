# Experiment Results

> **Status**: Template — populated after experiment runs.
>
> **Last updated**: _not yet run_

## 1. Service Dependency Graph (SDG)

| Metric | Value |
|---|---|
| Nodes (services) | _TBD_ |
| Edges (dependencies) | _TBD_ |
| Graph density | _TBD_ |
| Avg. in-degree | _TBD_ |
| Avg. out-degree | _TBD_ |

### SDG Sanity Check

_Compare against DeathStarBench paper Fig. 4. Note any discrepancies._

---

## 2. Centrality Rankings

| Rank | Service | Degree | Betweenness | PageRank | Composite Score |
|---|---|---|---|---|---|
| 1 | _TBD_ | | | | |
| 2 | _TBD_ | | | | |
| 3 | _TBD_ | | | | |
| ... | | | | | |

_Full table: `centrality/output/centrality_table.csv`_

---

## 3. Fault Injection Summary

| Statistic | Value |
|---|---|
| Total experiment runs | _TBD_ |
| Services tested | _TBD_ |
| Fault types used | _TBD_ |
| Repetitions per (service, fault) | _TBD_ |
| Total experiment time | _TBD_ |

### Per-Fault-Type Summary

_Average metrics across all services for each fault type._

---

## 4. Correlation Results

### Spearman Correlation Heatmap

_Insert `analysis/plots/correlation_heatmap.png`_

### Key Findings

**Which centrality metric(s) best predict real failure impact?**

_TBD — summarize the strongest correlations (highest |ρ| with p < 0.05)._

**Blast radius measures most correlated with centrality:**

1. _TBD_
2. _TBD_
3. _TBD_

### Statistical Significance

| Centrality Metric | Best Blast Measure | Spearman ρ | p-value | Significant? |
|---|---|---|---|---|
| _TBD_ | | | | |

_Full table: `analysis/output/correlation_results.csv`_

---

## 5. Outlier Analysis

### False Positives

Services with **high centrality** but **low actual blast radius**:

| Service | Centrality Rank | Blast Rank | Explanation |
|---|---|---|---|
| _TBD_ | | | |

### False Negatives

Services with **low centrality** but **high actual blast radius**:

| Service | Centrality Rank | Blast Rank | Explanation |
|---|---|---|---|
| _TBD_ | | | |

### Discussion

_Why do these discrepancies occur? Possible reasons:_
- Caching / redundancy mitigating structurally central failures
- Synchronous single-point-of-failure dependencies not captured by centrality
- Runtime dynamics (load balancing, retries) not reflected in static graph metrics

---

## 6. Limitations & Threats to Validity

1. **Sample size**: The SDG has ~12 services, giving small n for Spearman correlation. Statistical power is limited.
2. **Single benchmark application**: Results may not generalize to all microservice architectures.
3. **Fault types**: We tested crash (kill) and latency injection. Other fault types (Byzantine, data corruption) may yield different results.
4. **Static graph**: The SDG is constructed from a single load window. Different workloads might produce different graphs.
5. **No cascading failure chains**: We inject faults one service at a time. Concurrent failures could have amplified effects.
6. **Resource constraints**: _Document any resource-related limitations encountered during the experiment._

---

## 7. Reproducibility

All experiment data is preserved in:
- `measurement/results/experiment_log.csv` — cumulative log of all runs
- `measurement/results/run_*.json` — per-run detailed data
- `sdg/output/sdg.json` — the constructed graph
- `centrality/output/centrality_table.csv` — centrality metrics
- `analysis/output/correlation_results.csv` — statistical results
- `analysis/plots/` — all generated figures

To reproduce:
```bash
python scripts/run_full_experiment.py
```

See `docs/SETUP.md` for full environment setup instructions.
