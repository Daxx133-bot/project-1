# Actual Fault Execution & Hotel Configuration Audit

This document traces the exact physical commands executed during the fault injection experiments, resolving discrepancies between configuration defaults and CLI overrides.

## The Execution Chain
1. `implementation/run_controlled_experiment.py` (Orchestrator)
2. `implementation/fault_runner.py` (Injector)
3. `implementation/fault_config.py` (Default Config)

## Hotel Configuration Audit
**Target File:** `implementation/fault_config_hotel.py`
**Result:** **IGNORED FOR FAULT PARAMETERS**

The file `fault_config_hotel.py` contains hotel-specific fault parameters (like CPU workers). However, `fault_runner.py` ONLY imports `HOTEL_EXCLUDED_SERVICES` from this file (Line 84). It completely ignores the customized `DEFAULT_SPECS` in the hotel config, falling back to the standard `fault_config.py` for all physical parameters. 

**Conclusion:** Both Social Network and Hotel Reservation received the exact same physical fault parameters.

## Fault Parameter Audit

### 1. Fault Duration
- `fault_config.py` defaults to `duration_seconds=60`.
- **OVERRIDE:** `run_controlled_experiment.py` explicitly passes `--fault-duration 30` in the CLI arguments (Line 222).
- **Physical Reality:** The fault duration was **30 seconds**. The measurement window was 30 seconds.

### 2. CPU Faults
- `fault_config.py` defines `DEFAULT_CPU_SPEC` with `cpu_workers=2` (Line 181).
- No CLI override exists for CPU workers.
- **Physical Command:** Pumba stress sidecar was executed with `--stressors=--cpu 2`.
- **Physical Reality:** CPU faults used exactly **2 workers** for both architectures. 

### 3. Latency Faults
- `fault_config.py` defines `DEFAULT_LATENCY_SPEC` with `latency_ms=500` (Line 174).
- No CLI override exists for latency.
- **Physical Command:** Pumba netem sidecar executed with `delay --time 500`.
- **Physical Reality:** Latency faults injected exactly **500ms** of latency (not 100ms as hallucinated in earlier drafts).

### 4. Kill Faults
- Pumba executes a standard `SIGKILL`.
- Container is restored via `docker-compose up -d`.

## Conclusion
The experiments were executed uniformly across both architectures. The physical reality of the experiment is:
- **Duration:** 30 seconds
- **Latency:** 500ms
- **CPU:** 2 workers
- **Hotel Overrides:** None applied (except exclusions).
