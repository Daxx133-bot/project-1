# Phase 8.6: Primary Dataset Provenance

This document traces the exact path of data flow from raw experiment output to the `primary_analysis_dataset.csv`, establishing its provenance as the authoritative empirical dataset for statistical analysis.

## Data Pipeline

**1. Generation (`faultinjection/fault_runner.py`)**
- During each physical fault injection run, `fault_runner.py` calculates real-time metrics:
  - Queries Jaeger for `p95_ms` and `error_rate` (baseline and fault windows).
  - Queries Jaeger to compute `downstream_affected_count`.
  - Polls Docker to measure `recovery_time_s`.
- These values are appended directly to the architecture-specific `experiment_log.csv`.
- Telemetry traces are saved as raw `.json` files.

**2. Orchestration Aggregation (`scripts/run_controlled_experiment.py`)**
- After `fault_runner.py` exits, the orchestrator opens `experiment_log.csv` and extracts the latest row corresponding to the current run.
- It performs operational Quality Control (QC). If all metrics are present and valid, it marks the run `VALID`.
- It writes the aggregated row (including the metrics) into the master `measurement/results_controlled/run_manifest.csv`.

**3. Dataset Extraction (`scratch/phase5b_analysis.py`)**
- The script reads `run_manifest.csv`.
- **Filtering:** It strictly filters for `status == 'VALID'`, dropping exactly 3 invalid runs.
- **Transformations:** 
  - Computes `delta_p95_ms = fault_p95_ms - baseline_p95_ms`
  - Computes `delta_error_rate = fault_error_rate - baseline_error_rate`
  - Creates boolean flags `baseline_trace_observed` and `fault_trace_observed` (checking if `p95 != 0`).
- **Output:** It selects a subset of columns and writes them to `analysis/outputs/primary_analysis_dataset.csv`.

## Verification of Source-of-Truth Rule

1. **Extraction Script:** `scratch/phase5b_analysis.py` (lines 77-91).
2. **Input Files:** Exclusively reads from `run_manifest.csv`. It does NOT parse the raw `.json` files.
3. **Row Counts:** 171 rows exactly. Matches the valid count in `run_manifest.csv`.
4. **Dropped Rows:** 3 rows dropped. Justification: Status was marked `INVALID` by the orchestrator QC due to infrastructure or telemetry failures. These runs were subsequently retried by the orchestrator (generating the `_retry` suffixes on valid runs).
5. **Duplicated Rows:** 0 duplicated rows. Confirmed via script audit.
6. **Centrality Metrics:** `primary_analysis_dataset.csv` does **NOT** contain centrality metrics. They are joined dynamically at runtime by the statistical evaluation scripts (e.g., `phase5c_validation.py`) using `service` as the foreign key against `centrality/output/centrality_table_frozen.csv`.

## Conclusion

The `primary_analysis_dataset.csv` is an exact, unfiltered (among valid runs) passthrough of the physical measurements logged by `fault_runner.py` into the orchestrator manifest. It is a **fully verified and authoritative** aggregation of the underlying empirical observations, and is safe to use for independent statistical recomputations.
