#!/usr/bin/env python3
"""
identify_outliers.py — Find False Positives and False Negatives
================================================================
Identifies services where centrality rank and blast radius rank
diverge significantly:

  - False Positive (FP): High centrality rank but low actual blast radius.
    The graph says this service is critical, but faulting it had little impact.

  - False Negative (FN): Low centrality rank but high actual blast radius.
    The graph says this service is peripheral, but faulting it caused havoc.

Both types of discrepancies are interesting findings — they reveal the
limitations of pure structural analysis and suggest that centrality
metrics may miss certain runtime dynamics.

Usage:
    python analysis/identify_outliers.py
"""

import argparse
import sys
from pathlib import Path

import pandas as pd


def get_project_root() -> Path:
    """Return the project root (parent of /analysis)."""
    return Path(__file__).resolve().parent.parent


def identify_outliers(
    centrality_df: pd.DataFrame,
    blast_df: pd.DataFrame,
    threshold_fraction: float = 0.33,
) -> pd.DataFrame:
    """
    Identify services where centrality rank and blast radius rank diverge.

    Algorithm:
      1. Rank services by composite centrality (already done in centrality_df).
      2. Rank services by average downstream_affected_count (blast radius).
      3. Compute the rank difference: |centrality_rank - blast_rank|.
      4. Flag services where the difference exceeds N/3 (N = number of services).

    Args:
        centrality_df: Centrality table with composite_rank column.
        blast_df: Aggregated blast radius per service.
        threshold_fraction: Fraction of N to use as outlier threshold.

    Returns:
        DataFrame of outlier services with analysis columns.
    """
    # Merge
    merged = centrality_df[["service", "composite_rank", "composite_score"]].merge(
        blast_df[["service", "downstream_affected_count", "latency_p95_delta_ms",
                  "error_rate_delta", "recovery_time_s"]],
        on="service",
        how="inner",
    )

    n = len(merged)
    threshold = max(1, int(n * threshold_fraction))

    # Rank by blast radius (higher affected count = rank 1)
    merged["blast_rank"] = merged["downstream_affected_count"].rank(
        ascending=False, method="min"
    ).astype(int)

    # Compute discrepancy
    merged["rank_diff"] = (merged["composite_rank"] - merged["blast_rank"]).abs()
    merged["is_outlier"] = merged["rank_diff"] > threshold

    # Classify outlier type
    def classify(row):
        if not row["is_outlier"]:
            return "Aligned"
        # FP: high centrality (low rank number) but low blast (high rank number)
        if row["composite_rank"] < row["blast_rank"]:
            return "False Positive (high centrality, low impact)"
        else:
            return "False Negative (low centrality, high impact)"

    merged["outlier_type"] = merged.apply(classify, axis=1)

    return merged.sort_values("rank_diff", ascending=False)


