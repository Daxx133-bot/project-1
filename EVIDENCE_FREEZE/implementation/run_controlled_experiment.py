#!/usr/bin/env python3
"""
run_controlled_experiment.py — Controlled Experiment Orchestrator
==================================================================
Implements the frozen experimental protocol for the microservice
failure analysis. This script separates historical unstructured runs
from the new perfectly balanced 171-run controlled experiment.

Usage:
    # Run the full 171-run experiment (WARNING: takes ~7 hours)
    python scripts/run_controlled_experiment.py --full

    # Run the pilot validation (1 SN service, 1 HR service, all faults)
    python scripts/run_controlled_experiment.py --pilot

    # Dry run
    python scripts/run_controlled_experiment.py --full --dry-run
"""

import argparse
import subprocess
import sys
import csv
import time
from datetime import datetime
from pathlib import Path

# Matrices
SN_SERVICES = [
    "nginx-web-server", "home-timeline-service", "text-service", 
    "user-mention-service", "url-shorten-service", "media-service", 
    "unique-id-service", "post-storage-service", "social-graph-service", 
    "user-service", "user-timeline-service", "compose-post-service"
]
HR_SERVICES = [
    "frontend", "search", "reservation", "rate", 
    "geo", "profile", "recommendation"
]
FAULTS = ["kill", "latency", "cpu"]
REPS = 3

def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent

def run_preflight(py: str, arch_name: str, project_root: Path):
    print(f"\n[INFO] Running preflight for {arch_name}...")
    try:
        subprocess.run(
            [py, "scripts/preflight_environment.py", "--architecture", arch_name],
            cwd=str(project_root),
            check=True
        )
    except subprocess.CalledProcessError:
        print(f"[ERROR] Preflight failed for {arch_name}. Aborting.")
        sys.exit(1)

