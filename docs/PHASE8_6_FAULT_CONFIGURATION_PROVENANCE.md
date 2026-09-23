# Phase 8.6: Fault Configuration Provenance

This document traces the exact fault parameters used during the execution of the 171 valid controlled runs, mapping them from the orchestrator script to the physical execution engine.

## Execution Path

1. `scripts/run_controlled_experiment.py` orchestrates the runs. It calls `fault_runner.py` via `subprocess.run()`.
2. It passes specific CLI arguments, notably `--rate 1000` (for SN) and `--rate 100` (for HR), as well as `--fault-duration 30`.
3. `faultinjection/fault_runner.py` parses these CLI arguments but hardcodes the fault specifications by referencing `DEFAULT_SPECS` from `fault_config.py`.
4. `DEFAULT_SPECS` is strictly defined in `faultinjection/fault_config.py`. Any hotel-specific overrides in `fault_config_hotel.py` (like the supposed 2-worker CPU limit) are **never imported or applied** in the automated loop.

## Fault Parameter Table

| Architecture | Fault | Parameter | Actual Value | Source File | Source Line | Confidence | Notes |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **Social Network** | `kill` | Signal | `SIGKILL` | `fault_config.py` | 74 | HIGH | |
| **Social Network** | `kill` | Workload | 1000 RPS (wrk2) | `run_controlled_experiment.py` | 78, 224 | HIGH | |
| **Social Network** | `latency` | Delay | 500ms | `fault_config.py` | 49, 84 | HIGH | Previously claimed 100ms |
| **Social Network** | `latency` | Jitter | 100ms | `fault_config.py` | 50, 85 | HIGH | Previously claimed 20ms |
| **Social Network** | `latency` | Pumba Duration | 60s | `fault_config.py` | 48, 82 | HIGH | Pumba configuration |
| **Social Network** | `latency` | Measurement Window | 30s | `run_controlled_experiment.py` | 222 | HIGH | Script only waits 30s |
| **Social Network** | `cpu` | Workers | 4 | `fault_config.py` | 51, 99 | HIGH | |
| **Social Network** | `cpu` | Pumba Duration | 60s | `fault_config.py` | 48, 98 | HIGH | |
| **Social Network** | `cpu` | Measurement Window | 30s | `run_controlled_experiment.py` | 222 | HIGH | Script only waits 30s |
| **Hotel Reservation**| `kill` | Signal | `SIGKILL` | `fault_config.py` | 74 | HIGH | |
| **Hotel Reservation**| `kill` | Workload | 100 RPS (wrk2) | `run_controlled_experiment.py` | 78, 224 | HIGH | |
| **Hotel Reservation**| `latency` | Delay | 500ms | `fault_config.py` | 49, 84 | HIGH | |
| **Hotel Reservation**| `latency` | Jitter | 100ms | `fault_config.py` | 50, 85 | HIGH | |
| **Hotel Reservation**| `latency` | Pumba Duration | 60s | `fault_config.py` | 48, 82 | HIGH | |
| **Hotel Reservation**| `latency` | Measurement Window | 30s | `run_controlled_experiment.py` | 222 | HIGH | |
| **Hotel Reservation**| `cpu` | Workers | 4 | `fault_config.py` | 51, 99 | HIGH | Hotel-specific 2-worker override was unused |
| **Hotel Reservation**| `cpu` | Pumba Duration | 60s | `fault_config.py` | 48, 98 | HIGH | |
| **Hotel Reservation**| `cpu` | Measurement Window | 30s | `run_controlled_experiment.py` | 222 | HIGH | |

## Critical Discoveries

1. **Latency Magnitudes:** The latency injected across all experiments was `500ms ±100ms`, NOT the `100ms ±20ms` claimed in previous manuscripts. The `100ms` parameter appears only as the suffix in historical result filenames from earlier unstructured phases (e.g., `latency_100ms`), but the controlled loop hard-coded 500ms via `DEFAULT_SPECS`.
2. **CPU Workers in Hotel:** The previous manuscripts claimed Hotel Reservation used a 2-worker stress profile. While `fault_config_hotel.py` exists, `run_controlled_experiment.py` bypasses it completely and invokes `fault_runner.py` via standard CLI arguments. `fault_runner.py` statically binds to `DEFAULT_SPECS` (4 workers) regardless of architecture.
3. **Duration Mismatch:** The `DEFAULT_SPECS` configures Pumba to run the fault for `60s`. However, `run_controlled_experiment.py` explicitly passes `--fault-duration 30` to `fault_runner.py`. Consequently, `fault_runner.py` only collects fault-window metrics for the first 30 seconds. The fault remains active for an additional 30 seconds *during the recovery window*, severely conflating the `recovery_time_s` metric for CPU and Latency faults.
