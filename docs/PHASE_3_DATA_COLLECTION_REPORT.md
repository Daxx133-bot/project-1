# Phase 3: Data Collection Report (NO-GO)

This report details the attempted execution of the physical Phase 3 data collection pilot.

### 1. Pilot Results
**Status: NO-GO (CRITICAL TECHNICAL FAILURE)**

The physical pilot (`python scripts/run_controlled_experiment.py --pilot`) failed to execute successfully. 

**Pilot Execution Breakdown:**
*   **Social Network Pilot (`compose-post-service`):**
    *   **Fault Injection:** `FAILED`. Pumba reported `no containers found` because the Social Network stack was not actively running; only Hotel Reservation was occupying the Docker daemon.
    *   **Recovery Measurement:** `FAILED`. The orchestrator attempted to restore the service using `docker-compose up -d compose-post-service`. This command recursively attempted to start the `jaeger-agent` dependency. 
    *   **Crash Reason:** Port collision. `Bind for 0.0.0.0:16686 failed: port is already allocated`. The Hotel Reservation's Jaeger container was already bound to the host's 16686 port, causing the Social Network Jaeger container startup to crash. This terminated the entire Python orchestrator with a `subprocess.CalledProcessError`.
*   **Hotel Reservation Pilot (`reservation`):** `SKIPPED` (Pipeline aborted before reaching this stage).

### 2. Workload Decision
*   **Decision:** PENDING. 
*   **Reason:** The pilot crashed before `wrk2` could generate workload or establish baseline P95 latency.

### 3. Full Experiment Execution Summary
*   **Status:** ABORTED. The full 171-run experiment cannot proceed until the environment port collision is resolved.

### 4. Run Inventory
*   **Successful:** 0
*   **Failed:** 1 (Social Network `compose-post-service` Kill Rep 01)
*   **Partial:** 0
*   **Retried:** 0
*   **Missing:** 171

### 5. Failed Runs
*   **Run ID:** `SN_compose-post-service_kill_rep01` (Attempted)
*   **Reason:** Docker port 16686 allocation collision preventing environment restoration.

### 6-11. Data Completeness & Stability
*   *Not applicable. No measurements, traces, or baseline metrics were collected due to the orchestrator crash.*

### 12. Final Dataset Location
*   Target Location (Empty): `measurement/results_controlled/`

### 13. Exact Commands Used
```bash
# Executed Pilot
python scripts/run_controlled_experiment.py --pilot
```

### 14. Environment/Configuration Details
*   **Blocker:** DeathStarBench architecture collision. The default `docker-compose.yml` for both `socialNetwork` and `hotelReservation` attempt to bind their respective Jaeger instances to host ports `16686` and `5775`. 
*   **Resolution Required:** The orchestrator must be modified to entirely tear down (`docker-compose down -v`) the Hotel Reservation stack before bringing up the Social Network stack, or the port mappings in the `docker-compose.yml` files must be parameterized to avoid collisions.

### Conclusion
The experimental pipeline machinery has a fatal environment provisioning flaw. **DO NOT collect the 171 runs yet.** We must first patch the orchestration infrastructure to handle clean environment tear-downs between architecture shifts.