def ensure_manifest(manifest_path: Path) -> list:
    """Load or initialize run_manifest.csv"""
    headers = [
        "run_id", "architecture", "service", "fault_type", "repetition",
        "rps", "jaeger_port", "status", "start_time", "end_time",
        "baseline_p95_ms", "fault_p95_ms", "baseline_error_rate",
        "fault_error_rate", "downstream_affected_count", "recovery_time_s", "notes"
    ]
    
    runs = []
    
    if manifest_path.exists():
        print(f"[INFO] Loading existing manifest: {manifest_path}")
        with open(manifest_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                runs.append(row)
        return runs

    print(f"[INFO] Initializing new manifest: {manifest_path}")
    
    for arch, services, rps, jaeger in [("socialnetwork", SN_SERVICES, 1000, 16686), 
                                        ("hotelreservation", HR_SERVICES, 100, 16687)]:
        for svc in services:
            for fault in FAULTS:
                for rep in range(1, REPS + 1):
                    run_id = f"{arch}_{svc}_{fault}_rep{rep:02d}"
                    runs.append({
                        "run_id": run_id, "architecture": arch, "service": svc,
                        "fault_type": fault, "repetition": str(rep),
                        "rps": str(rps), "jaeger_port": str(jaeger), "status": "INCOMPLETE",
                        "start_time": "", "end_time": "", "baseline_p95_ms": "", 
                        "fault_p95_ms": "", "baseline_error_rate": "",
                        "fault_error_rate": "", "downstream_affected_count": "", 
                        "recovery_time_s": "", "notes": ""
                    })

    # Save initial
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(runs)

    return runs

def write_manifest(manifest_path: Path, runs: list):
    headers = [
        "run_id", "architecture", "service", "fault_type", "repetition",
        "rps", "jaeger_port", "status", "start_time", "end_time",
        "baseline_p95_ms", "fault_p95_ms", "baseline_error_rate",
        "fault_error_rate", "downstream_affected_count", "recovery_time_s", "notes"
    ]
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(runs)

def get_latest_metrics_from_log(log_path: Path, run_record: dict) -> dict:
    """Parse experiment_log.csv for the latest run of a specific service/fault/rep"""
    if not log_path.exists():
        return {}
        
    latest_match = {}
    with open(log_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row["service"] == run_record["service"] and 
                row["fault_type"] == run_record["fault_type"] and 
                row["repetition"] == run_record["repetition"]):
                latest_match = row
                
    return latest_match

def operational_qc(metrics: dict, process_ok: bool) -> tuple[str, str]:
    if not process_ok:
        return "FAILED_INFRASTRUCTURE", "process non-zero exit"
        
    if not metrics:
        return "INVALID", "missing experiment_log.csv or missing row"
        
    required_keys = ["baseline_p95_ms", "fault_p95_ms", "baseline_error_rate", "fault_error_rate"]
    for k in required_keys:
        if k not in metrics or metrics[k] == "" or metrics[k] is None:
            return "INVALID", f"missing required telemetry: {k}"
            
    try:
        float(metrics["baseline_p95_ms"])
        float(metrics["fault_p95_ms"])
    except ValueError:
        return "INVALID", "corrupt P95 metrics (non-float)"
        
    return "VALID", "process ok, telemetry present"

def main():
    parser = argparse.ArgumentParser(description="Run controlled failure experiment")
    parser.add_argument("--full", action="store_true", help="Run the full 171-run matrix")
    parser.add_argument("--pilot", action="store_true", help="Run the pilot validation")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without executing")
    args = parser.parse_args()

    if not args.full and not args.pilot:
        print("[ERROR] Must specify either --full or --pilot")
        sys.exit(1)

    project_root = get_project_root()
    py = sys.executable

    output_dir_base = project_root / "measurement" / "results_controlled"
    output_dir_base.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir_base / "run_manifest.csv"

    if args.pilot:
        print("==================================================")
        print("  PILOT VALIDATION PHASE")
        print("==================================================")
        print("Pilot not fully migrated to manifest runner yet. Exiting.")
        sys.exit(0)

    if args.full:
        print("==================================================")
        print("  FULL EXPERIMENT PHASE")
        print("==================================================")

        runs = ensure_manifest(manifest_path)
        
        if args.dry_run:
            print("\n[DRY RUN] Matrix verified.")
            print(f"Total runs: {len(runs)}")
            sn_count = sum(1 for r in runs if r["architecture"] == "socialnetwork")
            hr_count = sum(1 for r in runs if r["architecture"] == "hotelreservation")
            print(f"Social Network: {sn_count}")
            print(f"Hotel Reservation: {hr_count}")
            sys.exit(0)

        # Track valid runs for early QC
        valid_counts = {"socialnetwork": 0, "hotelreservation": 0}
        
        for r in runs:
            if r["status"] == "VALID":
                valid_counts[r["architecture"]] += 1

        def do_execute(run_dict):
            arch = run_dict["architecture"]
            svc = run_dict["service"]
            fault = run_dict["fault_type"]
            rep = run_dict["repetition"]
            rps = run_dict["rps"]
            jaeger = run_dict["jaeger_port"]
            
            output_arch_dir = output_dir_base / arch
            output_arch_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"\n==================================================")
            print(f"  EXECUTING RUN: {run_dict['run_id']}")
            print(f"==================================================")
            
            run_preflight(py, arch, project_root)
            
            cmd = [
                py, str(project_root / "faultinjection" / "fault_runner.py"),
                "--services", svc,
                "--faults", fault,
                "--rep-index", rep,
                "--output-dir", str(output_arch_dir),
                "--warmup", "15",
                "--fault-duration", "30",
                "--cooldown", "30",
                "--rate", str(rps),
                "--load-mode", "wrk2",
                "--jaeger-url", f"http://localhost:{jaeger}"
            ]
            
            if arch == "hotelreservation":
                cmd.extend(["--nginx-url", "http://localhost:5000"])
            else:
                cmd.extend(["--nginx-url", "http://localhost:8080"])
                
            run_dict["start_time"] = datetime.now().isoformat()
            write_manifest(manifest_path, runs)

            start_t = time.time()
            process_res = subprocess.run(cmd, cwd=str(project_root))
            process_ok = process_res.returncode == 0
            
            run_dict["end_time"] = datetime.now().isoformat()
            
            # Operational QC
            log_path = output_arch_dir / "experiment_log.csv"
            metrics = get_latest_metrics_from_log(log_path, run_dict)
            
            status, note = operational_qc(metrics, process_ok)
            
            run_dict["status"] = status
            run_dict["notes"] = note
            if metrics:
                run_dict["baseline_p95_ms"] = metrics.get("baseline_p95_ms", "")
                run_dict["fault_p95_ms"] = metrics.get("fault_p95_ms", "")
                run_dict["baseline_error_rate"] = metrics.get("baseline_error_rate", "")
                run_dict["fault_error_rate"] = metrics.get("fault_error_rate", "")
                run_dict["downstream_affected_count"] = metrics.get("downstream_affected_count", "")
                run_dict["recovery_time_s"] = metrics.get("recovery_time_s", "")
                
            write_manifest(manifest_path, runs)
            
            print(f"  [RUN END] Status: {status} ({note})")

        # Pass 1: Execute INCOMPLETE runs (prioritize unexecuted matrix cells)
        incomplete_runs = [r for r in runs if r["status"] == "INCOMPLETE"]
        for run in incomplete_runs:
            do_execute(run)

        # Pass 2: Retry INVALID and FAILED_INFRASTRUCTURE runs
        retryable_runs = [r for r in runs if r["status"] in ["INVALID", "FAILED_INFRASTRUCTURE"]]
        for orig_run in retryable_runs:
            base_id = orig_run["run_id"]
            if "_retry" in base_id:
                parts = base_id.rsplit("_retry", 1)
                next_retry = f"{parts[0]}_retry{int(parts[1]) + 1}"
            else:
                next_retry = f"{base_id}_retry1"
            
            already_retried = any(r["run_id"] == next_retry for r in runs)
            if already_retried:
                continue

            import copy
            new_run = copy.deepcopy(orig_run)
            new_run["run_id"] = next_retry
            new_run["status"] = "INCOMPLETE"
            new_run["start_time"] = ""
            new_run["end_time"] = ""
            new_run["baseline_p95_ms"] = ""
            new_run["fault_p95_ms"] = ""
            new_run["baseline_error_rate"] = ""
            new_run["fault_error_rate"] = ""
            new_run["downstream_affected_count"] = ""
            new_run["recovery_time_s"] = ""
            new_run["notes"] = ""
            
            runs.append(new_run)
            do_execute(new_run)

if __name__ == "__main__":
    main()
