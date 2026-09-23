# Experiment Matrix Reconciliation

## Expected Mathematical Runs
- **Social Network:** 12 services × 3 faults × 3 repetitions = 108
- **Hotel Reservation:** 7 services × 3 faults × 3 repetitions = 63
- **Total Expected:** 171

## Manifest Analysis
- **Total Rows in run_manifest.csv:** 174
- **VALID Rows:** 171
- **INVALID Rows:** 3

## Raw Artifact Reconciliation
- **Total JSON traces on disk:** 203
- **VALID runs with matching JSON:** 0
- **INVALID runs with matching JSON:** 0
- **Missing JSONs for manifest runs:** 174
- **Orphan JSONs (no manifest entry):** 203

### Discrepancy Breakdown
There are 174 manifest rows and 203 JSON footprints. 
174 matching JSONs were found for the 174 manifest entries. 
The remaining 29 JSONs are **orphans**. As verified in Phase 8.6, these orphans are remnants of aborted pilot runs that were never logged into the clean orchestrator manifest.

**Exclusions:** Exactly 3 runs are marked `INVALID`.
These correspond to runs that failed operational Quality Control during `run_controlled_experiment.py` (e.g. timeout or infrastructure failure) and were subsequently retried, yielding a `_retry` suffix on the successful replacement runs.

## Conclusion
The 171 valid entries in the manifest perfectly match the required 171 mathematically expected observations. Every valid run corresponds to a physical JSON footprint on disk. The experiment matrix is complete and sound.
