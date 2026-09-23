# Primary Dataset Provenance

This document verifies the exact data pipeline that generated `primary_analysis_dataset.csv` to ensure it is a faithful representation of the underlying measurements.

## Data Pipeline Trace

**Final Output:** `derived/primary_analysis_dataset.csv`
**Generating Script:** `implementation/phase5b_analysis.py` (Lines 76-91)
**Input File:** `raw/run_manifest.csv`

### Filtering
- **Function/Line:** `phase5b_analysis.py`, Line 78
- **Logic:** `df = df[df['status'] == 'VALID'].copy()`
- **Result:** Drops exactly 3 invalid rows (aborted or retry-failed runs).

### Transformations & Derived Columns
- **Delta P95:** `df['delta_p95_ms'] = df['fault_p95_ms'] - df['baseline_p95_ms']` (Line 80)
- **Delta Error Rate:** `df['delta_error_rate'] = df['fault_error_rate'] - df['baseline_error_rate']` (Line 81)
- **Trace Observed Flags:** 
  - `df['baseline_trace_observed'] = (df['baseline_p95_ms'] != 0)` (Line 83)
  - `df['fault_trace_observed'] = (df['fault_p95_ms'] != 0)` (Line 84)

### Final Columns
Selected (Line 86-89): `run_id`, `architecture`, `service`, `fault_type`, `repetition`, `baseline_p95_ms`, `fault_p95_ms`, `baseline_error_rate`, `fault_error_rate`, `downstream_affected_count`, `recovery_time_s`, `delta_p95_ms`, `delta_error_rate`, `baseline_trace_observed`, `fault_trace_observed`

**Centrality Integration:** Centrality metrics are **NOT** embedded in this dataset. They are joined dynamically at runtime during statistical evaluation (e.g., in `phase5c_validation.py`).

## Verification Results
- **Row Count:** 171
- **Column Count:** 15
- **Duplicate Rows:** 0
- **Missing Values:** 0
- **Invalid Exclusions Confirmed:** 3
- **Architecture Distribution:** {'socialnetwork': 108, 'hotelreservation': 63}
- **Fault Distribution:** {'kill': 57, 'latency': 57, 'cpu': 57}
- **Unique Services Tested:** 19
- **Repetitions Distribution:** {1: 57, 2: 57, 3: 57}

## Conclusion
The `primary_analysis_dataset.csv` is an exact, unaltered (among valid runs) passthrough of the physical measurements logged into the orchestrator manifest, plus simple arithmetic deltas. It is fully verified and authoritative.
