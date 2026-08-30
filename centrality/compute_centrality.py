#!/usr/bin/env python3
"""
compute_centrality.py — Centrality Metrics for the Service Dependency Graph
============================================================================
Computes 7 graph centrality metrics on the SDG built by graph_builder.py,
producing a ranked table of services by structural importance.

Metrics computed (all normalized):
  1. Degree centrality          — total connections (in + out)
  2. In-degree centrality       — how many services call this one
  3. Out-degree centrality      — how many services this one calls
  4. Betweenness centrality     — how often this service lies on shortest paths
  5. Closeness centrality       — average shortest-path distance to all others
  6. Eigenvector centrality     — importance based on connections to important nodes
  7. PageRank                   — random-walk-based importance (damping=0.85)

Plus a composite score: mean of normalized ranks across all 7 metrics.
This composite is exploratory — the primary analysis uses per-metric correlations.

Output:
  - centrality/output/centrality_table.csv
  - centrality/output/centrality_table.json

Usage:
    python centrality/compute_centrality.py [--input FILE] [--output-dir DIR]
"""

import argparse
import json
import sys
from pathlib import Path

import networkx as nx
import pandas as pd


def get_project_root() -> Path:
    """Return the project root (parent of /centrality)."""
    return Path(__file__).resolve().parent.parent


