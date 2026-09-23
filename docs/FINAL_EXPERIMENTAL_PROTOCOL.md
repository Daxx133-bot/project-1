# Final Experimental Protocol
## Topology-Based Microservice Failure Prediction

This document defines the frozen experimental protocol for evaluating graph centrality and fan-out metrics as predictors of microservice failure impact.

### 1. Research Questions & Hypotheses
*   **RQ1:** How strongly do structural properties of SDGs correspond to empirically observed failure impact?
*   **RQ2:** Do classical graph centrality measures identify services susceptible to failure propagation?
*   **RQ3:** Does explicitly incorporating fan-out improve identification beyond classical centrality?
*   **RQ4:** How does predictive power vary across topology classes (mesh vs. tree)?
*   **RQ5:** Under what fault conditions does prediction become unreliable?

**Hypotheses:**
*   **H1:** Centrality exhibits statistically significant rank correlation ($\tau_b > 0$) with failure impact.
*   **H2:** Impact is fault-dependent (Latency correlates with Betweenness, Kill with Degree).
*   **H3:** Fan-out corrected metric achieves significantly higher Pairwise Ranking Accuracy (PRA) than linear metrics on cyclic meshes.
*   **H4:** Static weights fail to generalize across topology classes.

### 2. Experimental Framework
*   **Experimental Unit:** Service-Fault combination (e.g., `media-service`, `latency`).
*   **Architectures:** 
    1. Social Network (DeathStarBench, C++/Thrift, Cyclic Mesh, 12 services).
    2. Hotel Reservation (DeathStarBench, Go/gRPC, Hierarchical Tree, 7 services).
*   **Services:** All 19 active microservices across both architectures.
*   **Fault Types:**
    1. `kill` (Container hard crash)
    2. `latency` (Network delay injection)
    3. `cpu` (CPU saturation)
*   **Fault Intensity:** 
    *   Latency: 500ms delay.
    *   CPU: 100% utilization on 1 core.
*   **Workload:** `wrk2` at 1000 Requests Per Second (RPS) for 60 seconds.
*   **Warm-up Duration:** 15 seconds.
*   **Fault Duration:** 30 seconds.
*   **Repetitions:** Exactly 3 repetitions per unit to balance variance.

### 3. Procedure
1.  **Reset:** Docker containers restarted, DBs purged, Jaeger flushed.
2.  **Warm-up:** Load generator active for 15s.
3.  **Baseline:** Extract baseline P95, throughput, and error rate.
4.  **Inject Fault:** Pumba executes fault for 30s.
5.  **Recovery:** Measure time until baseline P95 is restored.
6.  **Graph Extraction:** Generate SDG from baseline Jaeger traces (100% sampling).

### 4. Metrics & Evaluation
*   **Baselines:** In/Out/Total Degree, Betweenness, PageRank, Classical Composite.
*   **Hybrids:** Linear Hybrid, Quadratic Fan-Out Hybrid, Independent Fan-Out Hybrid.
*   **Dependent Variables (DVs):** $\Delta$P95 Latency, $\Delta$Error Rate, Recovery Time, Downstream Affected Count.
*   **Ranking:** Top-k Ranking, Pairwise Ranking Accuracy (PRA).
*   **Statistics:** Kendall's tau-b ($\tau_b$), Monte Carlo Permutation Test (N=9999, seed=42), Bootstrap 95% CI (1000 resamples).

### 5. Validation Protocol
*   **Architecture Holdout:** Train on HR $\rightarrow$ Test on SN. Train on SN $\rightarrow$ Test on HR.
*   **Fault Holdout:** Train on (Kill, CPU) $\rightarrow$ Test on Latency.
*   **Weight Optimization:** Grid search $\sum w_i = 1.0$ (step 0.1). Objective: Maximize $\tau_b$ against target DV on training set.
*   **Tie-Breaking:** If weights tie, prefer the model with lowest standard deviation of error, followed by smallest $w_2$ (favoring simpler models).

### 6. Data Management
*   **Run ID:** `{Arch}_{Service}_{Fault}_rep{N}` (e.g., `SN_compose-post-service_kill_rep01`).
*   **Failed Runs:** Logged as `FAILED`. Not silently retried.
*   **Missing Data:** If a run fails 3 times, the entire Service-Fault unit is excluded from aggregation to preserve matrix balance.
