#!/usr/bin/env python3
"""
run_master_pipeline.py — Master Orchestrator for Dual-Benchmark Empirical Pipeline
==================================================================================
Runs the complete empirical pipeline across both architectures:
  Phase 1: Social Network Pipeline
    - Injects remaining fault types (CPU stress) or full suite
    - Computes Centrality + Fan-out Corrected Hybrid Metric
    - Runs Correlation Analysis, Plot Generation, and Outlier Analysis
  Phase 2: Social Network Teardown
    - Shuts down Social Network containers to free RAM and ports
  Phase 3: Hotel Reservation Pipeline
    - Deploys Hotel Reservation stack on ports 5000 / 16687
    - Runs Health Check, Data Seeding, Baseline Load Generation
    - Collects Jaeger traces & builds Service Dependency Graph (SDG)
    - Computes Centrality + Hybrid Criticality Metric
    - Executes Fault Injection (kill, latency, cpu)
    - Runs Correlation Analysis, Plot Generation, and Outlier Analysis
  Phase 4: Cross-Architecture Comparative Analysis
    - Compares Spearman rho across Social Network & Hotel Reservation
    - Validates whether Hybrid Metric generalizes across diverse topologies
    - Generates multi-architecture comparison plots and CSV tables
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_command_step(name: str, cmd: list[str], cwd: Path = PROJECT_ROOT, critical: bool = True) -> bool:
    print(f"\n{'=' * 70}")
    print(f"  [MASTER PIPELINE] Step: {name}")
    print(f"  Command: {' '.join(str(c) for c in cmd)}")
    print(f"{'=' * 70}\n")

    start = time.time()
    result = subprocess.run([str(c) for c in cmd], cwd=str(cwd))
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"\n  [FAILED] {name} exited with code {result.returncode} ({elapsed:.1f}s)")
        if critical:
            print(f"  [ABORT] Critical step failed. Stopping pipeline.")
            sys.exit(result.returncode)
        return False

    print(f"\n  [PASSED] {name} completed in {elapsed:.1f}s")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Master Orchestrator for Dual-Benchmark Empirical Pipeline"
    )
    parser.add_argument(
        "--sn-faults", type=str, default="cpu",
        help="Fault types to run for Social Network (default: 'cpu' since kill & latency already completed)",
    )
    parser.add_argument(
        "--sn-reps", type=int, default=2,
        help="Repetitions for Social Network fault injection (default: 2)",
    )
    parser.add_argument(
        "--hotel-faults", type=str, default="kill,latency,cpu",
        help="Fault types to run for Hotel Reservation (default: kill,latency,cpu)",
    )
    parser.add_argument(
        "--hotel-reps", type=int, default=2,
        help="Repetitions for Hotel Reservation fault injection (default: 2)",
    )
    parser.add_argument(
        "--skip-sn", action="store_true",
        help="Skip Social Network fault injection (jump straight to Hotel or Cross-Arch)",
    )
    parser.add_argument(
        "--skip-hotel", action="store_true",
        help="Skip Hotel Reservation pipeline",
    )
    parser.add_argument(
        "--dsb-dir", type=str, default=None,
        help="Path to DeathStarBench repo (default: ../DeathStarBench)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print plan without executing",
    )
    args = parser.parse_args()

    dsb_dir = Path(args.dsb_dir).resolve() if args.dsb_dir else (PROJECT_ROOT / ".." / "DeathStarBench").resolve()
    py = sys.executable

    print("*" * 70)
    print("  DUAL-BENCHMARK MICROSERVICE FAILURE ANALYSIS PIPELINE")
    print("*" * 70)
    print(f"  Project Root: {PROJECT_ROOT}")
    print(f"  DeathStarBench: {dsb_dir}")
    print(f"  Python: {py}")
    print(f"  Social Network faults: {args.sn_faults} (reps={args.sn_reps})")
    print(f"  Hotel Reservation faults: {args.hotel_faults} (reps={args.hotel_reps})")
    print(f"  Dry Run: {args.dry_run}")
    print("*" * 70)

    if args.dry_run:
        print("\n[DRY RUN] Simulating pipeline execution...\n")

    # ── Phase 1: Social Network Fault Injection & Analysis ─────────────
    if not args.skip_sn:
        print("\n>>> STARTING PHASE 1: Social Network Experiments <<<")
        if args.sn_faults:
            run_command_step(
                "Social Network Fault Injection",
                [py, PROJECT_ROOT / "faultinjection" / "fault_runner.py",
                 "--faults", args.sn_faults,
                 "--reps", str(args.sn_reps),
                 "--dsb-dir", dsb_dir] + (["--dry-run"] if args.dry_run else []),
                critical=True,
            )

        # Centrality with Hybrid Metric
        run_command_step(
            "Social Network Centrality Computation",
            [py, PROJECT_ROOT / "centrality" / "compute_centrality.py"],
            critical=True,
        )

        # Statistical Correlations
        run_command_step(
            "Social Network Correlation Analysis",
            [py, PROJECT_ROOT / "analysis" / "correlation_analysis.py"],
            critical=True,
        )

        # Plots & Outliers
        run_command_step(
            "Social Network Plots",
            [py, PROJECT_ROOT / "analysis" / "generate_plots.py"],
            critical=False,
        )
        run_command_step(
            "Social Network Outlier Identification",
            [py, PROJECT_ROOT / "analysis" / "identify_outliers.py"],
            critical=False,
        )

        # ── Phase 2: Teardown Social Network to free ports and RAM ─────
        if not args.dry_run and not args.skip_hotel:
            print("\n>>> PHASE 2: Tearing down Social Network stack to release resources <<<")
            sn_dir = dsb_dir / "socialNetwork"
            if sn_dir.exists():
                from infra.docker_utils import get_compose_cmd
                subprocess.run(get_compose_cmd() + ["down"], cwd=str(sn_dir), check=False)
                time.sleep(5)
    else:
        print("  [SKIP] Phase 1: Social Network experiments skipped (--skip-sn)")

    # ── Phase 3: Hotel Reservation Pipeline ────────────────────────────
    if not args.skip_hotel:
        print("\n>>> STARTING PHASE 3: Hotel Reservation Pipeline <<<")
        hotel_cmd = [
            py, PROJECT_ROOT / "scripts" / "run_hotel_experiment.py",
            "--dsb-dir", dsb_dir,
            "--faults", args.hotel_faults,
            "--reps", str(args.hotel_reps),
        ]
        if args.dry_run:
            hotel_cmd.append("--dry-run")

        run_command_step(
            "Hotel Reservation Complete Pipeline",
            hotel_cmd,
            critical=True,
        )
    else:
        print("  [SKIP] Phase 3: Hotel Reservation experiments skipped (--skip-hotel)")

    # ── Phase 4: Cross-Architecture Comparative Analysis ───────────────
    if not args.dry_run:
        print("\n>>> STARTING PHASE 4: Cross-Architecture Comparative Analysis <<<")
        run_command_step(
            "Cross-Architecture Comparative Analysis",
            [py, PROJECT_ROOT / "analysis" / "cross_architecture_analysis.py"],
            critical=False,
        )

    print("\n" + "*" * 70)
    print("  ALL EXPERIMENTAL PHASES COMPLETE!")
    print("*" * 70)
    print("  Results available at:")
    print("    - Social Network: measurement/results/ & analysis/output/")
    print("    - Hotel Reservation: measurement/results/hotel/ & analysis/output/hotel/")
    print("    - Cross-Architecture: analysis/output/cross_arch_correlation_comparison.csv")
    print("    - Cross-Arch Figures: analysis/plots/cross_arch_correlation_bar.png")


if __name__ == "__main__":
    main()
