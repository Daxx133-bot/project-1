# Zero-Trace / Zero-Latency Forensic Audit

This document traces the exact implementation of latency extraction in `metrics_collector.py` to clarify the physical meaning of a `0.0` value in the dataset.

## Implementation Trace

**Source:** `implementation/metrics_collector.py`
**Function:** `compute_latency_percentiles(traces: list[dict[str, Any]]) -> dict[str, float]`
**Lines:** 101-103

```python
    if not root_durations_us:
        return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0,
                "mean_ms": 0.0, "count": 0}
```

## Scenario Analysis

- **When Jaeger returns no traces:** The `traces` argument is an empty list. The `root_durations_us` list is empty. The function returns exact `0.0` values.
- **When Jaeger returns an empty payload:** Same as above.
- **When a gateway crashes:** The entry point service is dead. Load generator requests timeout. No telemetry spans are ever generated or flushed. The Jaeger query returns empty. The function returns exact `0.0`.
- **When no matching span exists:** E.g., no root span found. `root_durations_us` is empty. The function returns exact `0.0`.
- **When latency is truly zero:** Physically impossible for a networked service, but theoretically, if a span had `duration: 0`, `root_durations_us` would contain `[0.0]`, and the percentiles would compute to `0.0` but `count` would be `>0`.

## Semantics Conclusion

In this dataset, a `p95_ms` of `0.0` means **missing telemetry / failed query / empty trace set**. 
It specifically does **not** mean the service executed the request instantaneously. 

It is structurally invalid to interpret `0.0` as "zero failure impact" or "infinite latency." It strictly means "no data." The `primary_analysis_dataset.csv` explicitly recognizes this by providing the `baseline_trace_observed` and `fault_trace_observed` boolean flags (where `p95_ms != 0`) to prevent blindly subtracting `0.0` from valid latencies during delta calculations.
