# Phase 8.6: Zero-Trace / Zero-Latency Semantics

This document clarifies the physical meaning of `0.0` values appearing in the `baseline_p95_ms` and `fault_p95_ms` columns of the primary dataset.

## Jaeger Extraction Logic

During the measurement windows, `faultinjection/fault_runner.py` queries Jaeger for all traces originating from the gateway (`nginx-web-server` or `frontend`).

The raw JSON payload is processed by `measurement/metrics_collector.py` using the `compute_latency_percentiles(traces)` function (lines 89-114).

```python
    root_durations_us: list[float] = []
    # ... extraction logic ...
    
    if not root_durations_us:
        return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0,
                "mean_ms": 0.0, "count": 0}
```

## Physical Meaning

A `p95_ms` of `0.0` does **not** mean the requests executed instantly. It means that **zero telemetry traces were recorded or successfully extracted during the time window**. 

This phenomenon heavily occurred during `kill` faults targeting the gateway or ingress points. When the entry point is physically dead:
1. Load generator (wrk2) requests simply time out or connection refuse.
2. No Jaeger spans are created because the process that creates them is offline.
3. The query returns an empty list.
4. The extraction script mathematically casts the empty array to `0.0` for all percentiles.

## Impact on Correlation Analysis

If a `0.0` value is blindly used in a mathematical calculation like $\Delta P95 = fault - baseline$, a service that completely crashes (infinite latency / 100% loss) will incorrectly manifest as having "improved" its latency by the baseline amount (e.g., $0 - 25\text{ms} = -25\text{ms}$ degradation). 

This is why Phase 5a correctly added the `baseline_trace_observed` and `fault_trace_observed` boolean flags, verifying that the correlation datasets only used valid numerical latency values where traces actually existed.
