#!/usr/bin/env python3
"""
hybrid_weight_optimizer.py — Grid-Search Optimal Weights for Hybrid Criticality Metric
========================================================================================
Searches all (w1, w2, w3) weight combinations (in steps of 0.1, where w1+w2+w3=1.0)
to find the weights that maximise Spearman rank correlation between hybrid_criticality
and error_rate_delta from the experiment log.

This script is a key part of the academic contribution: it proves that the chosen
weights are empirically optimal, not arbitrarily selected.

Inputs:
  - sdg/output/sdg.json                        (Social Network graph)
  - centrality/output/centrality_table.csv     (pre-computed centrality metrics)
  - measurement/results/experiment_log.csv     (fault injection results)

Outputs:
  - centrality/output/hybrid_weight_grid.csv   (all triplets with their rho, p-value)
  - Prints optimal weights and before/after rank table

Usage:
    python centrality/hybrid_weight_optimizer.py
    python centrality/hybrid_weight_optimizer.py --step 0.05   # finer grid
    python centrality/hybrid_weight_optimizer.py \\
        --graph sdg/output/hotel/sdg.json \\
        --centrality centrality/output/hotel/centrality_table.csv \\
        --results measurement/results/hotel/experiment_log.csv
"""

import argparse
import json
import sys
from itertools import product
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from scipy import stats


def get_project_root() -> Path:
    """Return the project root (parent of /centrality)."""
    return Path(__file__).resolve().parent.parent


