#!/usr/bin/env python3
"""
graph_builder.py — Build Service Dependency Graph from Jaeger Traces
=====================================================================
Parses the raw Jaeger traces collected by trace_collector.py and constructs
a directed Service Dependency Graph (SDG) as a NetworkX DiGraph.

How it works:
  1. For each trace, build a span tree using parentSpanID relationships.
  2. For each parent→child span pair, resolve the service names via the
     trace's "processes" map (processID → serviceName).
  3. If the parent and child belong to different services, that's an edge
     in the SDG: caller_service → callee_service.
  4. Aggregate across all traces: edge weight = call frequency, edge
     attributes include average latency.

Output:
  - sdg/output/sdg.graphml  (for Gephi / visual tools)
  - sdg/output/sdg.json     (for programmatic use)

Usage:
    python sdg/graph_builder.py [--input FILE] [--output-dir DIR]
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import networkx as nx


# ── Expected services in DSB Social Network (for sanity check) ─────────
# These are the microservices that should appear in traces. Storage
# backends (MongoDB, Redis, Memcached) do NOT appear in Jaeger traces
# because they're not instrumented with OpenTracing.
EXPECTED_SERVICES = {
    "nginx-web-server",
    "compose-post-service",
    "text-service",
    "user-mention-service",
    "url-shorten-service",
    "media-service",
    "unique-id-service",
    "user-service",
    "social-graph-service",
    "post-storage-service",
    "user-timeline-service",
    "home-timeline-service",
}


def get_project_root() -> Path:
    """Return the project root (parent of /sdg)."""
    return Path(__file__).resolve().parent.parent


def load_traces(input_file: Path) -> list[dict[str, Any]]:
    """
    Load raw traces from the JSON file produced by trace_collector.py.

    Expected format:
    {
        "metadata": { ... },
        "traces": [
            {
                "traceID": "...",
                "spans": [ { "spanID": ..., "processID": ..., ... } ],
                "processes": { "p1": { "serviceName": "..." }, ... }
            },
            ...
        ]
    }
    """
    print(f"[INFO] Loading traces from {input_file}...")

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    traces = data.get("traces", [])
    metadata = data.get("metadata", {})

    print(f"[INFO] Loaded {len(traces)} traces "
          f"({metadata.get('span_count', '?')} spans)")
    return traces


def extract_edges(
    traces: list[dict[str, Any]],
) -> tuple[dict[tuple[str, str], int], dict[tuple[str, str], list[float]]]:
    """
    Extract directed edges (caller → callee) from trace spans.

    For each trace:
      1. Map spanID → span for quick lookup.
      2. Map processID → serviceName from the trace's processes dict.
      3. For each span that has a "references" field pointing to a parent
         span, determine the parent's service and this span's service.
      4. If they differ, record an edge: parent_service → child_service.

    Returns:
        edge_counts: Dict of (caller, callee) → call count
        edge_latencies: Dict of (caller, callee) → list of durations (μs)
    """
    edge_counts: dict[tuple[str, str], int] = defaultdict(int)
    edge_latencies: dict[tuple[str, str], list[float]] = defaultdict(list)

    for trace in traces:
        # Build the process map: processID → service name
        processes = trace.get("processes", {})
        process_map = {
            key: proc.get("serviceName", "unknown")
            for key, proc in processes.items()
        }

        # Build span index: spanID → span
        spans = trace.get("spans", [])
        span_index = {
            span["spanID"]: span
            for span in spans
            if "spanID" in span
        }

        # For each span, find its parent and check for cross-service call
        for span in spans:
            child_process = span.get("processID", "")
            child_service = process_map.get(child_process, "unknown")
            child_duration = span.get("duration", 0)  # in microseconds

            # Find the parent span via the "references" field
            # Jaeger uses "references" with refType "CHILD_OF"
            references = span.get("references", [])
            for ref in references:
                if ref.get("refType") == "CHILD_OF":
                    parent_span_id = ref.get("spanID")
                    parent_span = span_index.get(parent_span_id)

                    if parent_span:
                        parent_process = parent_span.get("processID", "")
                        parent_service = process_map.get(
                            parent_process, "unknown"
                        )

                        # Only record edge if caller ≠ callee
                        # (same-service spans are internal, not inter-service)
                        if parent_service != child_service:
                            edge = (parent_service, child_service)
                            edge_counts[edge] += 1
                            edge_latencies[edge].append(child_duration)

    return edge_counts, edge_latencies


def build_graph(
    edge_counts: dict[tuple[str, str], int],
    edge_latencies: dict[tuple[str, str], list[float]],
) -> nx.DiGraph:
    """
    Build a NetworkX DiGraph from the extracted edge data.

    Node attributes:
      - name: service name

    Edge attributes:
      - weight: total call count across all traces
      - avg_latency_us: average call latency in microseconds
      - avg_latency_ms: average call latency in milliseconds (for readability)
      - call_count: same as weight (explicit alias)
    """
    G = nx.DiGraph()

    for (caller, callee), count in edge_counts.items():
        latencies = edge_latencies.get((caller, callee), [])
        avg_lat_us = sum(latencies) / len(latencies) if latencies else 0.0
        avg_lat_ms = avg_lat_us / 1000.0

        # Add the edge (nodes are auto-created)
        G.add_edge(
            caller,
            callee,
            weight=count,
            call_count=count,
            avg_latency_us=round(avg_lat_us, 2),
            avg_latency_ms=round(avg_lat_ms, 2),
        )

    return G


def sanity_check(G: nx.DiGraph) -> None:
    """
    Compare the constructed graph against the expected DSB Social Network
    architecture. Flag any discrepancies.

    Checks:
      - Missing expected services (services we expect but didn't observe)
      - Extra services (services we observed but didn't expect)
      - Node and edge counts are within reasonable ranges
    """
    observed = set(G.nodes())

    missing = EXPECTED_SERVICES - observed
    extra = observed - EXPECTED_SERVICES

    print("\n" + "=" * 60)
    print("  SDG Sanity Check")
    print("=" * 60)
    print(f"  Nodes (services):  {G.number_of_nodes()}")
    print(f"  Edges (calls):     {G.number_of_edges()}")
    print(f"  Expected services: {len(EXPECTED_SERVICES)}")
    print(f"  Observed services: {len(observed)}")

    if missing:
        print(f"\n  [WARNING] Missing expected services ({len(missing)}):")
        for svc in sorted(missing):
            print(f"    - {svc}")
        print("  These services may not have been called during the trace window.")
        print("  Try generating more load or increasing --lookback.")

    if extra:
        print(f"\n  [INFO] Extra services not in expected list ({len(extra)}):")
        for svc in sorted(extra):
            print(f"    - {svc}")
        print("  These may be infrastructure services or renamed services.")

    if not missing and not extra:
        print("\n  [OK] All expected services found, no unexpected services.")

    # Degree distribution
    print("\n  Per-service degree:")
    for node in sorted(G.nodes()):
        in_deg = G.in_degree(node)
        out_deg = G.out_degree(node)
        print(f"    {node:30s}  in={in_deg}  out={out_deg}")

    # Edge weight distribution
    print("\n  Top edges by call count:")
    edges_by_weight = sorted(
        G.edges(data=True),
        key=lambda e: e[2].get("weight", 0),
        reverse=True,
    )
    for caller, callee, data in edges_by_weight[:10]:
        print(f"    {caller} -> {callee}: "
              f"count={data['weight']}, avg_latency={data['avg_latency_ms']:.1f}ms")

    print("=" * 60)


def serialize_graph(G: nx.DiGraph, output_dir: Path) -> None:
    """
    Serialize the graph in two formats:
      1. GraphML — for visualization tools (Gephi, yEd)
      2. JSON — for programmatic use in later pipeline stages

    The JSON format uses node-link data:
    {
        "directed": true,
        "nodes": [ { "id": "service-name" }, ... ],
        "links": [ { "source": "A", "target": "B", "weight": 42, ... }, ... ]
    }
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # GraphML
    graphml_path = output_dir / "sdg.graphml"
    nx.write_graphml(G, str(graphml_path))
    print(f"[INFO] Saved GraphML: {graphml_path}")

    # JSON (node-link format)
    json_path = output_dir / "sdg.json"
    graph_data = nx.node_link_data(G)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2)
    print(f"[INFO] Saved JSON:    {json_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Build Service Dependency Graph from Jaeger traces"
    )
    parser.add_argument(
        "--input", type=str, default=None,
        help="Path to raw_traces.json (default: sdg/raw_traces/raw_traces.json)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output directory for graph files (default: sdg/output/)",
    )
    args = parser.parse_args()

    project_root = get_project_root()

    input_file = Path(args.input) if args.input else (
        project_root / "sdg" / "raw_traces" / "raw_traces.json"
    )
    output_dir = Path(args.output_dir) if args.output_dir else (
        project_root / "sdg" / "output"
    )

    # Verify input exists
    if not input_file.exists():
        print(f"[ERROR] Input file not found: {input_file}")
        print("[ERROR] Run trace_collector.py first to collect traces.")
        sys.exit(1)

    print("=" * 60)
    print("  Service Dependency Graph Construction")
    print("=" * 60)

    # Step 1: Load traces
    traces = load_traces(input_file)

    if not traces:
        print("[ERROR] No traces loaded. Cannot build graph.")
        sys.exit(1)

    # Step 2: Extract edges from span relationships
    print("\n[INFO] Extracting service-to-service edges from spans...")
    edge_counts, edge_latencies = extract_edges(traces)
    print(f"[INFO] Found {len(edge_counts)} unique service-to-service edges")

    if not edge_counts:
        print("[ERROR] No inter-service edges found in traces.")
        print("[ERROR] This might mean traces don't contain parent-child relationships.")
        sys.exit(1)

    # Step 3: Build the NetworkX graph
    print("\n[INFO] Building NetworkX DiGraph...")
    G = build_graph(edge_counts, edge_latencies)

    # Step 4: Sanity check against expected architecture
    sanity_check(G)

    # Step 5: Serialize
    print()
    serialize_graph(G, output_dir)

    print("\n[INFO] SDG construction complete.")
    print(f"[INFO] Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print("[INFO] Ready for centrality/compute_centrality.py")


if __name__ == "__main__":
    main()
