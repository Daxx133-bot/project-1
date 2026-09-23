# PHASE 3B — EXPERIMENT READINESS REPORT

## 1. Protocol Currently Implemented
Based on `FINAL_EXPERIMENTAL_PROTOCOL.md` and the `fault_runner.py` configuration:
- **Request rate:** 1000 RPS using `wrk2`.
- **Warmup duration:** 15 seconds.
- **Fault duration:** 60 seconds executed by Pumba (but the measurement script waits for 30 seconds).
- **Measurement windows:**
  - **Baseline:** Measured prior to fault injection (last 30s window by default in the metrics collector).
  - **Fault:** Measured over the 30-second window while the fault is actively running.
- **Recovery measurement:** Measured by polling the Docker container state until healthy/running.
- **Repetitions:** 3 repetitions per Service-Fault combination.
- **Fault types:** `kill`, `latency` (500ms), `cpu` (100% on 1 core).
- **Target services:** 19 active services (12 in Social Network, 7 in Hotel Reservation).

## 2. Observed Hotel Reservation Saturation Behavior
At the mandated **1000 RPS**, Hotel Reservation is in a state of severe saturation:
- **Baseline P95:** 908.68 ms
- **Fault P95:** 816.20 ms

To evaluate this, we tested lower load rates on the Hotel Reservation cluster:
- **At 500 RPS:** The system is still completely saturated. The actual throughput maxed out at **~233 RPS**, and average latency exploded to **6.42 seconds** (P99: 9.34s). 
- **At 100 RPS:** The system reached a highly stable state. Throughput matched the target (~98 RPS), and average latency settled at a healthy **64.82 ms** (P99: 308 ms).

**Conclusion:** 1000 RPS is NOT a valid operating point for Hotel Reservation. The untuned Docker Compose deployment has a maximum capacity of ~230 RPS.

## 3. Social Network Baseline Behavior
In contrast to Hotel Reservation, Social Network handles 1000 RPS easily:
- **Baseline P95:** Ranging from 20.49 ms to 26.63 ms.
- **Baseline Error Rate:** 0.0
- **Fault-window behavior:** Clear latency degradation during latency faults (jumping to ~2500 ms) and robust recovery behavior.

Social Network is highly tuned out-of-the-box (e.g., using Nginx proxies with Lua routing and asynchronous Thrift workers), allowing it to easily absorb 1000 RPS. Hotel Reservation's synchronous gRPC/Go tree architecture cannot handle the same raw throughput on a single node.

## 4. Exact P95 Calculation Semantics
Inspection of `measurement/metrics_collector.py` (`compute_latency_percentiles`) reveals that `baseline_p95_ms` and `fault_p95_ms` are calculated over **A. all requests**. 

The code extracts the duration of every root span (span with no parent) fetched from Jaeger in the given time window, unconditionally appending it to the latency distribution without checking if the trace succeeded or failed.

## 5. Error-Rate Calculation Semantics
In `compute_error_rate`, the error rate represents the fraction of traces that contain at least one span with an `error=true` tag or an `http.status_code >= 500` tag. 

## 6. Is 1000 RPS Valid?
**No.** 1000 RPS is scientifically invalid for Hotel Reservation. A baseline that is already failing/saturated (due to severe queuing) cannot cleanly isolate the impact of an injected fault. The noise of architectural overload will completely mask the structural propagation of the fault.

## 7. Is 500 RPS Preferable/Necessary?
**No.** 500 RPS is also invalid for Hotel Reservation, as it exceeds the system's ~230 RPS ceiling, resulting in multi-second request queues. A load of **100 RPS** is scientifically necessary for Hotel Reservation to provide a stable, measurable baseline. (Social Network can remain at 1000 RPS).

## 8. Measurement-Validity Risks (Error & Latency Interaction)
**CRITICAL RISK: Fast-Failure Latency Skew**
Because P95 is calculated over *all* requests (including errors), faults that induce timeouts or panics will artificially lower the calculated P95. 

For example, during the Hotel Reservation validation run, the 500ms latency fault caused the Go Memcached client to exceed its 2ms timeout, resulting in an immediate `log.Panic()`. This generated a highly abbreviated error trace (e.g., 2ms total duration). When these ultra-short "failed" traces are averaged with successful traces, the P95 artificially drops (as observed: dropping from 908ms baseline to 816ms fault). 

The final dataset must not allow a failure-induced reduction in successful-request P95 to be misinterpreted as "reduced" system latency. 

## 9. Required Changes
1. **Measurement Fix:** `compute_latency_percentiles` must be modified to filter out traces that contain errors (i.e., calculating P95 only over *successful* requests). Alternatively, failed requests must be assigned a fixed penalty latency (e.g., the timeout threshold) to accurately represent the degradation of user experience.
2. **Workload Tuning:** The load generator configuration in `fault_runner.py` must decouple the RPS setting for Social Network (1000 RPS) and Hotel Reservation (e.g., 100 RPS).

## 10. FINAL READINESS DECISION

**READY_WITH_MEASUREMENT_FIX**

I have stopped as instructed. The measurement skew must be fixed before proceeding to the 171-run experiment.