def print_analysis(analysis_df: pd.DataFrame) -> None:
    """Pretty-print the outlier analysis."""
    print("\n" + "=" * 90)
    print("  Outlier Analysis: Centrality Rank vs. Blast Radius Rank")
    print("=" * 90)

    if analysis_df.empty:
        print("  No data available for outlier analysis (empty DataFrame).")
        print("=" * 90)
        return

    # Print all services
    display_cols = [
        "service", "composite_rank", "blast_rank",
        "rank_diff", "downstream_affected_count",
        "outlier_type",
    ]
    print(analysis_df[display_cols].to_string(index=False))

    # Separate outliers
    outliers = analysis_df[analysis_df["is_outlier"]]
    # Cast outlier_type to str to prevent pandas errors when DataFrame is empty or contains NaN objects
    outlier_series = analysis_df["outlier_type"].astype(str)
    fps = analysis_df[outlier_series.str.contains("False Positive")]
    fns = analysis_df[outlier_series.str.contains("False Negative")]

    print(f"\n  Total services:        {len(analysis_df)}")
    print(f"  Outliers:              {len(outliers)}")
    print(f"  False Positives:       {len(fps)}")
    print(f"  False Negatives:       {len(fns)}")
    print(f"  Aligned (non-outlier): {len(analysis_df) - len(outliers)}")

    if len(fps) > 0:
        print("\n  === False Positives (high centrality, low actual impact) ===")
        print("  These services are structurally central but their failure")
        print("  had less impact than expected. Possible reasons:")
        print("    - Redundancy / caching mitigates the failure")
        print("    - Service is called frequently but not on critical paths")
        print("    - Fault tolerance mechanisms (retries, circuit breakers)")
        for _, row in fps.iterrows():
            print(f"\n    {row['service']}:")
            print(f"      Centrality rank: {row['composite_rank']} (high)")
            print(f"      Blast rank:      {row['blast_rank']} (low)")
            print(f"      Affected downstream: {row['downstream_affected_count']:.1f}")

    if len(fns) > 0:
        print("\n  === False Negatives (low centrality, high actual impact) ===")
        print("  These services appear peripheral in the graph but their")
        print("  failure caused significant damage. Possible reasons:")
        print("    - Single point of failure despite few connections")
        print("    - Synchronous dependency on critical path")
        print("    - No fallback / graceful degradation")
        for _, row in fns.iterrows():
            print(f"\n    {row['service']}:")
            print(f"      Centrality rank: {row['composite_rank']} (low)")
            print(f"      Blast rank:      {row['blast_rank']} (high)")
            print(f"      Affected downstream: {row['downstream_affected_count']:.1f}")

    print("\n" + "=" * 90)


def save_analysis(analysis_df: pd.DataFrame, output_dir: Path) -> None:
    """Save the outlier analysis as CSV and markdown."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # CSV
    csv_path = output_dir / "outlier_analysis.csv"
    analysis_df.to_csv(csv_path, index=False)
    print(f"[INFO] Saved CSV: {csv_path}")

    # Markdown table for RESULTS.md
    md_path = output_dir / "outlier_analysis.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("## Outlier Analysis\n\n")
        f.write("Services where centrality rank and blast radius rank diverge significantly.\n\n")
        f.write("| Service | Centrality Rank | Blast Rank | Rank Diff | Downstream Affected | Type |\n")
        f.write("|---|---|---|---|---|---|\n")
        for _, row in analysis_df.iterrows():
            f.write(f"| {row['service']} | {row['composite_rank']} | {row['blast_rank']} | "
                    f"{row['rank_diff']} | {row['downstream_affected_count']:.1f} | "
                    f"{row['outlier_type']} |\n")

    print(f"[INFO] Saved Markdown: {md_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Identify false positive/negative services in centrality predictions"
    )
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    project_root = get_project_root()
    output_dir = Path(args.output_dir) if args.output_dir else (
        project_root / "analysis" / "output"
    )

    # Load data
    centrality_path = project_root / "centrality" / "output" / "centrality_table.csv"
    results_path = project_root / "measurement" / "results" / "experiment_log.csv"

    for path in [centrality_path, results_path]:
        if not path.exists():
            print(f"[ERROR] Required file not found: {path}")
            sys.exit(1)

    centrality_df = pd.read_csv(centrality_path)
    results_df = pd.read_csv(results_path)

    # Aggregate blast radius per service
    for col in ["downstream_affected_count", "latency_p95_delta_ms",
                "error_rate_delta", "recovery_time_s"]:
        if col in results_df.columns:
            results_df[col] = pd.to_numeric(results_df[col], errors="coerce")

    blast_df = results_df.groupby("service").agg({
        "downstream_affected_count": "mean",
        "latency_p95_delta_ms": "mean",
        "error_rate_delta": "mean",
        "recovery_time_s": "mean",
    }).reset_index()

    # Identify outliers
    analysis_df = identify_outliers(centrality_df, blast_df)

    # Print and save
    print_analysis(analysis_df)
    save_analysis(analysis_df, output_dir)

    print("\n[INFO] Outlier analysis complete.")


if __name__ == "__main__":
    main()
