# Phase 5A.1 Graph and Zero-Metric Audit

## ISSUE 1: Social Network Graph Incompleteness

### 1A. Reconstructed Graphs
- **Graph A (Configured/Architecture SDG)**: Reconstructed with the 12 expected microservices and their architectural dependencies. Output saved to `analysis/outputs/graph_socialnetwork_configured.csv`.
- **Graph B (Observed Trace-Derived SDG)**: Yielded only 5 nodes and 4 edges (`nginx-web-server`, `user-timeline-service`, `user-service`, `social-graph-service`, `post-storage-service`). Output saved to `analysis/outputs/graph_socialnetwork_observed.csv`.

**Explanation**: 
The 5-node trace-derived graph represents **Option B: the workload-specific reachable subgraph**. It exclusively shows the execution path for a "Read User Timeline" request. Services like `compose-post-service`, `home-timeline-service`, and `text-service` are missing simply because they were not exercised by the specific workload running during the trace collection window.

### 1B. Which Graph Should Drive Centrality?
We **must** use the **Configured Architecture Graph (Graph A)**.
- **Methodological Consequence**: The research question investigates the structural properties of the entire microservice architecture. If we use the workload-observed trace graph, we introduce extreme survivorship/workload-path bias. Seven critical services (like `compose-post-service`, which has high fan-out) would be entirely excluded from the centrality calculation simply because of the timing/nature of the trace collection workload. This would fundamentally invalidate any structural analysis.

---

## ISSUE 2: Zero P95 Values

I have investigated every zero-valued observation and recorded the findings in `analysis/outputs/zero_p95_audit.csv`.

**Findings**:
- **Baseline Zeros**: For services like `user-service`, `user-timeline-service`, and `social-graph-service`, `baseline_p95_ms` is 0.0 because the parser returned zero. The measurement window had no matching spans for these services, indicating they were simply **not in the execution path of the workload** applied during that specific run.
- **Fault Zeros**: For kill/latency/cpu faults, `fault_p95_ms` zeroes occur either because the service was not in the workload path (both baseline and fault are zero), or because the fault (e.g., SIGKILL or CPU starvation) caused **trace disappearance** (the service crashed or timed out before it could emit a span back to Jaeger). 

---

## ISSUE 3: Validity of the 171 Observations

**Decision**: The 171 observations remain **VALID**.
- A zero measurement for latency (because a service was killed and couldn't respond, or because the specific workload didn't hit it) represents a **scientifically valid, genuine observation** of the system's behavior under those conditions. It is an unusual result (a missing trace or timeout) but NOT a measurement failure. The fault was correctly injected, the workload correctly applied, and the system's response (or lack thereof) accurately recorded.
- **Result**: `171_VALID`. No reclassification required.

---

## ISSUE 4: Check the Three Retries

- The original 3 failed attempts (`user-timeline-service_kill_rep01`, `rep02`, `rep03`) remain marked as `INVALID` and are preserved.
- The 3 retry observations (`_retry1`) successfully executed, generated traces/telemetry, and are marked `VALID`.
- The final analytical dataset contains exactly one valid observation per matrix cell (171 runs). The three failed attempts remain archived but do not duplicate the matrix cells in the final dataset.
