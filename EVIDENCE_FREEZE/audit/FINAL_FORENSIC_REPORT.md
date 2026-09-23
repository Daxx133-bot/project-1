# Final Forensic Report: Phase 8.7 Evidence Audit

## 1. Executive Summary
This report concludes a comprehensive, independent forensic reconstruction of the experimental dataset and methodology underlying the microservice failure analysis. The audit definitively proves that the statistical claims ($\tau = 0.84$ and $\tau = 0.38$) which anchored prior manuscript drafts were LLM hallucinations that bypassed validation. The actual data pipeline is mathematically sound, but it reveals that static topology has virtually no predictive power for the measured recovery time metrics.

## 2. Evidence Package Contents
The `EVIDENCE_FREEZE` directory contains 224 explicitly hashed, read-only artifacts. This includes 203 raw JSON traces, the full derived dataset pipeline, and the exact executable scripts used to orchestrate faults and measure outcomes.

## 3. Dataset Provenance
The `primary_analysis_dataset.csv` is an uncorrupted, perfectly faithful extraction of the physical measurements from `run_manifest.csv`, matching the valid runs exactly with zero arbitrary row droppings or leaky joins.

## 4. Experiment Matrix
The matrix contains exactly 171 valid physical observations (108 Social Network, 63 Hotel Reservation). Every valid run corresponds to a physical JSON footprint on disk. The matrix is complete.

## 5. Recovery-Time Implementation
`recovery_time_s` measures the duration of a `docker inspect` polling loop waiting for the container's `.State.Running` flag to become `true`. It captures hard container restarts (Kill faults). Because CPU and Latency faults do not kill the container, their "recovery time" is near-instant, rendering variance-based correlations (like Kendall Tau) mathematically undefined or meaningless. It does not measure telemetry stabilization.

## 6. Fault Execution
Physical fault configurations were hardcoded to 30 seconds duration (overriding the 60s config), 500ms latency, and 2 CPU workers. The Hotel Reservation-specific configurations were never imported for fault parameters, ensuring uniform physical execution across both architectures.

## 7. Zero-Trace Semantics
A `p95_ms` of `0.0` in this dataset mathematically denotes that Jaeger returned an empty payload, typically because the gateway container crashed and could not emit traces. It does not mean instantaneous request execution.

## 8. Independent Statistics
A ground-up Python recomputation of all correlations proved that Social Network kill faults have a true rank correlation with out-degree of $\tau = -0.037$ ($p = 0.937$), essentially zero.

## 9. Statistical Reconciliation
Every numerical output produced by the newly isolated `independent_recomputation.py` identically matches the outputs from the original Phase 5 scripts. The mathematical pipeline was correct; the interpretation was fabricated.

## 10. Cross-Architecture Optimization
The hybrid metric weights (0.0, 0.1, 0.9) were mathematically unidentifiable. The grid search optimized 2 degrees of freedom over a highly degenerate discrete rank space of only 12 nodes, simply locking onto the first arbitrary tie it encountered.

## 11. 0.84 / 0.38 Contamination Trace
These values originated as pure textual hallucinations in `FINAL_MANUSCRIPT_DRAFT.md`. Successive model iterations falsely validated these numbers in audit reports, institutionalizing them in evidence matrices without ever checking the CSV outputs.

## 12. Verified Facts
- 171 valid physical observations exist.
- Latency faults injected 500ms delay.
- Faults lasted 30 seconds.
- True SN Kill out-degree correlation is -0.037.

## 13. Unverified Claims
- The claim that fan-out improves prediction over out-degree is structurally unverified because no metric effectively predicted recovery time.

## 14. Incorrect Claims
- $\tau = 0.84$ (SN Kill) and $\tau = 0.38$ (SN CPU) are completely false.
- Claims of 100ms latency and 4 CPU workers are false.
- Claims of measuring true application telemetry stabilization are false.
- Claims of finding generalized cross-architecture structural patterns are false.

## 15. Remaining Questions
- Can the raw Jaeger JSON traces be re-mined to extract a true application-level stabilization metric (time until 5xx errors cease) rather than relying on the Docker socket polling?

## 16. Conditions Required Before Manuscript Generation
- The manuscript must NOT be generated until the scientific thesis is explicitly rewritten by the researchers to reflect the verified empirical truth (that static topology is insufficient) rather than the hallucinated conditional proxy narrative.
