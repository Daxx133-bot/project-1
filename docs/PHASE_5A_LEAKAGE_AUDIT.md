# Phase 5A Critical Leakage Check

## Audit Findings
I have audited the analysis scripts, particularly `analysis/correlation_analysis.py` and `centrality/hybrid_weight_optimizer.py`.

### 1. Target Leakage Identified
**CRITICAL LEAKAGE FOUND**: `centrality/hybrid_weight_optimizer.py` optimizes the novel centrality metric's weights (`w1`, `w2`, `w3`) using the *exact same* experimental observations (e.g., `error_rate_delta` in `experiment_log.csv`) that `correlation_analysis.py` subsequently evaluates it against.

**Why this is leakage**:
- The optimizer grid-searches weights specifically to maximize the Spearman rank correlation against the experimental `blast_measure` on the entire dataset.
- The resulting metric (`hybrid_criticality`) is then fed into `correlation_analysis.py`, which tests for statistical significance (p-values) against the *exact same data*.
- This creates circular reasoning/target leakage (training on the test set). The resulting p-values for the hybrid metric will be artificially inflated and statistically invalid, as the metric was explicitly tuned to maximize performance on that specific data.

### 2. Architecture Cross-Contamination
If the optimizer is run on one architecture (e.g., Social Network) and the resulting weights are used to evaluate the other architecture (e.g., Hotel Reservation), it is a valid out-of-sample test. However, if the weights are optimized over the entire combined dataset or optimized per-architecture and reported together, it constitutes severe data leakage.

### Recommendation for Phase 5B
Do not use `hybrid_weight_optimizer.py` on the same dataset used for evaluation, or split the dataset (e.g., use SN to optimize weights, and HR to evaluate).
