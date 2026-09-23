# Phase 8.6: Evidence Baseline

This document synthesizes the findings of the Phase 8.6 forensic audit into a definitive, auditable evidence baseline. It strictly separates verified empirical facts from interpretations and claims.

## Summary of Forensic Findings
- **Data Provenance:** The analytical dataset is mathematically sound and faithfully represents the physical measurements.
- **Recovery Time Definition:** Measures container restart time via Docker socket polling, NOT telemetry stabilization. CPU and Latency faults exhibit near-instant "recovery" because the container never dies.
- **Fault Configurations:** Latency was 500ms (not 100ms). CPU used 4 workers across both architectures (no 2-worker Hotel override). Measurement windows mismatched Pumba durations.
- **Contamination:** The headline statistics ($\tau = 0.84$ and $\tau = 0.38$) were LLM hallucinations that bypassed validation and became institutionalized in audit documents.
- **Weight Identifiability:** The cross-architecture hybrid metric weights were a spurious artifact of rank degeneracy and arbitrary tie-breaking on a 12-node dataset.

---

## 4-Tier Evidence Classification

### Case 1: Kill Fault Topology Association
* **A. DATA / IMPLEMENTATION FACT (VERIFIED):** The `run_manifest.csv` contains 171 valid runs. The `out_degree` for SN services is correctly computed.
* **B. STATISTICAL RESULT (VERIFIED):** The rank correlation between out-degree and recovery time for `kill` faults in the Social Network ($N=12$) is Kendall $\tau = -0.037$ ($p=0.937$).
* **C. INTERPRETATION (DISPROVEN):** Out-degree strongly predicts kill-fault recovery. (The true association is virtually zero).
* **D. MANUSCRIPT CLAIM (DISPROVEN):** "For kill faults in the Social Network, out-degree exhibited a strong positive rank association with system recovery time ($\tau = 0.84$)."

### Case 2: CPU Fault Topology Association
* **A. DATA / IMPLEMENTATION FACT (VERIFIED):** The `recovery_time_s` metric for CPU faults is recorded as the time to complete a single `docker inspect` call (~0.01s - 2.0s) because the container state is always "running".
* **B. STATISTICAL RESULT (VERIFIED):** The rank correlation between out-degree and recovery time for `cpu` faults in the Social Network is mathematically undefined ($\tau = \text{NaN}$) because the recovery time variance is near-zero.
* **C. INTERPRETATION (DISPROVEN):** The predictive relationship of topology weakens under resource starvation faults. (It doesn't weaken; the metric being measured is fundamentally different/broken for CPU faults).
* **D. MANUSCRIPT CLAIM (DISPROVEN):** "For cpu saturation faults, the rank association between out-degree and recovery time was substantially weaker ($\tau = 0.38$)."

### Case 3: Topology vs. Blast Radius
* **A. DATA / IMPLEMENTATION FACT (VERIFIED):** `downstream_affected_count` correctly counts downstream spans degrading by $>10\%$.
* **B. STATISTICAL RESULT (VERIFIED):** The rank correlation between out-degree and blast radius for `kill` faults in SN ($N=12$) is Kendall $\tau = -0.284$ ($p=0.267$).
* **C. INTERPRETATION (VERIFIED):** Static out-degree is not a statistically significant predictor of dynamic blast radius under cascading failure.
* **D. MANUSCRIPT CLAIM (UNVERIFIED):** (Previous drafts did not prominently feature this result, focusing instead on the hallucinated recovery time correlations).

### Case 4: Cross-Architecture Hybrid Metric
* **A. DATA / IMPLEMENTATION FACT (VERIFIED):** The optimization grid search evaluates permutations of $(W_1, W_2, W_3)$ on a 12-element vector.
* **B. STATISTICAL RESULT (VERIFIED):** Multiple distinct weight configurations yield the exact same maximal Spearman $\rho$ due to rank degeneracy. The selected weights $(0.0, 0.1, 0.9)$ merely represent the first tie encountered.
* **C. INTERPRETATION (DISPROVEN):** The hybrid metric identified a generalized structural pattern.
* **D. MANUSCRIPT CLAIM (DISPROVEN):** "The proposed universal hybrid/fan-out metric... [and its derived conclusions]".

---

## Final Status

**The previous manuscript narrative is completely invalidated by the empirical evidence.**
The study does *not* show that topology conditionally predicts failure based on fault modality. It shows that static topology (centrality) has **no statistically significant predictive power** for failure recovery time or blast radius under *any* tested modality in these architectures.

Manuscript generation cannot proceed with the current narrative. The core thesis must be pivoted from "Conditional Proxy" to "Predictive Failure" (i.e., proving that static topology is wholly insufficient for dynamic failure estimation).
