#!/usr/bin/env python3
"""
metrics_collector.py — Collect Blast Radius Metrics from Jaeger Traces
========================================================================
During a fault injection experiment, this module collects metrics from
Jaeger traces to quantify the "blast radius" — how much damage the fault
caused to the overall system.

Metrics collected:
  1. Tail latency (p95, p99) — from root span durations during baseline
     vs. fault windows.
  2. Error rate — fraction of traces with error tags during each window.
  3. Blast radius (downstream affected count) — number of distinct services
     showing degradation (latency > 2× baseline or new errors) during fault.
  4. Recovery time — measured externally by the fault runner.

Usage:
    This module is imported by fault_runner.py, not run standalone.
"""

import time
from typing import Any

import numpy as np
import requests


DEFAULT_JAEGER_URL = "http://localhost:16686"


def get_traces_in_window(
    jaeger_url: str,
    service: str,
    start_time_us: int,
    end_time_us: int,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """
    Fetch traces from Jaeger within a specific time window.

    Jaeger's /api/traces endpoint supports start/end parameters
    in microseconds since epoch.

    Args:
        jaeger_url: Jaeger query URL.
        service: Service name to query traces for.
        start_time_us: Window start (microseconds since epoch).
        end_time_us: Window end (microseconds since epoch).
        limit: Maximum traces to fetch.

    Returns:
        List of trace dicts from Jaeger.
    """
    try:
        resp = requests.get(
            f"{jaeger_url}/api/traces",
            params={
                "service": service,
                "start": start_time_us,
                "end": end_time_us,
                "limit": limit,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data") or []
    except requests.RequestException as e:
        print(f"  [WARNING] Failed to fetch traces for {service}: {e}")
        return []


def compute_latency_percentiles(
    traces: list[dict[str, Any]],
) -> dict[str, float]:
    """
    Compute p50, p95, and p99 latency from root span durations.

    A root span is identified as a span with no parent references
    (it's the top-level span in a trace). Its duration represents
    the end-to-end request latency.

    Args:
        traces: List of Jaeger trace dicts.

    Returns:
        Dict with keys: p50_ms, p95_ms, p99_ms, mean_ms, count
    """
    root_durations_us: list[float] = []

    for trace in traces:
        spans = trace.get("spans", [])
        for span in spans:
            # Root span: has no CHILD_OF references
            refs = span.get("references", [])
            is_root = not any(r.get("refType") == "CHILD_OF" for r in refs)
            if is_root:
                duration = span.get("duration", 0)
                root_durations_us.append(float(duration))

    if not root_durations_us:
        return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0,
                "mean_ms": 0.0, "count": 0}

    # Convert microseconds to milliseconds
    durations_ms = [d / 1000.0 for d in root_durations_us]

    return {
        "p50_ms": round(float(np.percentile(durations_ms, 50)), 2),
        "p95_ms": round(float(np.percentile(durations_ms, 95)), 2),
        "p99_ms": round(float(np.percentile(durations_ms, 99)), 2),
        "mean_ms": round(float(np.mean(durations_ms)), 2),
        "count": len(durations_ms),
    }


def compute_error_rate(traces: list[dict[str, Any]]) -> float:
    """
    Compute the error rate from traces.

    A trace is considered "errored" if any of its spans has a tag
    "error" set to true, or an "http.status_code" >= 500.

    Args:
        traces: List of Jaeger trace dicts.

    Returns:
        Error rate as a float in [0.0, 1.0].
    """
    if not traces:
        return 0.0

    error_count = 0

    for trace in traces:
        has_error = False
        for span in trace.get("spans", []):
            tags = span.get("tags", [])
            for tag in tags:
                key = tag.get("key", "")
                value = tag.get("value")

                # Check for explicit error tag
                if key == "error" and value is True:
                    has_error = True
                    break

                # Check for HTTP 5xx status
                if key == "http.status_code" and isinstance(value, int) and value >= 500:
                    has_error = True
                    break

            if has_error:
                break

        if has_error:
            error_count += 1

    return round(error_count / len(traces), 4)


def compute_blast_radius(
    jaeger_url: str,
    all_services: list[str],
    faulted_service: str,
    baseline_latencies: dict[str, dict[str, float]],
    fault_start_us: int,
    fault_end_us: int,
    degradation_factor: float = 2.0,
) -> tuple[int, list[str]]:
    """
    Compute the blast radius: how many OTHER services were affected
    by the fault on `faulted_service`.

    A service is considered "affected" if during the fault window:
      - Its p95 latency exceeds `degradation_factor × baseline_p95`
      - OR its error rate increases above baseline

    Args:
        jaeger_url: Jaeger query URL.
        all_services: List of all service names in the SDG.
        faulted_service: The service that was faulted (excluded from count).
        baseline_latencies: Dict of service → latency stats from baseline.
        fault_start_us: Fault window start (microseconds since epoch).
        fault_end_us: Fault window end (microseconds since epoch).
        degradation_factor: Threshold multiplier for latency degradation.

    Returns:
        Tuple of (affected_count, list_of_affected_service_names).
    """
    affected: list[str] = []

    for service in all_services:
        # Skip the faulted service itself — we're measuring collateral damage
        if service == faulted_service:
            continue

        # Skip infrastructure services
        if "jaeger" in service.lower() or "mongo" in service.lower() \
                or "redis" in service.lower() or "memcached" in service.lower():
            continue

        # Get fault-window traces for this service
        fault_traces = get_traces_in_window(
            jaeger_url, service, fault_start_us, fault_end_us
        )

        if not fault_traces:
            continue

        # Compute fault-window metrics
        fault_latency = compute_latency_percentiles(fault_traces)

        # Get baseline metrics for this service
        baseline = baseline_latencies.get(service, {})
        baseline_p95 = baseline.get("p95_ms", 0.0)

        # Check if latency degraded beyond threshold
        if baseline_p95 > 0 and fault_latency["p95_ms"] > degradation_factor * baseline_p95:
            affected.append(service)
            continue

        # Check if error rate increased
        fault_error = compute_error_rate(fault_traces)
        baseline_error = baseline.get("error_rate", 0.0)
        if fault_error > baseline_error + 0.05:  # 5% absolute increase threshold
            affected.append(service)

    return len(affected), affected


def collect_baseline_metrics(
    jaeger_url: str,
    all_services: list[str],
    window_seconds: int = 30,
) -> dict[str, dict[str, float]]:
    """
    Collect baseline latency and error rate for all services.

    Queries Jaeger for traces from the last `window_seconds` seconds,
    which should represent the steady-state baseline.

    Args:
        jaeger_url: Jaeger query URL.
        all_services: List of service names.
        window_seconds: How many seconds of baseline to measure.

    Returns:
        Dict of service → {"p95_ms": ..., "p99_ms": ..., "error_rate": ...}
    """
    now_us = int(time.time() * 1_000_000)
    start_us = now_us - (window_seconds * 1_000_000)

    baselines: dict[str, dict[str, float]] = {}

    for service in all_services:
        traces = get_traces_in_window(jaeger_url, service, start_us, now_us)

        if traces:
            latency = compute_latency_percentiles(traces)
            error_rate = compute_error_rate(traces)
            baselines[service] = {
                "p50_ms": latency["p50_ms"],
                "p95_ms": latency["p95_ms"],
                "p99_ms": latency["p99_ms"],
                "mean_ms": latency["mean_ms"],
                "trace_count": latency["count"],
                "error_rate": error_rate,
            }
        else:
            baselines[service] = {
                "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0,
                "mean_ms": 0.0, "trace_count": 0, "error_rate": 0.0,
            }

    return baselines


def collect_fault_window_metrics(
    jaeger_url: str,
    primary_service: str,
    fault_start_us: int,
    fault_end_us: int,
) -> dict[str, float]:
    """
    Collect metrics for the primary measurement service during the fault window.

    We typically measure using the top-level service (nginx-web-server)
    to get end-to-end impact, but also capture per-service data.

    Args:
        jaeger_url: Jaeger query URL.
        primary_service: Service to measure (usually nginx or the gateway).
        fault_start_us: Fault window start.
        fault_end_us: Fault window end.

    Returns:
        Dict with p95_ms, p99_ms, error_rate, trace_count.
    """
    traces = get_traces_in_window(
        jaeger_url, primary_service, fault_start_us, fault_end_us
    )

    latency = compute_latency_percentiles(traces)
    error_rate = compute_error_rate(traces)

    return {
        "p95_ms": latency["p95_ms"],
        "p99_ms": latency["p99_ms"],
        "mean_ms": latency["mean_ms"],
        "error_rate": error_rate,
        "trace_count": latency["count"],
    }
