#!/usr/bin/env python3
"""
run_hotel_experiment.py — Full Pipeline for Hotel Reservation Benchmark
=======================================================================
Orchestrates the complete 11-step experimental pipeline for the
DeathStarBench Hotel Reservation benchmark:

  Step 1:  Deploy Hotel stack (infra/setup_hotel_env.py)
  Step 2:  Health check (infra/health_check_hotel.py)
  Step 3:  Seed initial data (infra/init_hotel_data.py)
  Step 4:  Generate baseline load (infra/generate_hotel_load.py)
  Step 5:  Collect Jaeger traces (sdg/trace_collector.py)
  Step 6:  Build Hotel SDG (sdg/graph_builder.py)
  Step 7:  Compute centrality + hybrid metric (centrality/compute_centrality.py)
  Step 8:  Run fault injection (faultinjection/fault_runner.py) — ~4 hours
  Step 9:  Correlation analysis (analysis/correlation_analysis.py)
  Step 10: Generate plots (analysis/generate_plots.py)
  Step 11: Identify outliers (analysis/identify_outliers.py)

Usage:
    python scripts/run_hotel_experiment.py --dsb-dir C:\\path\\to\\DeathStarBench
    python scripts/run_hotel_experiment.py --dsb-dir C:\\path\\to\\DSB --skip-deploy
    python scripts/run_hotel_experiment.py --dsb-dir C:\\path\\to\\DSB --dry-run
    python scripts/run_hotel_experiment.py --start-from 8  # skip to fault injection
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

HOTEL_JAEGER_URL = "http://localhost:16687"
HOTEL_BASE_URL = "http://localhost:5000"
HOTEL_TRACE_DIR = PROJECT_ROOT / "sdg" / "raw_traces" / "hotel"
HOTEL_SDG_DIR = PROJECT_ROOT / "sdg" / "output" / "hotel"
HOTEL_CENTRALITY_DIR = PROJECT_ROOT / "centrality" / "output" / "hotel"
HOTEL_RESULTS_DIR = PROJECT_ROOT / "measurement" / "results" / "hotel"
HOTEL_ANALYSIS_DIR = PROJECT_ROOT / "analysis" / "output" / "hotel"
HOTEL_PLOTS_DIR = PROJECT_ROOT / "analysis" / "plots" / "hotel"


def run_step(
    step_num: int,
    description: str,
    cmd: list[str],
    dry_run: bool = False,
    required: bool = True,
) -> bool:
    """Run a pipeline step and return True on success."""
    print(f"\n{'=' * 60}")
    print(f"  Step {step_num}: {description}")
    print(f"{'=' * 60}")

    if dry_run:
        print(f"  [DRY RUN] Would run: {' '.join(str(c) for c in cmd)}")
        return True

    print(f"  Running: {' '.join(str(c) for c in cmd)}")
    result = subprocess.run([str(c) for c in cmd])
    if result.returncode != 0:
        if required:
            print(f"  [FAIL] Step {step_num} failed with exit code {result.returncode}")
            print(f"  Aborting pipeline.")
            sys.exit(result.returncode)
        else:
            print(f"  [WARNING] Step {step_num} exited with code {result.returncode} (non-critical, continuing)")
            return False
    print(f"  [OK] Step {step_num} complete.")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Full pipeline for Hotel Reservation benchmark experiments"
    )
    parser.add_argument(
        "--dsb-dir", type=str, required=False,
        help="Path to DeathStarBench repo (required unless --skip-deploy)",
    )
    parser.add_argument(
        "--skip-deploy", action="store_true",
        help="Skip Steps 1-4 (assume Hotel stack is already running and seeded)",
    )
    parser.add_argument(
        "--start-from", type=int, default=1,
        help="Start from this step number (default: 1)",
    )
    parser.add_argument(
        "--faults", type=str, default="kill,latency,cpu",
        help="Comma-separated fault types (default: kill,latency,cpu)",
    )
    parser.add_argument(
        "--reps", type=int, default=2,
        help="Repetitions per (service, fault) pair (default: 2)",
    )
    parser.add_argument(
        "--rate", type=int, default=50,
        help="Load rate — concurrent users (default: 50)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print commands without executing",
    )
    args = parser.parse_args()

    # Resolve DSB dir
    if args.dsb_dir:
        dsb_dir = Path(args.dsb_dir).resolve()
    else:
        dsb_dir = (PROJECT_ROOT / ".." / "DeathStarBench").resolve()

    py = sys.executable  # current Python interpreter
    start = args.start_from

    print("=" * 60)
    print("  Hotel Reservation Experiment Pipeline")
    print("=" * 60)
    print(f"  DSB dir:      {dsb_dir}")
    print(f"  Fault types:  {args.faults}")
    print(f"  Repetitions:  {args.reps}")
    print(f"  Load rate:    {args.rate} users")
    print(f"  Start from:   Step {start}")
    print(f"  Dry run:      {args.dry_run}")
    print("=" * 60)

    services_in_sdg = 8  # Hotel has 8 measurable services
    fault_count = len(args.faults.split(","))
    total_runs = services_in_sdg * fault_count * args.reps
    est_hours = total_runs * (30 + 60 + 30 + 30) / 3600
    print(f"\n  Total fault injection runs: {total_runs}")
    print(f"  Estimated fault injection time: ~{est_hours:.1f} hours")
    print()

    if args.dry_run:
        print("[DRY RUN] All steps will be printed but not executed.\n")

    # ── Step 1: Deploy Hotel stack ─────────────────────────────────────────
    if start <= 1 and not args.skip_deploy:
        run_step(1, "Deploy Hotel Reservation Stack",
                 [py, PROJECT_ROOT / "infra" / "setup_hotel_env.py",
                  "--dsb-dir", dsb_dir],
                 dry_run=args.dry_run)
    else:
        print("  [SKIP] Step 1: Deploy (--skip-deploy or --start-from)")

    # ── Step 2: Health check ───────────────────────────────────────────────
    if start <= 2 and not args.skip_deploy:
        run_step(2, "Health Check — Hotel Stack",
                 [py, PROJECT_ROOT / "infra" / "health_check_hotel.py",
                  "--base-url", HOTEL_BASE_URL,
                  "--jaeger-url", HOTEL_JAEGER_URL],
                 dry_run=args.dry_run)
    else:
        print("  [SKIP] Step 2: Health check")

    # ── Step 3: Init Hotel data ────────────────────────────────────────────
    if start <= 3 and not args.skip_deploy:
        run_step(3, "Seed Hotel Data (register users + seed traces)",
                 [py, PROJECT_ROOT / "infra" / "init_hotel_data.py",
                  "--base-url", HOTEL_BASE_URL,
                  "--requests", "200"],
                 dry_run=args.dry_run)
    else:
        print("  [SKIP] Step 3: Data seeding")

    # ── Step 4: Baseline load ──────────────────────────────────────────────
    if start <= 4 and not args.skip_deploy:
        run_step(4, "Generate Baseline Load (60s, 50 users)",
                 [py, PROJECT_ROOT / "infra" / "generate_hotel_load.py",
                  "--base-url", HOTEL_BASE_URL,
                  "--duration", "60",
                  "--rate", str(args.rate)],
                 dry_run=args.dry_run)
    else:
        print("  [SKIP] Step 4: Baseline load")

    # ── Step 5: Collect Jaeger traces ──────────────────────────────────────
    if start <= 5:
        HOTEL_TRACE_DIR.mkdir(parents=True, exist_ok=True)
        run_step(5, "Collect Hotel Jaeger Traces",
                 [py, PROJECT_ROOT / "sdg" / "trace_collector.py",
                  "--jaeger-url", HOTEL_JAEGER_URL,
                  "--output-dir", HOTEL_TRACE_DIR],
                 dry_run=args.dry_run)
    else:
        print("  [SKIP] Step 5: Trace collection")

    # ── Step 6: Build Hotel SDG ────────────────────────────────────────────
    if start <= 6:
        HOTEL_SDG_DIR.mkdir(parents=True, exist_ok=True)
        trace_file = HOTEL_TRACE_DIR / "raw_traces.json"
        run_step(6, "Build Hotel Service Dependency Graph",
                 [py, PROJECT_ROOT / "sdg" / "graph_builder.py",
                  "--input", trace_file,
                  "--output-dir", HOTEL_SDG_DIR],
                 dry_run=args.dry_run)
    else:
        print("  [SKIP] Step 6: SDG construction")

    # ── Step 7: Compute centrality ─────────────────────────────────────────
    if start <= 7:
        HOTEL_CENTRALITY_DIR.mkdir(parents=True, exist_ok=True)
        sdg_json = HOTEL_SDG_DIR / "sdg.json"
        run_step(7, "Compute Hotel Centrality (incl. Hybrid Metric)",
                 [py, PROJECT_ROOT / "centrality" / "compute_centrality.py",
                  "--input", sdg_json,
                  "--output-dir", HOTEL_CENTRALITY_DIR],
                 dry_run=args.dry_run)
    else:
        print("  [SKIP] Step 7: Centrality computation")

    # ── Step 8: Fault injection ────────────────────────────────────────────
    if start <= 8:
        HOTEL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"\n{'=' * 60}")
        print(f"  Step 8: Fault Injection (~{est_hours:.1f} hours)")
        print(f"{'=' * 60}")
        print(f"  This will run {total_runs} fault injection experiments.")
        print(f"  It is SAFE to leave this running unattended overnight.")
        print()

        run_step(8, f"Fault Injection — {total_runs} runs",
                 [py, PROJECT_ROOT / "faultinjection" / "fault_runner.py",
                  "--faults", args.faults,
                  "--reps", str(args.reps),
                  "--nginx-url", HOTEL_BASE_URL,
                  "--jaeger-url", HOTEL_JAEGER_URL,
                  "--output-dir", HOTEL_RESULTS_DIR,
                  "--sdg-file", HOTEL_SDG_DIR / "sdg.json",
                  "--dsb-dir", dsb_dir],
                 dry_run=args.dry_run)
    else:
        print("  [SKIP] Step 8: Fault injection")

    # ── Step 9: Correlation analysis ───────────────────────────────────────
    if start <= 9:
        HOTEL_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
        run_step(9, "Hotel Correlation Analysis",
                 [py, PROJECT_ROOT / "analysis" / "correlation_analysis.py",
                  "--centrality-file",
                  HOTEL_CENTRALITY_DIR / "centrality_table.csv",
                  "--results-file",
                  HOTEL_RESULTS_DIR / "experiment_log.csv",
                  "--output-dir", HOTEL_ANALYSIS_DIR],
                 dry_run=args.dry_run)
    else:
        print("  [SKIP] Step 9: Correlation analysis")

    # ── Step 10: Generate plots ────────────────────────────────────────────
    if start <= 10:
        HOTEL_PLOTS_DIR.mkdir(parents=True, exist_ok=True)
        run_step(10, "Generate Hotel Plots",
                 [py, PROJECT_ROOT / "analysis" / "generate_plots.py",
                  "--centrality-file",
                  HOTEL_CENTRALITY_DIR / "centrality_table.csv",
                  "--results-file",
                  HOTEL_RESULTS_DIR / "experiment_log.csv",
                  "--output-dir", HOTEL_PLOTS_DIR],
                 dry_run=args.dry_run, required=False)
    else:
        print("  [SKIP] Step 10: Plot generation")

    # ── Step 11: Identify outliers ─────────────────────────────────────────
    if start <= 11:
        run_step(11, "Identify Hotel Outliers (FP/FN)",
                 [py, PROJECT_ROOT / "analysis" / "identify_outliers.py",
                  "--centrality-file",
                  HOTEL_CENTRALITY_DIR / "centrality_table.csv",
                  "--results-file",
                  HOTEL_RESULTS_DIR / "experiment_log.csv",
                  "--output-dir", HOTEL_ANALYSIS_DIR],
                 dry_run=args.dry_run, required=False)
    else:
        print("  [SKIP] Step 11: Outlier analysis")

    # ── Done ───────────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("  Hotel Reservation Experiment Pipeline Complete!")
    print(f"{'=' * 60}")
    print(f"  Results:     {HOTEL_RESULTS_DIR}")
    print(f"  Centrality:  {HOTEL_CENTRALITY_DIR}")
    print(f"  Analysis:    {HOTEL_ANALYSIS_DIR}")
    print(f"  Plots:       {HOTEL_PLOTS_DIR}")
    print(f"\n  Next step: python analysis/cross_architecture_analysis.py")


if __name__ == "__main__":
    main()
