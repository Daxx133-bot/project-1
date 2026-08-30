#!/usr/bin/env python3
"""
generate_plots.py — Publication-Quality Visualizations
========================================================
Generates plots from the correlation analysis results:
  1. Correlation heatmap (centrality × blast radius, colored by Spearman ρ)
  2. Scatter plots for the top-3 strongest correlations
  3. Bar chart comparing composite centrality rank vs. blast radius

Uses seaborn + matplotlib with a clean, publication-friendly style.

Usage:
    python analysis/generate_plots.py
"""

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for script use
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def get_project_root() -> Path:
    """Return the project root (parent of /analysis)."""
    return Path(__file__).resolve().parent.parent


def setup_style():
    """Configure matplotlib/seaborn for clean, publication-quality plots."""
    sns.set_theme(style="whitegrid", font_scale=1.1)
    plt.rcParams.update({
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "font.family": "sans-serif",
        "axes.titlesize": 14,
        "axes.labelsize": 12,
    })


def plot_correlation_heatmap(
    corr_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    """
    Generate a correlation heatmap: centrality metrics (rows) ×
    blast radius measures (columns), colored by Spearman ρ,
    with p-values annotated.
    """
    print("[INFO] Generating correlation heatmap...")

    # Pivot to matrix form
    rho_matrix = corr_df.pivot(
        index="centrality_metric",
        columns="blast_radius_measure",
        values="spearman_rho",
    )

    p_matrix = corr_df.pivot(
        index="centrality_metric",
        columns="blast_radius_measure",
        values="p_value",
    )

    # Create annotation labels: "ρ\n(p=...)"
    annot = rho_matrix.astype(object)
    for idx in annot.index:
        for col in annot.columns:
            rho = rho_matrix.loc[idx, col]
            p = p_matrix.loc[idx, col]
            sig = "*" if p < 0.05 else ""
            annot.loc[idx, col] = f"{rho:.2f}{sig}\n(p={p:.3f})"

    # Rename columns and index for readability
    col_rename = {
        "latency_p95_delta_ms": "Δ Latency p95",
        "latency_p99_delta_ms": "Δ Latency p99",
        "error_rate_delta": "Δ Error Rate",
        "downstream_affected_count": "Blast Radius",
        "recovery_time_s": "Recovery Time",
    }
    idx_rename = {
        "degree": "Degree",
        "in_degree": "In-Degree",
        "out_degree": "Out-Degree",
        "betweenness": "Betweenness",
        "closeness": "Closeness",
        "eigenvector": "Eigenvector",
        "pagerank": "PageRank",
        "composite_score": "Composite",
    }

    rho_matrix = rho_matrix.rename(columns=col_rename, index=idx_rename)
    annot = annot.rename(columns=col_rename, index=idx_rename)

    # Plot
    fig, ax = plt.subplots(figsize=(12, 8))
    sns.heatmap(
        rho_matrix.astype(float),
        annot=annot,
        fmt="",
        cmap="RdBu_r",
        center=0,
        vmin=-1,
        vmax=1,
        linewidths=0.5,
        ax=ax,
        cbar_kws={"label": "Spearman ρ"},
    )

    ax.set_title("Centrality Metrics vs. Failure Impact\n(Spearman Rank Correlation)")
    ax.set_xlabel("Blast Radius Measure")
    ax.set_ylabel("Centrality Metric")

    # Rotate labels for readability
    plt.xticks(rotation=30, ha="right")
    plt.yticks(rotation=0)

    path = output_dir / "correlation_heatmap.png"
    plt.savefig(path)
    plt.close()
    print(f"[INFO] Saved: {path}")


def plot_scatter(
    centrality_df: pd.DataFrame,
    blast_df: pd.DataFrame,
    corr_df: pd.DataFrame,
    output_dir: Path,
    top_n: int = 3,
) -> None:
    """
    Generate scatter plots for the top-N strongest correlations.

    Each plot shows: centrality value (x) vs. blast radius measure (y),
    with service name labels and a trend line.
    """
    print(f"[INFO] Generating scatter plots for top {top_n} correlations...")

    # Sort by absolute rho
    sorted_corr = corr_df.copy()
    sorted_corr["abs_rho"] = sorted_corr["spearman_rho"].abs()
    sorted_corr = sorted_corr.sort_values("abs_rho", ascending=False)

    # Merge data
    merged = centrality_df.merge(blast_df, on="service", how="inner")

    for i, (_, row) in enumerate(sorted_corr.head(top_n).iterrows()):
        c_metric = row["centrality_metric"]
        b_measure = row["blast_radius_measure"]
        rho = row["spearman_rho"]
        p_val = row["p_value"]

        # Human-readable names
        c_label = c_metric.replace("_", " ").title()
        b_label = b_measure.replace("_", " ").replace("ms", "(ms)").replace("  ", " ")

        fig, ax = plt.subplots(figsize=(8, 6))

        # Scatter plot
        ax.scatter(
            merged[c_metric], merged[b_measure],
            s=80, alpha=0.7, edgecolors="w", linewidth=0.5,
            color=sns.color_palette("deep")[i],
        )

        # Add service name labels
        for _, point in merged.iterrows():
            name = point["service"].replace("-service", "").replace("-", " ")
            ax.annotate(
                name,
                (point[c_metric], point[b_measure]),
                fontsize=8,
                ha="left",
                va="bottom",
                alpha=0.8,
            )

        # Add trend line (linear fit for visual reference)
        if len(merged) > 2:
            z = np.polyfit(merged[c_metric], merged[b_measure], 1)
            p = np.poly1d(z)
            x_line = np.linspace(merged[c_metric].min(), merged[c_metric].max(), 50)
            ax.plot(x_line, p(x_line), "--", color="gray", alpha=0.5, linewidth=1)

        sig_marker = " *" if p_val < 0.05 else ""
        ax.set_title(f"{c_label} vs. {b_label}\nSpearman ρ = {rho:.3f}, "
                     f"p = {p_val:.4f}{sig_marker}")
        ax.set_xlabel(c_label)
        ax.set_ylabel(b_label)

        path = output_dir / f"scatter_{c_metric}_vs_{b_measure}.png"
        plt.savefig(path)
        plt.close()
        print(f"[INFO] Saved: {path}")


def plot_composite_bar(
    centrality_df: pd.DataFrame,
    blast_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    """
    Bar chart: composite centrality rank vs. average blast radius
    (downstream affected count) for each service.

    This highlights false positives (high centrality, low blast radius)
    and false negatives (low centrality, high blast radius).
    """
    print("[INFO] Generating composite rank vs. blast radius bar chart...")

    merged = centrality_df.merge(blast_df, on="service", how="inner")
    merged = merged.sort_values("composite_rank")

    # Shorten service names for the plot
    merged["short_name"] = merged["service"].str.replace("-service", "").str.replace("-", " ")

    fig, ax1 = plt.subplots(figsize=(12, 6))

    x = range(len(merged))
    width = 0.35

    # Bar 1: Composite centrality (inverted rank so higher = more central)
    max_rank = merged["composite_rank"].max()
    centrality_bars = ax1.bar(
        [xi - width / 2 for xi in x],
        max_rank - merged["composite_rank"] + 1,  # Invert so higher = more central
        width,
        label="Centrality (inverted rank)",
        color=sns.color_palette("deep")[0],
        alpha=0.8,
    )

    ax1.set_xlabel("Service")
    ax1.set_ylabel("Centrality (inverted rank, higher = more central)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(merged["short_name"], rotation=45, ha="right")

    # Bar 2: Blast radius on secondary axis
    ax2 = ax1.twinx()
    blast_bars = ax2.bar(
        [xi + width / 2 for xi in x],
        merged["downstream_affected_count"],
        width,
        label="Blast Radius (affected services)",
        color=sns.color_palette("deep")[3],
        alpha=0.8,
    )

    ax2.set_ylabel("Blast Radius (avg. affected services)")

    # Combined legend
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")

    ax1.set_title("Composite Centrality Rank vs. Actual Blast Radius per Service")

    path = output_dir / "composite_vs_blast_radius.png"
    plt.savefig(path)
    plt.close()
    print(f"[INFO] Saved: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate publication-quality plots from correlation analysis"
    )
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    project_root = get_project_root()
    output_dir = Path(args.output_dir) if args.output_dir else (
        project_root / "analysis" / "plots"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    corr_path = project_root / "analysis" / "output" / "correlation_results.csv"
    centrality_path = project_root / "centrality" / "output" / "centrality_table.csv"
    results_path = project_root / "measurement" / "results" / "experiment_log.csv"

    for path in [corr_path, centrality_path, results_path]:
        if not path.exists():
            print(f"[ERROR] Required file not found: {path}")
            sys.exit(1)

    corr_df = pd.read_csv(corr_path)
    centrality_df = pd.read_csv(centrality_path)
    results_df = pd.read_csv(results_path)

    # Aggregate blast radius per service
    numeric_cols = ["latency_p95_delta_ms", "latency_p99_delta_ms",
                    "error_rate_delta", "downstream_affected_count", "recovery_time_s",
                    "fault_p95_ms", "fault_p99_ms", "fault_error_rate"]
    for col in numeric_cols:
        if col in results_df.columns:
            results_df[col] = pd.to_numeric(results_df[col], errors="coerce")

    blast_df = results_df.groupby("service").agg({
        col: "mean" for col in numeric_cols if col in results_df.columns
    }).reset_index()

    setup_style()

    # Generate plots
    plot_correlation_heatmap(corr_df, output_dir)
    plot_scatter(centrality_df, blast_df, corr_df, output_dir)
    plot_composite_bar(centrality_df, blast_df, output_dir)

    print(f"\n[INFO] All plots saved to {output_dir}")
    print("[INFO] Next: python analysis/identify_outliers.py")


if __name__ == "__main__":
    main()
