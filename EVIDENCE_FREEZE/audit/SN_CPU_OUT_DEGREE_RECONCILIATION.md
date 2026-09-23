# SN CPU / Out-Degree Discrepancy Reconciliation

## 1. The Discrepancy
- **Earlier Evidence Inventory:** Claimed `tau = 0.113, p = 0.665`.
- **Phase 8.7 Initial Audit:** Claimed `tau = NaN` due to "zero variance."

## 2. Independent Re-Evaluation
By strictly isolating the 12 Social Network CPU fault observations from `primary_analysis_dataset.csv`, we observe the following aggregated `recovery_time_s` values:
- `unique-id-service`: 20.13 s
- `compose-post-service`: 0.123 s
- `post-storage-service`: 0.126 s
- `social-graph-service`: 0.083 s
- `nginx-web-server`: 60.85 s
- `user-timeline-service`: 0.100 s
- `text-service`: 0.116 s
- `user-mention-service`: 0.106 s
- `home-timeline-service`: 0.116 s
- `url-shorten-service`: 0.113 s
- `media-service`: 0.156 s
- `user-service`: 0.106 s

**Variances:**
- `recovery_time_s` variance: 295.52
- `out_degree` variance: 5.02

Both vectors have non-zero variance. The correlation is mathematically defined.

## 3. Recomputation
Calculating the Kendall rank correlation coefficient between `out_degree` and `recovery_time_s` on these 12 exact physical observations yields:
**$\tau = 0.113$**

## 4. Final Conclusion & Reconciliation
- **What produced 0.113:** The actual, physical recorded data in `primary_analysis_dataset.csv` aggregated by service mean. Two specific services (`nginx-web-server` and `unique-id-service`) experienced substantial physical recovery times during CPU faults, creating significant variance in the dataset.
- **Is 0.113 experimentally valid:** **YES.** It is the precise, mathematically correct correlation of the physical measurements.
- **Why the current audit reported NaN:** The Phase 8.7 audit textually hallucinated the `NaN` claim. The auditor incorrectly generalized the qualitative observation that "CPU faults do not stop the Docker container" into an absolute mathematical assumption of "zero variance," directly contradicting the auditor's own internal calculation logs (which had actually output 0.113).
- **Correct final statistical result:** **$\tau = 0.113$**.
- **Source Files:** 
  - `EVIDENCE_FREEZE/derived/primary_analysis_dataset.csv`
  - `EVIDENCE_FREEZE/derived/centrality_table_frozen.csv`
  - `EVIDENCE_FREEZE/scripts/independent_recomputation.py` (Line 42)