def load_graph(input_file: Path) -> nx.DiGraph:
    """
    Load the SDG from the JSON file produced by graph_builder.py.

    Uses NetworkX's node_link_data format:
    {
        "directed": true,
        "nodes": [...],
        "links": [...]
    }
    """
    print(f"[INFO] Loading SDG from {input_file}...")

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    G = nx.node_link_graph(data)
    print(f"[INFO] Loaded graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def compute_all_centralities(G: nx.DiGraph) -> pd.DataFrame:
    """
    Compute all 7 centrality metrics on the directed graph.

    Each metric returns a dict of {node: value}. We merge them into a
    single DataFrame indexed by service name.

    Special handling:
      - Eigenvector centrality may fail to converge on small/sparse graphs.
        We fall back to numpy-based computation, and if that also fails,
        we use zeros (documented as a limitation).
      - Closeness centrality on DiGraph uses shortest paths from the node.
        For nodes with no outgoing paths, closeness = 0.
    """
    print("\n[INFO] Computing centrality metrics...")

    # 1. Degree centrality (treats DiGraph as undirected for total degree)
    print("  Computing degree centrality...")
    degree_cent = nx.degree_centrality(G)

    # 2. In-degree centrality
    print("  Computing in-degree centrality...")
    in_degree_cent = nx.in_degree_centrality(G)

    # 3. Out-degree centrality
    print("  Computing out-degree centrality...")
    out_degree_cent = nx.out_degree_centrality(G)

    # 4. Betweenness centrality (normalized by default for DiGraph)
    print("  Computing betweenness centrality...")
    betweenness_cent = nx.betweenness_centrality(G, normalized=True)

    # 5. Closeness centrality
    print("  Computing closeness centrality...")
    closeness_cent = nx.closeness_centrality(G)

    # 6. Eigenvector centrality
    print("  Computing eigenvector centrality...")
    try:
        eigenvector_cent = nx.eigenvector_centrality(
            G, max_iter=1000, tol=1e-06
        )
    except nx.PowerIterationFailedConvergence:
        print("  [WARNING] Eigenvector centrality did not converge (power iteration).")
        print("  [INFO] Falling back to numpy-based eigenvector centrality...")
        try:
            eigenvector_cent = nx.eigenvector_centrality_numpy(G)
        except Exception as e:
            print(f"  [WARNING] Numpy eigenvector centrality also failed: {e}")
            print("  [INFO] Setting eigenvector centrality to 0 for all nodes.")
            eigenvector_cent = {node: 0.0 for node in G.nodes()}

    # 7. PageRank (alpha=0.85 is the standard damping factor)
    print("  Computing PageRank...")
    pagerank = nx.pagerank(G, alpha=0.85)

    # Merge all metrics into a DataFrame
    services = sorted(G.nodes())

    data = {
        "service": services,
        "degree": [degree_cent.get(s, 0.0) for s in services],
        "in_degree": [in_degree_cent.get(s, 0.0) for s in services],
        "out_degree": [out_degree_cent.get(s, 0.0) for s in services],
        "betweenness": [betweenness_cent.get(s, 0.0) for s in services],
        "closeness": [closeness_cent.get(s, 0.0) for s in services],
        "eigenvector": [eigenvector_cent.get(s, 0.0) for s in services],
        "pagerank": [pagerank.get(s, 0.0) for s in services],
    }

    df = pd.DataFrame(data)
    return df


def add_ranks(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add rank columns for each centrality metric.

    Ranking: higher centrality value = rank 1 (most central).
    Uses method='min' for ties (tied services get the same rank).
    """
    metrics = ["degree", "in_degree", "out_degree", "betweenness",
               "closeness", "eigenvector", "pagerank"]

    for metric in metrics:
        # Rank in descending order: highest value = rank 1
        rank_col = f"{metric}_rank"
        df[rank_col] = df[metric].rank(ascending=False, method="min").astype(int)

    return df


def add_composite_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute a composite centrality score.

    The composite score is the mean of the normalized ranks across all
    7 metrics. Lower composite score = higher overall centrality.

    This is an EXPLORATORY measure — the primary analysis uses per-metric
    Spearman correlations. The composite score is useful for quick
    identification of structurally central services but may obscure
    metric-specific patterns.

    Normalization: each rank is divided by the number of services (N)
    so all ranks fall in [1/N, 1.0].
    """
    rank_cols = [col for col in df.columns if col.endswith("_rank")]
    n = len(df)

    # Normalize ranks to [0, 1] range
    normalized_ranks = df[rank_cols].div(n)

    # Composite = mean of normalized ranks (lower = more central)
    df["composite_score"] = normalized_ranks.mean(axis=1).round(4)

    # Rank by composite score (lower score = rank 1 = most central)
    df["composite_rank"] = df["composite_score"].rank(
        ascending=True, method="min"
    ).astype(int)

    return df


def print_results(df: pd.DataFrame) -> None:
    """Pretty-print the centrality results table."""
    print("\n" + "=" * 100)
    print("  Centrality Rankings")
    print("=" * 100)

    # Sort by composite rank for display
    display_df = df.sort_values("composite_rank")

    # Select columns for display
    display_cols = [
        "service", "composite_rank",
        "degree", "degree_rank",
        "betweenness", "betweenness_rank",
        "pagerank", "pagerank_rank",
    ]

    # Print with nice formatting
    print(display_df[display_cols].to_string(index=False, float_format="%.4f"))

    print("\n" + "-" * 100)
    print("  Full table (all 7 metrics) saved to output files.")
    print("  Composite score = mean of normalized ranks (lower = more central)")
    print("=" * 100)

    # Highlight top-3 most central services
    top3 = display_df.head(3)
    print("\n  Top 3 most structurally central services:")
    for _, row in top3.iterrows():
        print(f"    {int(row['composite_rank'])}. {row['service']} "
              f"(composite={row['composite_score']:.4f}, "
              f"pagerank={row['pagerank']:.4f}, "
              f"betweenness={row['betweenness']:.4f})")


def save_results(df: pd.DataFrame, output_dir: Path) -> None:
    """Save the centrality table as both CSV and JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # CSV
    csv_path = output_dir / "centrality_table.csv"
    df.to_csv(csv_path, index=False, float_format="%.6f")
    print(f"\n[INFO] Saved CSV: {csv_path}")

    # JSON (orient='records' for list-of-dicts format)
    json_path = output_dir / "centrality_table.json"
    df.to_json(json_path, orient="records", indent=2)
    print(f"[INFO] Saved JSON: {json_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Compute centrality metrics on the Service Dependency Graph"
    )
    parser.add_argument(
        "--input", type=str, default=None,
        help="Path to sdg.json (default: sdg/output/sdg.json)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output directory (default: centrality/output/)",
    )
    args = parser.parse_args()

    project_root = get_project_root()

    input_file = Path(args.input) if args.input else (
        project_root / "sdg" / "output" / "sdg.json"
    )
    output_dir = Path(args.output_dir) if args.output_dir else (
        project_root / "centrality" / "output"
    )

    # Verify input exists
    if not input_file.exists():
        print(f"[ERROR] SDG file not found: {input_file}")
        print("[ERROR] Run sdg/graph_builder.py first to construct the graph.")
        sys.exit(1)

    print("=" * 60)
    print("  Centrality Computation")
    print("=" * 60)

    # Step 1: Load the graph
    G = load_graph(input_file)

    if G.number_of_nodes() == 0:
        print("[ERROR] Graph has no nodes. Cannot compute centrality.")
        sys.exit(1)

    # Step 2: Compute all centrality metrics
    df = compute_all_centralities(G)

    # Step 3: Add rank columns
    df = add_ranks(df)

    # Step 4: Add composite score
    df = add_composite_score(df)

    # Step 5: Print results
    print_results(df)

    # Step 6: Save
    save_results(df, output_dir)

    print("\n[INFO] Centrality computation complete.")
    print("[INFO] Ready for faultinjection/fault_runner.py")


if __name__ == "__main__":
    main()
