#!/usr/bin/env python3
"""
fault_runner.py — Fault Injection Experiment Orchestrator
==========================================================
Runs the full fault injection experiment: for each service in the SDG,
inject faults one-at-a-time and measure the blast radius.

Experiment loop per (service, fault_type, repetition):
  1. Start baseline load (wrk2/Locust warm-up)
  2. Collect baseline metrics from Jaeger
  3. Inject fault on the target service
  4. Continue load during fault window
  5. Collect fault-window metrics from Jaeger
  6. Remove fault (restart container for kill; netem auto-expires)
  7. Wait for recovery, run health check
  8. Run pytest integration tests
  9. Log all results

Usage:
    python faultinjection/fault_runner.py [--services S1,S2] [--faults kill,latency]
                                          [--reps 3] [--dry-run]
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import requests

# Add project root to path so we can import sibling packages
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from faultinjection.fault_config import (
    ExperimentConfig, FaultType, FaultSpec, DEFAULT_SPECS, EXCLUDED_SERVICES,
)
from measurement.metrics_collector import (
    collect_baseline_metrics, collect_fault_window_metrics,
    compute_blast_radius,
)
from measurement.results_logger import ExperimentResult, ResultsLogger


from infra.docker_utils import find_docker_executable, get_compose_cmd


def get_project_root() -> Path:
    """Return the project root (parent of /faultinjection)."""
    return Path(__file__).resolve().parent.parent


def get_sdg_services(
    project_root: Path,
    sdg_path: Optional[Path] = None,
    is_hotel: bool = False,
) -> list[str]:
    """
    Load the list of services from the SDG JSON file.

    Only returns services that are in the SDG graph (i.e., microservices
    that appear in traces), excluding infrastructure services.
    """
    if sdg_path is None:
        if is_hotel:
            sdg_path = project_root / "sdg" / "output" / "hotel" / "sdg.json"
        else:
            sdg_path = project_root / "sdg" / "output" / "sdg.json"

    if not sdg_path.exists():
        print(f"[ERROR] SDG file not found: {sdg_path}")
        print("[ERROR] Run sdg/graph_builder.py first.")
        sys.exit(1)

    with open(sdg_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract node IDs from the graph
    nodes = [n["id"] for n in data.get("nodes", [])]

    # Filter out excluded services
    from faultinjection.fault_config_hotel import HOTEL_EXCLUDED_SERVICES
    excluded = HOTEL_EXCLUDED_SERVICES if is_hotel else EXCLUDED_SERVICES
    services = [s for s in nodes if s not in excluded]

    print(f"[INFO] SDG services available for fault injection: {services}")
    return services


def get_container_name(service: str, dsb_dir: str) -> str:
    """
    Resolve the Docker Compose service name to the actual running
    container name.

    Docker Compose prepends the project name (usually the directory name)
    to the container name. E.g., "socialnetwork-compose-post-service-1".
    """
    try:
        docker_exe = find_docker_executable()
        result = subprocess.run(
            [docker_exe, "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, check=True,
        )
        running = result.stdout.strip().split("\n")

        # Find the container whose name contains the service name
        for name in running:
            if service in name:
                return name

        # If no match, return the service name as-is (may work for some setups)
        print(f"  [WARNING] Could not find container for '{service}', using name as-is")
        return service

    except subprocess.CalledProcessError:
        return service


def inject_fault(
    service: str,
    fault_spec: FaultSpec,
    container_name: str,
) -> bool:
    """
    Inject a fault on the specified service.

    Returns True if the fault was injected successfully.
    """
    print(f"  [FAULT] Injecting {fault_spec.description()} on {service}...")

    cmd = fault_spec.pumba_command(container_name)
    print(f"  [FAULT] Command: {' '.join(cmd)}")

    try:
        if fault_spec.fault_type == FaultType.KILL:
            # Kill is instant — run synchronously
            subprocess.run(cmd, check=True, timeout=30)
            print(f"  [FAULT] Container {service} killed.")

        elif fault_spec.fault_type == FaultType.LATENCY:
            # Netem runs for the specified duration — run in background
            # Pumba's netem auto-cleans up after duration expires
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            print(f"  [FAULT] Latency injection started (PID: {process.pid})")
            # Don't wait — let it run while we continue measurement

        elif fault_spec.fault_type == FaultType.CPU:
            # CPU stress runs inside the container — run in background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            print(f"  [FAULT] CPU stress started (PID: {process.pid})")

        return True

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"  [ERROR] Fault injection failed: {e}")
        return False
    except FileNotFoundError:
        print(f"  [ERROR] Docker or Pumba not found. Is Docker running?")
        return False


def restore_service(
    service: str,
    container_name: str,
    fault_type: FaultType,
    dsb_dir: str,
) -> float:
    """
    Restore the service to a healthy state after fault injection.

    For KILL faults: restart the container via docker-compose.
    For LATENCY/CPU faults: they auto-expire (Pumba cleans up netem rules).

    Returns the recovery time in seconds.
    """
    start = time.time()

    if fault_type == FaultType.KILL:
        print(f"  [RESTORE] Restarting killed container {service}...")
        hotel_dir = Path(dsb_dir) / "hotelReservation"
        social_dir = Path(dsb_dir) / "socialNetwork"
        compose_cmd = get_compose_cmd()

        target_dir = social_dir
        if hotel_dir.exists():
            compose_file = hotel_dir / "docker-compose.yml"
            if compose_file.exists() and f"  {service}:" in compose_file.read_text(encoding="utf-8", errors="ignore"):
                target_dir = hotel_dir

        try:
            subprocess.run(
                compose_cmd + ["up", "-d", service],
                cwd=str(target_dir),
                check=True,
                timeout=60,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"  [ERROR] Failed to restart {service}: {e}")

    elif fault_type == FaultType.CPU:
        # Pumba stress auto-expires after the specified duration
        print(f"  [RESTORE] CPU stress (Pumba) auto-expires after {dsb_dir and 'duration' or 'duration'}. "
              f"Waiting for {service} to normalise...")

    else:
        print(f"  [RESTORE] Waiting for {fault_type.value} fault to auto-expire...")

    # Wait for the service to become healthy
    max_wait = 60  # seconds
    docker_exe = find_docker_executable()
    while time.time() - start < max_wait:
        try:
            result = subprocess.run(
                [docker_exe, "inspect", "--format", "{{.State.Running}}", container_name],
                capture_output=True, text=True, check=True,
            )
            if "true" in result.stdout.lower():
                recovery_time = time.time() - start
                print(f"  [RESTORE] {service} recovered in {recovery_time:.1f}s")
                return recovery_time
        except subprocess.CalledProcessError:
            pass

        time.sleep(2)

    recovery_time = time.time() - start
    print(f"  [WARNING] {service} may not have fully recovered ({recovery_time:.1f}s)")
    return recovery_time


def run_health_check(nginx_url: str) -> bool:
    """Quick health check: can we reach Nginx and get a response?"""
    try:
        resp = requests.get(nginx_url, timeout=10)
        return resp.status_code < 500
    except requests.RequestException:
        return False


def run_integration_tests(project_root: Path, is_hotel: bool = False) -> bool:
    """Run integration tests / health checks."""
    try:
        if is_hotel:
            result = subprocess.run(
                [sys.executable, str(project_root / "infra" / "health_check_hotel.py")],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=60,
            )
        else:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-q"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=120,
            )
        passed = result.returncode == 0
        if not passed:
            print(f"  [TESTS] Some tests failed:")
            # Print last 10 lines of output
            for line in result.stdout.strip().split("\n")[-10:]:
                print(f"    {line}")
        return passed
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"  [TESTS] Test run failed: {e}")
        return False


def start_load(
    nginx_url: str,
    duration: int,
    rate: int,
    mode: str,
    project_root: Path,
) -> Optional[subprocess.Popen]:
    """
    Start background load generation for the duration of the experiment.

    Returns the Popen process (for cleanup later).
    """
    if mode == "locust":
        is_hotel = ":5000" in nginx_url
        if is_hotel:
            locustfile = project_root / "infra" / "_locustfile_hotel.py"
            if not locustfile.exists():
                print("  [LOAD] Hotel Locustfile not found. Generating...")
                subprocess.run(
                    [sys.executable, str(project_root / "infra" / "generate_hotel_load.py"),
                     "--duration", "5", "--rate", str(rate)],
                    cwd=str(project_root),
                    capture_output=True,
                )
        else:
            locustfile = project_root / "infra" / "_locustfile_baseline.py"
            if not locustfile.exists():
                print("  [LOAD] Locustfile not found. Generating inline...")
                # Import and run the locust setup
                subprocess.run(
                    [sys.executable, str(project_root / "infra" / "generate_baseline_load.py"),
                     "--mode", "locust", "--duration", "5", "--rate", str(rate),
                     "--skip-verify"],
                    cwd=str(project_root),
                    capture_output=True,
                )

        cmd = [
            sys.executable, "-m", "locust",
            "-f", str(locustfile),
            "--host", nginx_url,
            "--headless",
            "--users", str(rate),
            "--spawn-rate", "10",
            "--run-time", f"{duration}s",
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print(f"  [LOAD] Locust started (PID: {process.pid}), {rate} users for {duration}s")
        return process
    
    elif mode == "wrk2":
        docker_exe = find_docker_executable()
        script = "/wrk2/scripts/social-network/mixed-workload.lua"
        if ":5000" in nginx_url:
            script = "/wrk2/scripts/hotel-reservation/mixed-workload_type_1.lua"
            
        cmd = [
            docker_exe, "run", "--rm",
            "--network", "host",
            "-v", f"{Path(__file__).resolve().parent.parent.parent / 'DeathStarBench' / 'hotelReservation' / 'wrk2' / 'scripts' / 'hotel-reservation' / 'mixed-workload_type_1.lua'}:/wrk2/scripts/hotel-reservation/mixed-workload_type_1.lua",
            "dsb-wrk2",
            "-t", "4",
            "-c", "50",
            "-d", f"{duration}s",
            "-R", str(rate),
            "-L",
            "-s", script,
            nginx_url,
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print(f"  [LOAD] wrk2 started (PID: {process.pid}), {rate} RPS for {duration}s")
        return process

    return None


def run_single_experiment(
    service: str,
    fault_spec: FaultSpec,
    repetition: int,
    config: ExperimentConfig,
    all_services: list[str],
    logger: ResultsLogger,
    project_root: Path,
) -> None:
    """
    Run a single experiment iteration: inject one fault on one service,
    measure the impact, restore, and log results.
    """
    print(f"\n{'=' * 60}")
    print(f"  Experiment: {service} / {fault_spec.fault_type.value} / rep {repetition}")
    print(f"{'=' * 60}")

    container_name = get_container_name(service, config.dsb_dir)

    # ── Step 1: Start baseline load ────────────────────────────────────
    total_duration = config.warmup_seconds + config.fault_duration + 30
    load_process = start_load(
        config.nginx_url, total_duration, config.load_rate,
        config.load_mode, project_root,
    )

    # ── Step 2: Warm up and collect baseline ───────────────────────────
    print(f"  [BASELINE] Warming up for {config.warmup_seconds}s...")
    time.sleep(config.warmup_seconds)

    print("  [BASELINE] Collecting baseline metrics...")
    baseline_metrics = collect_baseline_metrics(
        config.jaeger_url, all_services, window_seconds=config.warmup_seconds
    )

    # Get gateway-level baseline
    is_hotel_exp = (config.output_dir and "hotel" in str(config.output_dir).lower()) or ":5000" in (config.nginx_url or "")
    gateway = "frontend" if is_hotel_exp else "nginx-web-server"
    gateway_baseline = baseline_metrics.get(gateway, {})

    # ── Step 3: Inject fault ───────────────────────────────────────────
    fault_start_us = int(time.time() * 1_000_000)
    fault_injected = inject_fault(service, fault_spec, container_name)

    if not fault_injected:
        print("  [SKIP] Fault injection failed, skipping this run.")
        return

    # ── Step 4: Wait for fault duration ────────────────────────────────
    if fault_spec.fault_type != FaultType.KILL:
        print(f"  [WAIT] Fault active for {config.fault_duration}s...")
        time.sleep(config.fault_duration)
    else:
        # For kill, wait a shorter period — the impact is immediate
        print(f"  [WAIT] Service killed, measuring for {config.fault_duration}s...")
        time.sleep(config.fault_duration)

    fault_end_us = int(time.time() * 1_000_000)

    # ── Step 5: Collect fault-window metrics ───────────────────────────
    print("  [MEASURE] Collecting fault-window metrics...")
    fault_metrics = collect_fault_window_metrics(
        config.jaeger_url, gateway, fault_start_us, fault_end_us,
    )

    # Compute blast radius
    downstream_count, downstream_list = compute_blast_radius(
        config.jaeger_url, all_services, service,
        baseline_metrics, fault_start_us, fault_end_us,
    )

    print(f"  [MEASURE] Blast radius: {downstream_count} services affected")
    if downstream_list:
        print(f"  [MEASURE] Affected: {downstream_list}")

    # ── Step 6: Restore service ────────────────────────────────────────
    recovery_time = restore_service(
        service, container_name, fault_spec.fault_type, config.dsb_dir,
    )

    # ── Step 7: Cooldown and health check ──────────────────────────────
    print(f"  [COOLDOWN] Waiting {config.cooldown_seconds}s...")
    time.sleep(config.cooldown_seconds)

    health_ok = run_health_check(config.nginx_url)
    print(f"  [HEALTH] Health check: {'PASS' if health_ok else 'FAIL'}")

    # ── Step 8: Integration tests ──────────────────────────────────────
    is_hotel = ":5000" in config.nginx_url or "hotel" in str(config.output_dir).lower()
    tests_ok = run_integration_tests(project_root, is_hotel=is_hotel)
    print(f"  [TESTS] Integration tests: {'PASS' if tests_ok else 'FAIL'}")

    # ── Step 9: Log results ────────────────────────────────────────────
    result = ExperimentResult(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        service=service,
        fault_type=fault_spec.fault_type.value,
        repetition=repetition,
        baseline_p95_ms=gateway_baseline.get("p95_ms", 0.0),
        baseline_p99_ms=gateway_baseline.get("p99_ms", 0.0),
        baseline_error_rate=gateway_baseline.get("error_rate", 0.0),
        fault_p95_ms=fault_metrics.get("p95_ms", 0.0),
        fault_p99_ms=fault_metrics.get("p99_ms", 0.0),
        fault_error_rate=fault_metrics.get("error_rate", 0.0),
        downstream_affected_count=downstream_count,
        downstream_affected_services=",".join(downstream_list),
        recovery_time_s=round(recovery_time, 2),
        health_check_pass=health_ok,
        integration_tests_pass=tests_ok,
    )

    logger.log_result(result)

    # Clean up load process
    if load_process:
        load_process.terminate()
        try:
            load_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            load_process.kill()


def main():
    parser = argparse.ArgumentParser(
        description="Run fault injection experiments"
    )
    parser.add_argument(
        "--services", type=str, default="",
        help="Comma-separated list of services to test (default: all SDG services)",
    )
    parser.add_argument(
        "--faults", type=str, default="kill,latency",
        help="Comma-separated fault types: kill,latency,cpu (default: kill,latency)",
    )
    parser.add_argument(
        "--reps", type=int, default=3,
        help="Repetitions per (service, fault) pair (default: 3)",
    )
    parser.add_argument(
        "--rep-index", type=int, default=None,
        help="Specific repetition index to run. If provided, overrides --reps loop to run only this rep.",
    )
    parser.add_argument(
        "--warmup", type=int, default=30,
        help="Warm-up seconds before fault (default: 30)",
    )
    parser.add_argument(
        "--fault-duration", type=int, default=60,
        help="Fault duration in seconds (default: 60)",
    )
    parser.add_argument(
        "--cooldown", type=int, default=30,
        help="Cooldown seconds after fault (default: 30)",
    )
    parser.add_argument(
        "--rate", type=int, default=50,
        help="Load rate — concurrent users for Locust (default: 50)",
    )
    parser.add_argument(
        "--load-mode", choices=["wrk2", "locust"], default="locust",
        help="Load generator (default: locust)",
    )
    parser.add_argument(
        "--nginx-url", default="http://localhost:8080",
        help="Nginx URL (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--jaeger-url", default="http://localhost:16686",
        help="Jaeger URL (default: http://localhost:16686)",
    )
    parser.add_argument(
        "--dsb-dir", type=str, default=None,
        help="Path to DeathStarBench repo",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Results output directory (default: measurement/results/)",
    )
    parser.add_argument(
        "--sdg-file", type=str, default=None,
        help="Path to SDG JSON file (default: auto-detected based on output dir)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print experiment plan without executing",
    )
    args = parser.parse_args()

    project_root = get_project_root()

    # Resolve DSB directory
    dsb_dir = args.dsb_dir or str(
        (project_root / "../DeathStarBench").resolve()
    )

    # Resolve output directory
    output_dir = args.output_dir or str(
        project_root / "measurement" / "results"
    )

    # Parse fault types
    fault_type_map = {
        "kill": FaultType.KILL,
        "latency": FaultType.LATENCY,
        "cpu": FaultType.CPU,
    }
    fault_types = []
    for ft in args.faults.split(","):
        ft = ft.strip().lower()
        if ft in fault_type_map:
            fault_types.append(fault_type_map[ft])
        else:
            print(f"[WARNING] Unknown fault type '{ft}', skipping.")

    # Get services to test
    is_hotel = (output_dir and "hotel" in str(output_dir).lower()) or ":5000" in (args.nginx_url or "")
    sdg_path = Path(args.sdg_file) if args.sdg_file else None
    all_sdg_services = get_sdg_services(project_root, sdg_path=sdg_path, is_hotel=is_hotel)

    if args.services:
        services = [s.strip() for s in args.services.split(",")]
        # Validate
        for s in services:
            if s not in all_sdg_services:
                print(f"[WARNING] Service '{s}' not in SDG, skipping.")
        services = [s for s in services if s in all_sdg_services]
    else:
        services = all_sdg_services

    # Build config
    config = ExperimentConfig(
        services=services,
        fault_types=fault_types,
        repetitions=args.reps,
        warmup_seconds=args.warmup,
        fault_duration=args.fault_duration,
        cooldown_seconds=args.cooldown,
        load_rate=args.rate,
        load_mode=args.load_mode,
        nginx_url=args.nginx_url,
        jaeger_url=args.jaeger_url,
        dsb_dir=dsb_dir,
        output_dir=output_dir,
    )

    # Print experiment plan
    print("=" * 60)
    print("  Fault Injection Experiment Plan")
    print("=" * 60)
    print(f"  Services:     {len(services)} - {services}")
    print(f"  Fault types:  {[ft.value for ft in fault_types]}")
    print(f"  Repetitions:  {config.repetitions}")
    print(f"  Total runs:   {config.total_runs()}")
    print(f"  Est. time:    {config.estimated_time_minutes():.0f} minutes")
    print(f"  Load rate:    {config.load_rate} users ({config.load_mode})")
    print(f"  Output:       {output_dir}")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN] Experiment plan printed. No faults injected.")
        return

    # Initialize logger
    logger = ResultsLogger(output_dir)

    # ── Main experiment loop ───────────────────────────────────────────
    run_number = 0
    total_runs = config.total_runs()

    for service in services:
        for fault_type in fault_types:
            fault_spec = DEFAULT_SPECS[fault_type]

            rep_range = [args.rep_index] if args.rep_index is not None else range(1, config.repetitions + 1)
            for rep in rep_range:
                run_number += 1
                print(f"\n{'=' * 60}")
                print(f"  Run {run_number}/{total_runs}")
                print(f"{'=' * 60}")

                run_single_experiment(
                    service=service,
                    fault_spec=fault_spec,
                    repetition=rep,
                    config=config,
                    all_services=all_sdg_services,
                    logger=logger,
                    project_root=project_root,
                )

    # ── Final summary ──────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"  Experiment Complete")
    print(f"{'=' * 60}")
    print(f"  Total runs executed: {run_number}")
    print(f"  Results saved to:    {output_dir}")
    print(f"  CSV log:             {Path(output_dir) / 'experiment_log.csv'}")
    print(f"\n  Next step: python analysis/correlation_analysis.py")


if __name__ == "__main__":
    main()
