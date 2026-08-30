#!/usr/bin/env python3
"""
run_full_experiment.py — End-to-End Experiment Orchestrator
=============================================================
Single entry point that chains all phases of the experiment:
  1. Deploy the DeathStarBench stack
  2. Health check
  3. Initialize social graph data
  4. Generate baseline load & verify traces
  5. Collect traces & build SDG
  6. Compute centrality metrics
  7. Run fault injection experiments (longest step)
  8. Compute correlations
  9. Generate plots
  10. Identify outliers
  11. Update RESULTS.md

Usage:
    # Full experiment
    python scripts/run_full_experiment.py

    # Quick test (2 services, kill only, 1 rep)
    python scripts/run_full_experiment.py \
        --services compose-post-service,nginx-web-server \
        --faults kill --reps 1

    # Dry run (plan only)
    python scripts/run_full_experiment.py --dry-run

    # Skip deployment (stack already running)
    python scripts/run_full_experiment.py --skip-deploy
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def get_project_root() -> Path:
    """Return the project root (parent of /scripts)."""
    return Path(__file__).resolve().parent.parent


def run_step(name: str, cmd: list[str], cwd: Path, critical: bool = True) -> bool:
    """
    Run a pipeline step as a subprocess.

    Args:
        name: Human-readable step name.
        cmd: Command to execute.
        cwd: Working directory.
        critical: If True, abort the pipeline on failure.

    Returns:
        True if the step succeeded.
    """
    print(f"\n{'=' * 60}")
    print(f"  Step: {name}")
    print(f"  Command: {' '.join(cmd)}")
    print(f"{'=' * 60}\n")

    start = time.time()

    result = subprocess.run(
        cmd,
        cwd=str(cwd),
    )

    elapsed = time.time() - start
    success = result.returncode == 0

    status = "PASSED" if success else "FAILED"
    print(f"\n  [{status}] - {name} ({elapsed:.0f}s)")

    if not success and critical:
        print(f"\n[ABORT] Critical step '{name}' failed. Stopping pipeline.")
        sys.exit(1)

    return success


def main():
    parser = argparse.ArgumentParser(
        description="Run the full microservice failure analysis experiment"
    )
    parser.add_argument(
        "--skip-deploy", action="store_true",
        help="Skip deployment (assume stack is already running)",
    )
    parser.add_argument(
        "--skip-init", action="store_true",
        help="Skip social graph initialization (already done)",
    )
    parser.add_argument(
        "--skip-load", action="store_true",
        help="Skip baseline load generation (traces already in Jaeger)",
    )
    parser.add_argument(
        "--skip-sdg", action="store_true",
        help="Skip SDG construction (already built)",
    )
    parser.add_argument(
        "--skip-centrality", action="store_true",
        help="Skip centrality computation (already computed)",
    )
    parser.add_argument(
        "--skip-faults", action="store_true",
        help="Skip fault injection (only run analysis on existing data)",
    )
    parser.add_argument(
        "--services", type=str, default="",
        help="Comma-separated services for fault injection (default: all)",
    )
    parser.add_argument(
        "--faults", type=str, default="kill,latency",
        help="Comma-separated fault types (default: kill,latency)",
    )
    parser.add_argument(
        "--reps", type=int, default=3,
        help="Repetitions per fault (default: 3)",
    )
    parser.add_argument(
        "--dsb-dir", type=str, default=None,
        help="Path to DeathStarBench repo",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print plan without executing",
    )
    args = parser.parse_args()

    project_root = get_project_root()
    py = sys.executable  # Current Python interpreter

    print("=" * 60)
    print("  Microservice Failure Analysis - Full Experiment")
    print("=" * 60)
    print(f"  Project root: {project_root}")
    print(f"  Python:       {py}")
    print(f"  Time:         {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN] Printing experiment plan...\n")

    steps = []

    # ── Phase 1: Deployment ────────────────────────────────────────────
    if not args.skip_deploy:
        dsb_args = ["--dsb-dir", args.dsb_dir] if args.dsb_dir else []
        steps.append(("1a. Deploy Stack",
                       [py, "infra/setup_env.py"] + dsb_args, True))
        steps.append(("1b. Health Check",
                       [py, "infra/health_check.py"], True))

    if not args.skip_init:
        dsb_args = ["--dsb-dir", args.dsb_dir] if args.dsb_dir else []
        steps.append(("1c. Init Social Graph",
                       [py, "infra/init_social_graph.py"] + dsb_args, True))

    if not args.skip_load:
        steps.append(("1d. Baseline Load",
                       [py, "infra/generate_baseline_load.py",
                        "--mode", "auto", "--duration", "60", "--rate", "50"],
                       True))

    # ── Phase 2: SDG Construction ──────────────────────────────────────
    if not args.skip_sdg:
        steps.append(("2a. Collect Traces",
                       [py, "sdg/trace_collector.py", "--lookback", "2h"], True))
        steps.append(("2b. Build SDG",
                       [py, "sdg/graph_builder.py"], True))

    # ── Phase 3: Centrality ────────────────────────────────────────────
    if not args.skip_centrality:
        steps.append(("3. Compute Centrality",
                       [py, "centrality/compute_centrality.py"], True))

    # ── Phase 4: Fault Injection ───────────────────────────────────────
    if not args.skip_faults:
        fault_cmd = [
            py, "faultinjection/fault_runner.py",
            "--faults", args.faults,
            "--reps", str(args.reps),
        ]
        if args.services:
            fault_cmd += ["--services", args.services]
        if args.dsb_dir:
            fault_cmd += ["--dsb-dir", args.dsb_dir]
        if args.dry_run:
            fault_cmd.append("--dry-run")

        steps.append(("4. Fault Injection & Measurement", fault_cmd, True))

    # ── Phase 6: Analysis ──────────────────────────────────────────────
    steps.append(("6a. Correlation Analysis",
                   [py, "analysis/correlation_analysis.py"], False))
    steps.append(("6b. Generate Plots",
                   [py, "analysis/generate_plots.py"], False))
    steps.append(("6c. Identify Outliers",
                   [py, "analysis/identify_outliers.py"], False))

    # ── Print plan ─────────────────────────────────────────────────────
    print(f"\n  Pipeline: {len(steps)} steps")
    for i, (name, cmd, critical) in enumerate(steps, 1):
        crit = " [CRITICAL]" if critical else ""
        print(f"    {i}. {name}{crit}")

    if args.dry_run:
        print("\n[DRY RUN] Plan printed. Exiting without execution.")
        return

    # ── Execute ────────────────────────────────────────────────────────
    start_time = time.time()

    for name, cmd, critical in steps:
        run_step(name, cmd, project_root, critical)

    total_time = time.time() - start_time
    hours = int(total_time // 3600)
    minutes = int((total_time % 3600) // 60)

    print(f"\n{'=' * 60}")
    print(f"  Experiment Complete!")
    print(f"  Total time: {hours}h {minutes}m")
    print(f"{'=' * 60}")
    print(f"\n  Results:")
    print(f"    Centrality:    centrality/output/centrality_table.csv")
    print(f"    Experiment:    measurement/results/experiment_log.csv")
    print(f"    Correlations:  analysis/output/correlation_results.csv")
    print(f"    Plots:         analysis/plots/")
    print(f"    Outliers:      analysis/output/outlier_analysis.csv")
    print(f"\n  Review: docs/RESULTS.md")


if __name__ == "__main__":
    main()
