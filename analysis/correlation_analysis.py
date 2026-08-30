#!/usr/bin/env python3
"""
correlation_analysis.py — Spearman Correlation: Centrality vs. Blast Radius
=============================================================================
Computes Spearman's rank correlation between each centrality metric and
each blast radius measure. This is the core statistical test of the project:
does structural position predict actual failure impact?

Inputs:
  - centrality/output/centrality_table.csv
  - measurement/results/experiment_log.csv

Output:
  - analysis/output/correlation_results.csv

Usage:
    python analysis/correlation_analysis.py
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from scipy import stats


def get_project_root() -> Path:
    """Return the project root (parent of /analysis)."""
    return Path(__file__).resolve().parent.parent


def load_centrality(path: Path) -> pd.DataFrame:
    """Load the centrality table."""
    print(f"[INFO] Loading centrality data from {path}...")
    df = pd.read_csv(path)
    print(f"[INFO] Loaded {len(df)} services with centrality metrics")
    return df


def load_experiment_results(path: Path) -> pd.DataFrame:
    """Load the experiment log and compute per-service aggregates."""
    print(f"[INFO] Loading experiment results from {path}...")
    df = pd.read_csv(path)
    print(f"[INFO] Loaded {len(df)} experiment runs")

    # Ensure numeric columns are float
    numeric_cols = [
        "baseline_p95_ms", "fault_p95_ms", "latency_p95_delta_ms",
        "baseline_p99_ms", "fault_p99_ms", "latency_p99_delta_ms",
        "baseline_error_rate", "fault_error_rate", "error_rate_delta",
        "downstream_affected_count", "recovery_time_s",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def aggregate_by_service(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Average the experiment results per service across all fault types
    and repetitions.

    This gives us one row per service with mean blast radius metrics.
    """
    print("[INFO] Aggregating results per service (mean across reps & fault types)...")

    agg = results_df.groupby("service").agg({
        "latency_p95_delta_ms": "mean",
        "latency_p99_delta_ms": "mean",
        "error_rate_delta": "mean",
        "downstream_affected_count": "mean",
        "recovery_time_s": "mean",
        "fault_p95_ms": "mean",
        "fault_p99_ms": "mean",
        "fault_error_rate": "mean",
    }).reset_index()

    # Round for readability
    for col in agg.columns:
        if col != "service":
            agg[col] = agg[col].round(4)

    print(f"[INFO] Aggregated to {len(agg)} services")
    return agg


