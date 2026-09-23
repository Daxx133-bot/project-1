# Phase 8.7 Final Evidence Baseline

This document represents the absolute ground-truth physical and statistical reality of the experiment, verified by independent forensic reconstruction. No conclusions from previous LLM-generated manuscripts or audits are preserved unless independently validated by executable code and raw JSON footprints in this `EVIDENCE_FREEZE`.

## A. VERIFIED DATA FACTS
- **171 Valid Observations:** The experiment matrix completed exactly 171 runs that passed operational QC (108 SN, 63 HR).
- **Dataset Provenance:** The `primary_analysis_dataset.csv` is an exact, mathematically sound passthrough of physical measurements.
- **Zero-Trace Semantics:** A recorded `p95_ms` of `0.0` mathematically signifies missing telemetry/failed queries due to crashed entry-point services, not instantaneous execution.

## B. VERIFIED IMPLEMENTATION FACTS
- **Recovery Time Definition:** Measures the duration of a Docker socket polling loop until `.State.Running == true`. It **does not** measure telemetry stabilization.
- **Fault Duration:** 30 seconds (overridden in `run_controlled_experiment.py` CLI).
- **Latency Fault Config:** 500ms delay.
- **CPU Fault Config:** 2 workers (applied equally to both architectures; hotel override was ignored).
- **Multiple Testing Correction:** None was applied during Phase 5.
- **Cross-Architecture Weight Identifiability:** Mathematically unidentifiable due to rank degeneracy; the optimization over-parameters 12 data points to resolve arbitrary ties.

## C. VERIFIED STATISTICAL RESULTS
- **SN kill / out_degree actual value:** $\tau = -0.037$ ($p = 0.937$)
- **SN CPU / out_degree actual value:** $\tau = 0.113$ (Mathematically valid, but statistically insignificant correlation from the true experimental data).
- **HR CPU / out_degree result:** $\tau = -0.741$. However, this is statistically invalid when adjusted for the 84 uncorrected multiple tests performed across the dataset.

## D. UNVERIFIED CLAIMS
- **Fan-out Improvement:** The claim that fan-out broadly improves prediction over out-degree is structurally unverified because no metric significantly correlates with actual telemetry-based recovery.

## E. DISPROVEN / INCORRECT CLAIMS
- **SN kill / out_degree $\tau = 0.84$:** Fabricated LLM hallucination.
- **SN CPU / out_degree $\tau = 0.38$:** Fabricated LLM hallucination.
- **100ms latency config:** Incorrect; actual was 500ms.
- **100ms ±20ms claim:** Incorrect.
- **500ms ±100ms claim:** Correct, but the 100ms jitter was not heavily analyzed.
- **60s fault duration:** Incorrect; overridden to 30s in orchestrator CLI.
- **4 CPU workers:** Incorrect; default in `fault_config.py` was 2 workers.
- **Telemetry stabilization recovery:** Incorrect; it was a simple Docker state poll.
- **Cross-architecture weight transfer:** Incorrect; optimization simply locked onto arbitrary grid-search ties.

## F. REMAINING UNCERTAINTIES
- **True Application Recovery Time:** Because the metric only polled Docker socket state, the true time for the microservice application layer to stabilize its telemetry and error rates remains entirely unmeasured by this dataset. Any claims about *application* recovery time are unsupported by this data.