def load_graph(path: Path) -> nx.DiGraph:
    """Load the SDG JSON into a NetworkX DiGraph."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return nx.node_link_graph(data)


def load_centrality(path: Path) -> pd.DataFrame:
    """Load centrality table CSV."""
    df = pd.read_csv(path)
    print(f"[INFO] Centrality: {len(df)} services, columns: {list(df.columns)}")
    return df


def load_experiment_results(path: Path) -> pd.DataFrame:
    """Load experiment log and aggregate per service."""
    df = pd.read_csv(path)
    numeric_cols = [
        "latency_p95_delta_ms", "latency_p99_delta_ms",
        "error_rate_delta", "downstream_affected_count", "recovery_time_s",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    agg = df.groupby("service").agg({
        "error_rate_delta": "mean",
        "latency_p95_delta_ms": "mean",
        "downstream_affected_count": "mean",
        "recovery_time_s": "mean",
    }).reset_index()
    print(f"[INFO] Experiment results: {len(agg)} services (aggregated)")
    return agg


def compute_hybrid_for_weights(
    G: nx.DiGraph,
    centrality_df: pd.DataFrame,
    w1: float, w2: float, w3: float,
) -> pd.DataFrame:
    """Compute hybrid criticality score for a specific (w1, w2, w3) triplet."""
    out_degrees = dict(G.out_degree())
    max_out = max(out_degrees.values()) if out_degrees else 1
    if max_out == 0:
        max_out = 1

    df = centrality_df.copy()
    fan_out_map = {n: (out_degrees.get(n, 0) / max_out) for n in G.nodes()}
    df["fan_out_weight"] = df["service"].map(fan_out_map).fillna(0.0)

    df["hybrid_criticality"] = (
        w1 * df["in_degree"]
        + w2 * df["out_degree"] * df["fan_out_weight"]
        + w3 * df["betweenness"]
    )
    return df[["service", "hybrid_criticality"]]


def grid_search(
    G: nx.DiGraph,
    centrality_df: pd.DataFrame,
    blast_df: pd.DataFrame,
    step: float = 0.1,
    blast_measure: str = "error_rate_delta",
) -> pd.DataFrame:
    """
    Search all (w1, w2, w3) triplets where w1+w2+w3=1.0 (within float tolerance).

    For each triplet, compute hybrid score, merge with blast_df, and compute
    Spearman rho against the specified blast_measure.

    Returns a DataFrame sorted by descending |rho|.
    """
    print(f"\n[INFO] Grid search: step={step}, blast_measure={blast_measure}")

    # Generate all triplets that sum to 1.0
    steps = [round(v * step, 6) for v in range(int(1.0 / step) + 1)]
    triplets = [
        (w1, w2, round(1.0 - w1 - w2, 6))
        for w1, w2 in product(steps, steps)
        if 0.0 <= round(1.0 - w1 - w2, 6) <= 1.0
    ]
    print(f"[INFO] Testing {len(triplets)} weight combinations...")

    results = []
    merged_base = centrality_df.merge(blast_df, on="service", how="inner")

    for w1, w2, w3 in triplets:
        hybrid_df = compute_hybrid_for_weights(G, centrality_df, w1, w2, w3)
        merged = merged_base.merge(hybrid_df, on="service", how="inner")

        x = merged["hybrid_criticality"].values
        y = merged[blast_measure].values

        if len(x) < 4 or x.std() == 0 or y.std() == 0:
            results.append({
                "w1": w1, "w2": w2, "w3": w3,
                "spearman_rho": 0.0, "p_value": 1.0,
                "abs_rho": 0.0, "significant": False,
            })
            continue

        rho, p = stats.spearmanr(x, y)
        results.append({
            "w1": w1, "w2": w2, "w3": w3,
            "spearman_rho": round(rho, 4),
            "p_value": round(p, 4),
            "abs_rho": round(abs(rho), 4),
            "significant": p < 0.05,
        })

    result_df = pd.DataFrame(results).sort_values("abs_rho", ascending=False)
    return result_df


def print_optimal_result(
    best_row: pd.Series,
    G: nx.DiGraph,
    centrality_df: pd.DataFrame,
    blast_df: pd.DataFrame,
    composite_rho: float,
) -> None:
    """Print the optimal weights and the before/after rank comparison."""
    w1, w2, w3 = best_row["w1"], best_row["w2"], best_row["w3"]
    rho = best_row["spearman_rho"]
    p = best_row["p_value"]

    print("\n" + "=" * 70)
    print("  OPTIMAL HYBRID WEIGHTS FOUND")
    print("=" * 70)
    print(f"  w1 (in_degree):   {w1}")
    print(f"  w2 (fan_out):     {w2}")
    print(f"  w3 (betweenness): {w3}")
    print(f"  Spearman rho:     {rho:.4f}  (p={p:.4f})")
    print(f"  Composite rho:    {composite_rho:.4f}")
    improvement = (abs(rho) - abs(composite_rho)) / abs(composite_rho) * 100 if composite_rho != 0 else 0
    print(f"  Improvement:      {improvement:+.1f}% over composite_score")
    print("=" * 70)

    # Compute hybrid ranks with optimal weights
    hybrid_df = compute_hybrid_for_weights(G, centrality_df, w1, w2, w3)
    merged = centrality_df[["service", "composite_rank", "composite_score"]].merge(
        hybrid_df, on="service", how="inner"
    )
    merged["hybrid_rank"] = merged["hybrid_criticality"].rank(
        ascending=False, method="min"
    ).astype(int)
    merged = merged.merge(
        blast_df[["service", "downstream_affected_count"]].assign(
            blast_rank=lambda df: df["downstream_affected_count"].rank(
                ascending=False, method="min"
            ).astype(int)
        ),
        on="service", how="inner"
    )

    print("\n  Before/After Rank Comparison (sorted by hybrid_rank):")
    print(f"  {'Service':<35s} {'composite_rank':>15} {'hybrid_rank':>12} {'blast_rank':>11} {'FN_resolved?':>13}")
    print("  " + "-" * 90)
    for _, row in merged.sort_values("hybrid_rank").iterrows():
        fn_was = abs(int(row["composite_rank"]) - int(row["blast_rank"])) >= len(merged) // 3
        fn_now = abs(int(row["hybrid_rank"]) - int(row["blast_rank"])) >= len(merged) // 3
        resolved = "✓ FIXED" if (fn_was and not fn_now) else ("still FN" if fn_now else "")
        print(f"  {row['service']:<35s} {int(row['composite_rank']):>15} "
              f"{int(row['hybrid_rank']):>12} {int(row['blast_rank']):>11} {resolved:>13}")


def main():
    parser = argparse.ArgumentParser(
        description="Grid-search optimal weights for the Hybrid Criticality Metric"
    )
    parser.add_argument("--graph", type=str, default=None,
                        help="Path to sdg.json (default: sdg/output/sdg.json)")
    parser.add_argument("--centrality", type=str, default=None,
                        help="Path to centrality_table.csv (default: centrality/output/centrality_table.csv)")
    parser.add_argument("--results", type=str, default=None,
                        help="Path to experiment_log.csv (default: measurement/results/experiment_log.csv)")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: centrality/output/)")
    parser.add_argument("--step", type=float, default=0.1,
                        help="Grid step size for weights (default: 0.1, use 0.05 for finer search)")
    parser.add_argument("--blast-measure", type=str, default="error_rate_delta",
                        help="Blast radius measure to optimise against (default: error_rate_delta)")
    args = parser.parse_args()

    root = get_project_root()

    graph_path = Path(args.graph) if args.graph else root / "sdg" / "output" / "sdg.json"
    centrality_path = Path(args.centrality) if args.centrality else (
        root / "centrality" / "output" / "centrality_table.csv"
    )
    results_path = Path(args.results) if args.results else (
        root / "measurement" / "results" / "experiment_log.csv"
    )
    output_dir = Path(args.output_dir) if args.output_dir else (
        root / "centrality" / "output"
    )

    # Validate inputs
    for p, name in [(graph_path, "SDG"), (centrality_path, "centrality"),
                    (results_path, "experiment results")]:
        if not p.exists():
            print(f"[ERROR] {name} file not found: {p}")
            sys.exit(1)

    print("=" * 70)
    print("  Hybrid Criticality Weight Optimizer")
    print("=" * 70)

    G = load_graph(graph_path)
    centrality_df = load_centrality(centrality_path)
    blast_df = load_experiment_results(results_path)

    # Baseline: composite_score correlation for comparison
    merged_base = centrality_df.merge(blast_df, on="service", how="inner")
    if "composite_score" in merged_base.columns and args.blast_measure in merged_base.columns:
        x_comp = merged_base["composite_score"].values
        y_blast = merged_base[args.blast_measure].values
        if x_comp.std() > 0 and y_blast.std() > 0:
            comp_rho, _ = stats.spearmanr(x_comp, y_blast)
        else:
            comp_rho = 0.0
    else:
        comp_rho = 0.0
    print(f"\n[INFO] Baseline composite_score rho ({args.blast_measure}): {comp_rho:.4f}")

    # Grid search
    grid_df = grid_search(G, centrality_df, blast_df, step=args.step,
                          blast_measure=args.blast_measure)

    # Save grid results
    output_dir.mkdir(parents=True, exist_ok=True)
    grid_path = output_dir / "hybrid_weight_grid.csv"
    grid_df.to_csv(grid_path, index=False)
    print(f"\n[INFO] Saved grid search results: {grid_path}")

    # Print top-5 triplets
    print("\n  Top 5 weight combinations:")
    print(f"  {'w1':>6} {'w2':>6} {'w3':>6} {'rho':>8} {'p':>8} {'sig':>6}")
    print("  " + "-" * 50)
    for _, row in grid_df.head(5).iterrows():
        sig = "✓" if row["significant"] else "✗"
        print(f"  {row['w1']:>6.2f} {row['w2']:>6.2f} {row['w3']:>6.2f} "
              f"{row['spearman_rho']:>8.4f} {row['p_value']:>8.4f} {sig:>6}")

    # Print optimal result with rank comparison
    best = grid_df.iloc[0]
    print_optimal_result(best, G, centrality_df, blast_df, comp_rho)

    print(f"\n[INFO] Optimal weights for your paper:")
    print(f"  Criticality(v) = {best['w1']} × in_degree(v) + "
          f"{best['w2']} × out_degree(v) × fan_out_weight(v) + "
          f"{best['w3']} × betweenness(v)")
    print(f"\n[INFO] Done. Update compute_centrality.py with: "
          f"w1={best['w1']}, w2={best['w2']}, w3={best['w3']}")


if __name__ == "__main__":
    main()
