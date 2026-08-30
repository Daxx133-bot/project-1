#!/usr/bin/env python3
"""
trace_collector.py — Collect Distributed Traces from Jaeger
============================================================
Queries Jaeger's HTTP API to retrieve distributed traces generated during
normal load. These traces contain the span-level caller→callee relationships
that we use to build the Service Dependency Graph (SDG).

The collector:
  1. Fetches the list of all registered services from /api/services
  2. For each service, retrieves traces from /api/traces
  3. Deduplicates traces (same trace may appear across multiple services)
  4. Saves raw trace JSON to sdg/raw_traces/

Usage:
    python sdg/trace_collector.py [--jaeger-url URL] [--lookback 2h]
                                   [--limit 1000] [--output-dir DIR]
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests


# ── Defaults ───────────────────────────────────────────────────────────────
DEFAULT_JAEGER_URL = "http://localhost:16686"
DEFAULT_LOOKBACK = "2h"        # How far back to query for traces
DEFAULT_LIMIT = 1000           # Max traces per service query
DEFAULT_OUTPUT_DIR = None      # Set dynamically based on project root


def get_project_root() -> Path:
    """Return the project root (parent of /sdg)."""
    return Path(__file__).resolve().parent.parent


def get_services(jaeger_url: str) -> list[str]:
    """
    Fetch the list of all services that have reported traces to Jaeger.

    Uses the internal /api/services endpoint. While this is technically
    an unofficial API, it's stable and widely used for tooling.

    Returns:
        List of service name strings.
    """
    url = f"{jaeger_url}/api/services"
    print(f"[INFO] Querying services: {url}")

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        services = data.get("data") or []

        # Filter out Jaeger's own internal service
        services = [s for s in services if s != "jaeger-query"]

        print(f"[INFO] Found {len(services)} services: {services}")
        return services

    except requests.RequestException as e:
        print(f"[ERROR] Failed to query Jaeger services: {e}")
        sys.exit(1)


def fetch_traces_for_service(
    jaeger_url: str,
    service: str,
    lookback: str,
    limit: int,
) -> list[dict[str, Any]]:
    """
    Fetch traces for a specific service from Jaeger.

    Each trace object contains:
      - traceID: unique identifier
      - spans: list of span objects with spanID, operationName, duration, etc.
      - processes: dict mapping process keys (p1, p2, ...) to service names

    Args:
        jaeger_url: Base URL for Jaeger query service.
        service: Name of the service to query traces for.
        lookback: How far back to look (e.g., "1h", "2h", "24h").
        limit: Maximum number of traces to return.

    Returns:
        List of trace dictionaries.
    """
    url = f"{jaeger_url}/api/traces"
    params = {
        "service": service,
        "lookback": lookback,
        "limit": limit,
    }

    print(f"  [INFO] Fetching traces for '{service}' (lookback={lookback}, limit={limit})...")

    try:
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        traces = data.get("data") or []
        print(f"  [INFO] Retrieved {len(traces)} traces for '{service}'")
        return traces

    except requests.RequestException as e:
        print(f"  [WARNING] Failed to fetch traces for '{service}': {e}")
        return []


def deduplicate_traces(
    all_traces: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    Deduplicate traces by traceID.

    The same trace appears when querying different services (because a trace
    spans multiple services). We keep only one copy, identified by traceID.

    Args:
        all_traces: List of trace dicts, possibly with duplicates.

    Returns:
        Dictionary mapping traceID → trace dict (deduplicated).
    """
    unique = {}
    for trace in all_traces:
        trace_id = trace.get("traceID")
        if trace_id and trace_id not in unique:
            unique[trace_id] = trace

    return unique


