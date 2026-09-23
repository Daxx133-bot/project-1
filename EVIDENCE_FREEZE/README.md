# Evidence Freeze Package

- **Date/Time of Freeze:** 2026-09-20T21:58:00+05:30
- **Original Repository Root:** `C:/Users/daksh/.gemini/antigravity-ide/scratch/microservice-failure-analysis`
- **Purpose:** To create a completely isolated, read-only evidence package for independent forensic reconciliation of statistical and methodological claims, fully detached from potentially hallucinated or contaminated prior manuscript drafts.
- **Statement of Integrity:** All files in this directory are exact, unmodified copies of the original artifacts. The original files in the repository root were NOT modified during this process.

## Contents
- **Total Files Copied:** 224
- **Raw JSON Traces Copied:** 203
- **SHA256 Manifest:** `audit/SHA256_MANIFEST.csv`

## Exact Artifacts Included

### Derived Datasets (`derived/`)
- `primary_analysis_dataset.csv`
- `metric_correlations.csv`
- `fault_specific_correlations.csv`
- `fault_modality_validation.csv`
- `cross_architecture_results.csv`
- `fanout_validation.csv`
- `centrality_table_frozen.csv`

### Raw Telemetry (`raw/`)
- `run_manifest.csv`
- 203 raw Jaeger trace JSON footprints inside `socialnetwork/` and `hotelreservation/` subdirectories.

### Implementation Logic (`implementation/`)
- `fault_runner.py`
- `fault_config.py`
- `fault_config_hotel.py`
- `metrics_collector.py`
- `run_controlled_experiment.py`
- `compute_centrality.py`
- `phase5b_analysis.py` (Analysis Script)
- `phase5c_fast.py` (Analysis Script)
- `phase5c_validation.py` (Analysis Script)
- `correlation_analysis.py` (Analysis Script)
- `hybrid_weight_optimizer.py` (Analysis Script)

## Known Limitations
The frozen `fault_specific_correlations.csv` contains legacy computational results that must be independently verified. The raw JSON payload structure lacks standard schema definitions, requiring manual inference in `metrics_collector.py`.

> [!WARNING]
> This directory is an evidence snapshot. No scientific conclusion is considered established merely because it appears in a previous report. All statistics must be independently recomputed from the primary datasets or raw JSON footprints.
