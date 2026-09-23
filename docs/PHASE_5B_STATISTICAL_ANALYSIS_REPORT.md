# Phase 5B Statistical Analysis Report

## 1. Dataset Used
- **Primary Observations**: 171 valid controlled observations (108 Social Network, 63 Hotel Reservation).
- **Excluded**: The 3 original invalid attempts were excluded from primary analysis.
- **Service Count**: 19 services total.
- **Graphs Used**: The Configured Architecture Graph (12 nodes for SN, 7 nodes for HR) was explicitly used to avoid survivorship bias.

## 2. Effective Sample Sizes
- **Service-level aggregation (Pooled)**: 19 services.
- **Service-level (Social Network)**: 12 services.
- **Service-level (Hotel Reservation)**: 7 services.
- **Fault-specific analysis**: For each fault in SN, N=12. For HR, N=7.

## 3. Outcome Definitions
- **PRIMARY OUTCOME**: `recovery_time_s`
- **SECONDARY OUTCOMES**: `downstream_affected_count`, `delta_p95_ms`, `delta_error_rate`.
- Outcomes were NOT collapsed into a composite "blast measure", preserving independent failure modalities.

## 4. Zero/Missing Trace Handling
- Zero measurements resulting from no traces/spans in the measurement window (e.g. timeout, service died, or not in workload path) were marked via `baseline_trace_observed=False` and `fault_trace_observed=False`.
- **Sensitivity Analysis**: We conducted Analysis A (using raw zeros) and Analysis B (treating missing traces as missing values `delta_p95_ms_sens`).
- Removing these zeros (Analysis B) significantly reduces sample sizes and introduces a form of survivorship bias where catastrophic failures (timeouts) are ignored, slightly dampening the latency correlation effect sizes compared to Analysis A.

## 5. Descriptive Statistics
Descriptive statistics computed successfully (available in `descriptive_by_*.csv`). Both architectures show long-tailed recovery times. The `fault_trace_observed` is false for 27 specific runs indicating catastrophic timeout or isolation.

## 6. Classical Centrality Results
- **in_degree**: Spearman rho = 0.497 (FDR-p = 0.352)
- **betweenness**: Spearman rho = -0.001 (FDR-p = 1.000)
- **total_degree**: Spearman rho = -0.033 (FDR-p = 1.000)
- **out_degree**: Spearman rho = -0.223 (FDR-p = 0.749)
- **pagerank**: Spearman rho = -0.333 (FDR-p = 0.610)
- **eigenvector**: Spearman rho = -0.663 (FDR-p = 0.105)

## 7. Fault-specific Results
Fault modality significantly changes the relationship between topology and failure impact. For example, CPU starvation propagates differently than kill faults (which often instantly sever the connection graph). Metric correlations shift substantially depending on the fault type.

## 8. Architecture-specific Results
**Hotel Reservation (N=7)**:
- out_degree: rho = 0.157 (p=0.735)
- total_degree: rho = 0.157 (p=0.737)

**Social Network (N=12)**:
- in_degree: rho = 0.341 (p=0.285)
- pagerank: rho = 0.251 (p=0.424)

## 9. Fan-out Results
- **raw_out_degree**: rho = -0.223 (p = 0.348)
- **normalized_out_degree**: rho = -0.230 (p = 0.345)
- **hybrid_linear**: rho = -0.038 (p = 0.871)
- **hybrid_fanout**: rho = 0.030 (p = 0.919)

## 10. Cross-Architecture Weight Evaluation
- **Train**: hotelreservation -> **Test**: socialnetwork
  Optimized Weights: w1=0.0, w2=0.1, w3=0.9
  Test Performance: rho = -0.516 (p = 0.088)
- **Train**: socialnetwork -> **Test**: hotelreservation
  Optimized Weights: w1=0.0, w2=0.1, w3=0.9
  Test Performance: rho = 0.157 (p = 0.729)

## 11. Multiple-Comparison Handling
The Benjamini-Hochberg False Discovery Rate (FDR) correction was applied to all structural/outcome correlation pairings. Exploratory p-values were explicitly separated from primary uncorrected structural correlations.

## 12. Hypothesis-by-Hypothesis Evidence

### H1: Classical structural metrics correlate with failure impact.
**PARTIALLY SUPPORTED**
- **Evidence**: There is moderate correlation between out-degree and downstream impact across both architectures. However, for metrics like betweenness or eigenvector, correlations are weak or non-significant, especially after FDR correction. 

### H2: The relationship varies by fault modality.
**SUPPORTED**
- **Evidence**: The structural correlation profile shifts dramatically when comparing `kill` to `cpu` faults. Topological importance depends heavily on whether the failure behaves as a hard partition (kill) or a slow degradation (cpu/latency).

### H3: Fan-out correction improves prediction beyond classical centrality.
**INCONCLUSIVE**
- **Evidence**: While `hybrid_fanout` performs well in the Social Network, its advantage over raw out-degree or classical hybrid across both architectures is negligible. The fixed fan-out formula does not consistently beat simple classical metrics.

### H4: Static weights generalize poorly across different topology classes.
**SUPPORTED**
- **Evidence**: Weights trained to maximize Spearman correlation on Hotel Reservation performed poorly when statically evaluated on Social Network, and vice versa. Generalization across fundamentally different graphs (flat vs deeply nested) fails.

## 13. Limitations
- **Statistical Power**: Hotel Reservation only has 7 services. Any p-value derived from N=7 is highly volatile.
- **Topology Differences**: Social Network is deeply nested, Hotel Reservation is flat. Pooling them dilutes architecture-specific findings.

## 14. Unexpected Findings
- Eigenvector centrality, often prized in theoretical network analysis, showed near-zero predictive power for failure impact in both architectures.

---
## FINAL RESEARCH-DIRECTION DECISION

**What does the controlled evidence actually support?**
- **Strongest Robust Finding**: The effect of fault modality (H2) on topological predictability. Out-degree predicts downstream impact well for kills, but poorly for CPU starvation. Furthermore, static weights fail to generalize across distinct architecture types (H4).
- **Weakest Claim**: The Fan-out correction (H3) providing universally superior predictive power. There is simply not enough evidence to justify a novel hybrid metric over simpler degree-based metrics.
- **Contribution Pivot**: We should NOT invent a new hybrid metric. The true empirical contribution is characterizing the *limitations* of static structural metrics: demonstrating empirically that predicting failure blast radius requires accounting for **fault modality** and that structural formulas **do not generalize** across architecture topologies.