def compute_spearman_correlations(
    centrality_df: pd.DataFrame,
    blast_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    For each centrality metric × blast radius measure pair, compute
    Spearman's rank correlation (rho) and its p-value.

    Spearman's rho measures monotonic association between rankings.
    Values near +1 mean high centrality → high blast radius (our hypothesis).

    Returns:
        DataFrame with columns:
        centrality_metric, blast_radius_measure, spearman_rho, p_value,
        significant_at_005, n_services
    """
    # Merge centrality and blast radius data on service name
    merged = centrality_df.merge(blast_df, on="service", how="inner")
    n = len(merged)

    print(f"\n[INFO] Merged {n} services for correlation analysis")

    if n < 4:
        print("[WARNING] Very few services for Spearman correlation.")
        print("[WARNING] Results may not be statistically meaningful.")

    # Define metric columns
    centrality_metrics = [
        "degree", "in_degree", "out_degree",
        "betweenness", "closeness", "eigenvector", "pagerank",
        "composite_score",
    ]

    blast_measures = [
        "latency_p95_delta_ms", "latency_p99_delta_ms",
        "error_rate_delta", "downstream_affected_count",
        "recovery_time_s",
    ]

    results = []

    for c_metric in centrality_metrics:
        if c_metric not in merged.columns:
            continue

        for b_measure in blast_measures:
            if b_measure not in merged.columns:
                continue

            x = merged[c_metric].values
            y = merged[b_measure].values

            # Skip if either vector has no variance (all same value)
            if x.std() == 0 or y.std() == 0:
                results.append({
                    "centrality_metric": c_metric,
                    "blast_radius_measure": b_measure,
                    "spearman_rho": 0.0,
                    "p_value": 1.0,
                    "significant_at_005": False,
                    "n_services": n,
                })
                continue

            # Compute Spearman's rank correlation
            rho, p_value = stats.spearmanr(x, y)

            results.append({
                "centrality_metric": c_metric,
                "blast_radius_measure": b_measure,
                "spearman_rho": round(rho, 4),
                "p_value": round(p_value, 4),
                "significant_at_005": p_value < 0.05,
                "n_services": n,
            })

    return pd.DataFrame(results)


def print_results(corr_df: pd.DataFrame) -> None:
    """Pretty-print the correlation results."""
    print("\n" + "=" * 90)
    print("  Spearman Correlation Results: Centrality Metrics vs. Blast Radius")
    print("=" * 90)

    # Sort by absolute rho descending (strongest correlations first)
    sorted_df = corr_df.copy()
    sorted_df["abs_rho"] = sorted_df["spearman_rho"].abs()
    sorted_df = sorted_df.sort_values("abs_rho", ascending=False)

    # Print all results
    print(sorted_df[[
        "centrality_metric", "blast_radius_measure",
        "spearman_rho", "p_value", "significant_at_005",
    ]].to_string(index=False))

    # Highlight significant results
    sig = sorted_df[sorted_df["significant_at_005"]]
    if len(sig) > 0:
        print(f"\n  Significant correlations (p < 0.05): {len(sig)}")
        for _, row in sig.iterrows():
            direction = "positive" if row["spearman_rho"] > 0 else "negative"
            print(f"    {row['centrality_metric']} vs {row['blast_radius_measure']}: "
                  f"rho={row['spearman_rho']:.4f} ({direction}), p={row['p_value']:.4f}")
    else:
        print("\n  No statistically significant correlations found at p < 0.05.")
        print("  This could be due to small sample size or genuinely weak relationships.")

    # Top-3 strongest correlations (regardless of significance)
    print("\n  Top 3 strongest correlations (by |rho|):")
    for _, row in sorted_df.head(3).iterrows():
        sig_marker = " *" if row["significant_at_005"] else ""
        print(f"    {row['centrality_metric']} vs {row['blast_radius_measure']}: "
              f"rho={row['spearman_rho']:.4f}, p={row['p_value']:.4f}{sig_marker}")

    print("=" * 90)


def save_results(corr_df: pd.DataFrame, output_dir: Path) -> None:
    """Save correlation results to CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "correlation_results.csv"
    corr_df.to_csv(path, index=False)
    print(f"\n[INFO] Saved correlation results: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Compute Spearman correlations between centrality and blast radius"
    )
    parser.add_argument(
        "--centrality-file", type=str, default=None,
        help="Path to centrality_table.csv",
    )
    parser.add_argument(
        "--results-file", type=str, default=None,
        help="Path to experiment_log.csv",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output directory (default: analysis/output/)",
    )
    args = parser.parse_args()

    project_root = get_project_root()

    centrality_path = Path(args.centrality_file) if args.centrality_file else (
        project_root / "centrality" / "output" / "centrality_table.csv"
    )
    results_path = Path(args.results_file) if args.results_file else (
        project_root / "measurement" / "results" / "experiment_log.csv"
    )
    output_dir = Path(args.output_dir) if args.output_dir else (
        project_root / "analysis" / "output"
    )

    # Verify inputs exist
    if not centrality_path.exists():
        print(f"[ERROR] Centrality file not found: {centrality_path}")
        sys.exit(1)
    if not results_path.exists():
        print(f"[ERROR] Experiment results not found: {results_path}")
        sys.exit(1)

    print("=" * 60)
    print("  Statistical Correlation Analysis")
    print("=" * 60)

    # Load data
    centrality_df = load_centrality(centrality_path)
    results_df = load_experiment_results(results_path)

    # Aggregate per service
    blast_df = aggregate_by_service(results_df)

    # Compute correlations
    corr_df = compute_spearman_correlations(centrality_df, blast_df)

    # Print and save
    print_results(corr_df)
    save_results(corr_df, output_dir)

    print("\n[INFO] Correlation analysis complete.")
    print("[INFO] Next: python analysis/generate_plots.py")


if __name__ == "__main__":
    main()
