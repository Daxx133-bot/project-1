# Phase 3A: Infrastructure Fix Report

This report documents the resolution of the Docker environment blocker and the results of the subsequent physical pilot experiment.

### 1. Root Cause
The `run_controlled_experiment.py` orchestrator originally attempted to restart `compose-post-service` (Social Network) after a kill fault. This triggered a recursive `docker-compose up -d` which attempted to spin up the Social Network's `jaeger-agent` dependency. The start failed because the Hotel Reservation's Jaeger instance was already running and occupying host port `16686`, resulting in a fatal `subprocess.CalledProcessError`.

### 2. Ports Identified
Through analyzing the `docker-compose.yml` configurations for both architectures, the following host ports were identified:
*   **Social Network:** `10002`, `8080`, `8081`, `16686`
*   **Hotel Reservation:** `8300`, `8400`, `8500`, `8600`, `5000`, `16686`, `5778`, `14268`, `5775`, `6831`, `6832`

The critical collision point is `16686` (Jaeger UI), which both architectures explicitly map to the host.

### 3. Infrastructure Changes
*   Designed a targeted architecture transition strategy using `docker-compose down` (without `-v`) to gracefully tear down the active architecture and release its host ports while preserving the underlying database volumes (such as the initialized social graph).
*   Implemented a safe port-conflict detection check that scans running container ports before attempting a startup.
*   Implemented HTTP health checks targeting the Application Gateways (`8080` / `5000`) and the Jaeger API (`16686`).
*   Modified the experiment orchestrator to enforce a strict preflight check before every architecture transition.

### 4. Files Modified
*   `[NEW] scripts/preflight_environment.py`
*   `[MODIFIED] scripts/run_controlled_experiment.py`

### 5. Safety Considerations
*   **Volume Preservation:** Used `docker-compose down` explicitly omitting the `-v` flag to prevent destroying the `init_social_graph` state.
*   **Targeted Teardown:** The preflight script explicitly targets the active DeathStarBench compose stack. It will automatically abort rather than issuing broad `docker kill` commands if unrelated processes are occupying the required ports.

### 6. Preflight Results
The standalone `preflight_environment.py` successfully parses docker states, tears down the inactive stack, starts up the target stack, and verifies its health.

### 7. Architecture Switching Test Results
The environment successfully transitioned in both directions:
1.  **HR $\rightarrow$ SN:** Port 16686 successfully released by HR Jaeger and acquired by SN Jaeger. SN gateway HTTP 8080 reported healthy.
2.  **SN $\rightarrow$ HR:** Port 16686 successfully released by SN Jaeger and acquired by HR Jaeger. HR gateway HTTP 5000 reported healthy.

### 8. Pilot Results
*   **Status:** PARTIAL SUCCESS (Infrastructure Passed, Data Collection Failed)
*   **Executions:** 12 total runs successfully orchestrated without crashing.
*   **Fault Injection:** `SUCCESS`. Pumba successfully targeted the active containers and injected kill, latency, and cpu faults.
*   **Recovery Measurement:** `SUCCESS`. The script successfully waited and detected service recovery post-fault.
*   **Workload/Trace Collection:** `FAILED`. The resulting `experiment_log.csv` generated all `0.0` values for `baseline_p95_ms`, `fault_p95_ms`, and `downstream_affected_count`.

### 9. Any Remaining Blockers
While the orchestrator machinery is now stable and fully capable of surviving the 171-run loop without crashing, **no telemetry data is being captured**. The metrics parser is returning `0.0` for all latencies and `0` for the blast radius. 
This indicates that either:
1.  The `wrk2` / Locust load generator is failing to generate valid traffic.
2.  The Jaeger agent is failing to ingest or report the traces to the collector.
3.  The Python metrics parsing script is querying the wrong Jaeger endpoint.

We cannot proceed to the 171-run physical experiment until trace ingestion is fixed.

### 10. Exact Command for the Next Phase
The next phase must debug the trace collection pipeline. Start by running a single trace generation debug run:
```bash
python scripts/run_controlled_experiment.py --pilot
```