def save_traces(
    traces: dict[str, dict[str, Any]],
    output_dir: Path,
) -> Path:
    """
    Save deduplicated traces to a JSON file.

    File format:
    {
        "metadata": {
            "collected_at": "...",
            "trace_count": N,
            "span_count": M
        },
        "traces": [ ... ]
    }

    Args:
        traces: Dict of traceID → trace dict.
        output_dir: Directory to save the output file.

    Returns:
        Path to the saved file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Count total spans across all traces
    total_spans = sum(
        len(trace.get("spans", []))
        for trace in traces.values()
    )

    # Build the output structure
    output = {
        "metadata": {
            "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "trace_count": len(traces),
            "span_count": total_spans,
        },
        "traces": list(traces.values()),
    }

    output_file = output_dir / "raw_traces.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\n[INFO] Saved {len(traces)} traces ({total_spans} spans) to {output_file}")
    return output_file


def print_trace_summary(traces: dict[str, dict[str, Any]]) -> None:
    """
    Print a summary of the collected traces for sanity checking.

    Shows:
      - Total trace count and span count
      - Services observed across all traces
      - Operations per service
    """
    # Collect all service names and operations from spans
    service_ops: dict[str, set[str]] = {}
    total_spans = 0

    for trace in traces.values():
        # Build process key → service name mapping
        processes = trace.get("processes", {})
        process_map = {
            key: proc.get("serviceName", "unknown")
            for key, proc in processes.items()
        }

        for span in trace.get("spans", []):
            total_spans += 1
            process_key = span.get("processID", "")
            service = process_map.get(process_key, "unknown")
            operation = span.get("operationName", "unknown")

            if service not in service_ops:
                service_ops[service] = set()
            service_ops[service].add(operation)

    print("\n" + "=" * 60)
    print("  Trace Collection Summary")
    print("=" * 60)
    print(f"  Total traces:     {len(traces)}")
    print(f"  Total spans:      {total_spans}")
    print(f"  Unique services:  {len(service_ops)}")
    print()

    # Print per-service breakdown
    print("  Services and their operations:")
    for service in sorted(service_ops.keys()):
        ops = sorted(service_ops[service])
        print(f"    {service}: {len(ops)} operations")
        for op in ops[:5]:  # Show first 5 operations
            print(f"      - {op}")
        if len(ops) > 5:
            print(f"      ... and {len(ops) - 5} more")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Collect distributed traces from Jaeger for SDG construction"
    )
    parser.add_argument(
        "--jaeger-url", default=DEFAULT_JAEGER_URL,
        help=f"Jaeger query URL (default: {DEFAULT_JAEGER_URL})",
    )
    parser.add_argument(
        "--lookback", default=DEFAULT_LOOKBACK,
        help=f"How far back to query (default: {DEFAULT_LOOKBACK})",
    )
    parser.add_argument(
        "--limit", type=int, default=DEFAULT_LIMIT,
        help=f"Max traces per service (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output directory (default: sdg/raw_traces/)",
    )
    args = parser.parse_args()

    project_root = get_project_root()
    output_dir = Path(args.output_dir) if args.output_dir else (
        project_root / "sdg" / "raw_traces"
    )

    print("=" * 60)
    print("  Jaeger Trace Collection")
    print("=" * 60)

    # Step 1: Get all registered services
    services = get_services(args.jaeger_url)

    if not services:
        print("[ERROR] No services found in Jaeger.")
        print("[ERROR] Have you generated any load? Run generate_baseline_load.py first.")
        sys.exit(1)

    # Step 2: Fetch traces for each service
    all_traces: list[dict[str, Any]] = []
    for service in services:
        traces = fetch_traces_for_service(
            args.jaeger_url, service, args.lookback, args.limit
        )
        all_traces.extend(traces)

    if not all_traces:
        print("[ERROR] No traces retrieved from any service.")
        sys.exit(1)

    # Step 3: Deduplicate
    print(f"\n[INFO] Total traces before dedup: {len(all_traces)}")
    unique_traces = deduplicate_traces(all_traces)
    print(f"[INFO] Total traces after dedup:  {len(unique_traces)}")

    # Step 4: Print summary
    print_trace_summary(unique_traces)

    # Step 5: Save to disk
    save_traces(unique_traces, output_dir)

    print("\n[INFO] Trace collection complete. Ready for graph_builder.py")


if __name__ == "__main__":
    main()
