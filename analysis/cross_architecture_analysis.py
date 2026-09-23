#!/usr/bin/env python3
"""
cross_architecture_analysis.py
================================
Combines correlation results from both benchmarks:
  - Social Network (12 services, 3 fault types, 2 reps = 72 runs)
  - Hotel Reservation (8 services, 3 fault types, 2 reps = 48 runs)

Produces:
  - analysis/output/cross_arch_correlation_comparison.csv
  - analysis/plots/cross_arch_correlation_bar.png
  
Key comparison: Does hybrid_criticality achieve higher rho than composite_score
in BOTH architectures? This is the core generalizability claim.
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def generate_comparison_table(
    sn_df: pd.DataFrame, hotel_df: pd.DataFrame
) -> pd.DataFrame:
    """Generate side-by-side comparison of correlation results."""
    # Prefix columns
    sn_sub = sn_df.copy()
    sn_sub.rename(columns={"spearman_rho": "rho_sn", "p_value": "p_sn"}, inplace=True)
    
    hotel_sub = hotel_df.copy()
    hotel_sub.rename(columns={"spearman_rho": "rho_hotel", "p_value": "p_hotel"}, inplace=True)
    
    merged = pd.merge(
        sn_sub[["centrality_metric", "blast_radius_measure", "rho_sn", "p_sn"]],
        hotel_sub[["centrality_metric", "blast_radius_measure", "rho_hotel", "p_hotel"]],
        on=["centrality_metric", "blast_radius_measure"],
        how="outer"
    )
    
    # Add significant in both column
    merged["significant_both"] = (merged["p_sn"] < 0.05) & (merged["p_hotel"] < 0.05)
    
    return merged


def plot_comparison(
    merged_df: pd.DataFrame, output_dir: Path, blast_measure: str = "error_rate_delta"
):
    """Generate a grouped bar chart comparing the two architectures."""
    df_plot = merged_df[merged_df["blast_radius_measure"] == blast_measure].copy()
    
    if df_plot.empty:
        print(f"[WARNING] No data for plot with blast measure {blast_measure}")
        return
        
    df_plot = df_plot.melt(
        id_vars=["centrality_metric"],
        value_vars=["rho_sn", "rho_hotel"],
        var_name="architecture",
        value_name="spearman_rho"
    )
    df_plot["architecture"] = df_plot["architecture"].replace({
        "rho_sn": "Social Network",
        "rho_hotel": "Hotel Reservation"
    })
    
    # Convert rho to absolute values for comparison (since magnitude matters)
    df_plot["abs_rho"] = df_plot["spearman_rho"].abs()
    
    # Sort by Social Network abs rho
    order = df_plot[df_plot["architecture"] == "Social Network"].sort_values("abs_rho", ascending=False)["centrality_metric"]

    plt.figure(figsize=(12, 6))
    sns.barplot(
        data=df_plot,
        x="centrality_metric",
        y="abs_rho",
        hue="architecture",
        order=order
    )
    plt.title(f"Cross-Architecture Comparison: Correlation with {blast_measure}")
    plt.ylabel("Absolute Spearman's Rho (|ρ|)")
    plt.xlabel("Centrality Metric")
    plt.xticks(rotation=45, ha="right")
    plt.axhline(y=0.0, color="black", linestyle="-", linewidth=0.5)
    
    # Add significance lines (approximate critical value for n=12 is 0.59, n=8 is 0.73)
    plt.axhline(y=0.59, color="blue", linestyle="--", alpha=0.5, label="Significance Threshold (SN, α=0.05)")
    plt.axhline(y=0.73, color="orange", linestyle="--", alpha=0.5, label="Significance Threshold (Hotel, α=0.05)")
    
    plt.legend()
    plt.tight_layout()
    
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_path = output_dir / "cross_arch_correlation_bar.png"
    plt.savefig(plot_path, dpi=300)
    plt.close()
    
    print(f"[INFO] Saved comparison plot: {plot_path}")


def main():
    parser = argparse.ArgumentParser(description="Cross Architecture Analysis")
    parser.add_argument("--sn-results", type=str, default=None)
    parser.add_argument("--hotel-results", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()
    
    root = get_project_root()
    
    sn_path = Path(args.sn_results) if args.sn_results else (root / "analysis" / "output" / "correlation_results.csv")
    
    # Fix argparse attribute parsing issue
    hotel_path = Path(args.hotel_results) if args.hotel_results else (root / "analysis" / "output" / "hotel" / "correlation_results.csv")
    output_dir = Path(args.output_dir) if args.output_dir else (root / "analysis" / "output")
    
    print("=" * 70)
    print("  Cross Architecture Analysis")
    print("=" * 70)
    
    if not sn_path.exists():
        print(f"[ERROR] SN results not found: {sn_path}")
        sys.exit(1)
    if not hotel_path.exists():
        print(f"[ERROR] Hotel results not found: {hotel_path}")
        sys.exit(1)
        
    sn_df = pd.read_csv(sn_path)
    hotel_df = pd.read_csv(hotel_path)
    
    merged_df = generate_comparison_table(sn_df, hotel_df)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "cross_arch_correlation_comparison.csv"
    merged_df.to_csv(csv_path, index=False)
    print(f"[INFO] Saved comparison table: {csv_path}")
    
    plot_dir = root / "analysis" / "plots"
    plot_comparison(merged_df, plot_dir, blast_measure="error_rate_delta")
    plot_comparison(merged_df, plot_dir, blast_measure="downstream_affected_count")
    
    # Print highlight
    print("\n  Highlights (Significant in BOTH):")
    sig_both = merged_df[merged_df["significant_both"]]
    if not sig_both.empty:
        for _, row in sig_both.iterrows():
            print(f"    - {row['centrality_metric']} -> {row['blast_radius_measure']}:")
            print(f"        SN:    rho={row['rho_sn']:.4f} (p={row['p_sn']:.4f})")
            print(f"        Hotel: rho={row['rho_hotel']:.4f} (p={row['p_hotel']:.4f})")
    else:
        print("    None found.")
        
    print("\n[INFO] Cross-architecture analysis complete.")


if __name__ == "__main__":
    main()
