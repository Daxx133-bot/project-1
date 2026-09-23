# Phase 8.6: Artifact Inventory

This document enumerates the relevant artifacts located in the repository for the Evidence Reconstruction and Data Integrity Audit.

## Raw Experiment Output Files
**Location:** `measurement/results_controlled/`
- **Purpose:** Primary historical record of the 171 controlled runs.
- **Artifacts:**
  - `run_manifest.csv`: The master orchestrator log documenting all attempts, statuses (VALID/INVALID), and high-level timestamps and metrics.
  - `socialnetwork/*.json`: Individual raw telemetry snapshots (latency distributions, error rates, timestamps) for the SN experiments.
  - `socialnetwork/experiment_log.csv`: Flattened log of the SN runs.
  - `hotelreservation/*.json`: Individual raw telemetry snapshots for the HR experiments.
  - `hotelreservation/experiment_log.csv`: Flattened log of the HR runs.
- **Nature:** Raw observational data.
- **Reproducibility:** Cannot be strictly reproduced without re-running the 7-hour physical experiment, but the JSON files serve as the ground-truth historical record.

## Analysis and Transformation Scripts
**Location:** `scratch/` and `analysis/`
- **Purpose:** Scripts that transformed raw data into statistical datasets.
- **Artifacts:**
  - `scratch/phase5a.py`: Looks to be the script that assembled the primary analysis dataset from the `run_manifest.csv` and JSON outputs.
  - `scratch/phase5b_analysis.py`: Likely generated the descriptive statistics.
  - `scratch/phase5c_validation.py` / `scratch/phase5c_fast.py`: Likely computed the Kendall/Spearman correlations.
  - `analysis/correlation_analysis.py`: Contains the core correlation logic.
  - `analysis/generate_plots.py`: Generates the figures.
- **Nature:** Derived / Interpretive code.
- **Reproducibility:** Highly reproducible. The logic can be audited and rerun.

## Phase 5 Datasets and CSVs
**Location:** `analysis/outputs/`
- **Purpose:** The datasets and outputs from the Phase 5 analysis.
- **Artifacts:**
  - `primary_analysis_dataset.csv`: The core dataset containing joined topological and empirical metrics for the 171 valid runs. **(Requires strict provenance audit)**.
  - `metric_correlations.csv`: Pooled correlation results.
  - `fault_specific_correlations.csv`: Correlation results broken down by fault and architecture.
  - `fault_modality_validation.csv`: Another correlation output file.
  - `cross_architecture_results.csv`: Outputs of the cross-architecture transfer experiment.
  - `fanout_validation.csv`: Outputs of the fan-out metric analysis.
- **Nature:** Derived data (except for centrality table).
- **Reproducibility:** Yes, these must be independently reproducible from the raw JSONs and centrality table.

## Centrality Data
**Location:** `centrality/output/`
- **Purpose:** Frozen structural data based on the service dependency graphs.
- **Artifacts:**
  - `centrality_table_frozen.csv`: The frozen structural metrics for all services.
- **Nature:** Derived data (from static graph analysis).
- **Reproducibility:** Yes, via `centrality/compute_centrality.py`.

## Measurement and Metric Collection
**Location:** `measurement/`
- **Purpose:** Contains the actual implementation logic for querying Jaeger and computing blast radius/recovery.
- **Artifacts:**
  - `metrics_collector.py`: Defines how zero-traces are handled and how percentiles are computed.
- **Nature:** Implementation logic.
- **Reproducibility:** Represents the physical mechanism of measurement.

## Fault Injection Configuration
**Location:** `faultinjection/`
- **Purpose:** Configuration and orchestration of the physical faults.
- **Artifacts:**
  - `fault_config.py`: Base fault configurations and Pumba command builders.
  - `fault_config_hotel.py`: HR-specific overrides.
  - `fault_runner.py`: The execution loop, containing the `recovery_time_s` container restart polling logic.
- **Nature:** Implementation logic.
- **Reproducibility:** Represents the physical mechanism of fault injection.

## Orchestration Scripts
**Location:** `scripts/`
- **Purpose:** Main entry points for running the experiments.
- **Artifacts:**
  - `run_controlled_experiment.py`: The script that initiated the 171 controlled runs.
- **Nature:** Orchestration logic.
