# PHASE 3A.3: Pilot Completion Report

## 1. Complete 12-Run Matrix Status
The pilot matrix has been completed.
- **Social Network (`compose-post-service`)**: 6 valid runs completed (2 kill, 2 latency, 2 cpu).
- **Hotel Reservation (`reservation`)**: 6 runs completed, but data reliability issues persist (see anomalies below).

## 2. Run IDs & Metrics

### Social Network (Valid Runs)
| Timestamp | Fault | Rep | Baseline p95 (ms) | Fault p95 (ms) | Error Rate | Blast Radius | Recovery (s) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `2026-09-19T00:15:49` | kill | 1 | 20.49 | 21.86 | 0.02 | 8 | 1.18 |
| `2026-09-19T00:17:25` | kill | 2 | 23.37 | 1960.65 | 0.08 | 1 | 1.35 |
| `2026-09-19T00:18:57` | latency | 1 | 26.48 | 2573.35 | 0.0 | 11 | 0.09 |
| `2026-09-19T09:50:15` | latency | 1 (Retry) | 22.30 | 2646.24 | 0.0 | 11 | 0.07 |
| `2026-09-19T00:22:08` | cpu | 1 | 26.63 | 18.91 | 0.0 | 0 | 0.14 |
| `2026-09-19T00:24:04` | cpu | 2 | 25.60 | 206.99 | 0.0 | 11 | 0.16 |

### Hotel Reservation (New Pilot Runs)
| Timestamp | Fault | Rep | Baseline p95 (ms) | Fault p95 (ms) | Error Rate | Blast Radius | Recovery (s) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `2026-09-19T09:45:14` | kill | 1 | 0.53 | 0.54 | 0.0 | 0 | 61.68 |
| `2026-09-19T09:52:12` | kill | 2 | 0.46 | 0.49 | 0.0 | 0 | 1.05 |
| `2026-09-19T09:53:44` | latency | 1 | 0.52 | 0.51 | 0.0 | 0 | 0.06 |
| `2026-09-19T09:55:04` | latency | 2 | 0.52 | 0.45 | 0.0 | 0 | 0.07 |
| `2026-09-19T09:56:22` | cpu | 1 | 0.40 | **0.00** | 0.0 | 0 | 0.07 |
| `2026-09-19T09:57:40` | cpu | 2 | 0.46 | 0.50 | 0.0 | 0 | 0.12 |

## 3. Successful Runs
- **Social Network:** All 6 runs produced expected, meaningful metrics (severe latency spikes during latency faults, measurable error rates during kills, wide blast radiuses). 
- **Hotel Reservation:** None of the runs are reliable for scientific analysis.

## 4. Failed/Partial Runs
- Hotel Reservation `cpu` rep 1 (`2026-09-19T09:56:22`) returned `0.0` for Fault P95, indicating an inability to capture traces during the fault window.
- All other Hotel Reservation runs failed to register any meaningful fault impact or blast radius.

## 5. Retries
- Social Network `latency` was retried once (`2026-09-19T09:50:15`) to replace the previously partial/invalid rep 2 run. It succeeded beautifully.
- Hotel Reservation was entirely re-run to fulfill the 6-run requirement after the Jaeger telemetry fix.

## 6-11. Data Overview & Trace Availability
- **Jaeger traces** are actively flowing and being parsed for both architectures.
- **Social Network** metrics are highly dynamic and responsive to faults.
- **Hotel Reservation** metrics are completely static, near zero, and unresponsive.

## 12. Anomalies (Hotel Reservation)
1. **Suspiciously low baselines:** Hotel Reservation p95 latency is uniformly ~0.5ms. This is impossibly fast for a full end-to-end microservice chain, suggesting Jaeger is only tracing the frontend's immediate rejection or caching layer, rather than the deep distributed transaction.
2. **No Fault Impact:** Even when injecting a 500ms network delay or killing the reservation service entirely, the fault P95 remains identical to the baseline (~0.5ms). 
3. **No Error Rates:** During the `kill` faults, the health check explicitly logged HTTP 500 errors (`Hotel search end-to-end — HTTP 500`). Yet, the telemetry parser recorded `0.0` error rate. This proves Hotel Reservation is failing to propagate `error=true` tags to Jaeger when exceptions occur.
4. **0.0 Drop-out:** `cpu` rep 1 experienced a total trace drop-out (0.0 ms) during the fault window.

## 13. Final GO/NO-GO Decision

**DECISION: NO-GO** 🛑

**Reasoning:**
The full 171-run experiment requires BOTH architectures to produce reliable telemetry across all three fault types. While the pipeline is successfully communicating with Hotel Reservation's Jaeger instance, the telemetry data inside Jaeger is scientifically invalid. It fails to capture downstream propagation, fails to register HTTP 500s as errors in traces, and fails to show latency degradation when faults are actively injected.

Running the 171-run experiment now would permanently pollute the dataset with flatlined 0.5ms latency graphs for Hotel Reservation. Further architectural investigation of Hotel Reservation's trace propagation and workload generation is required before proceeding.
