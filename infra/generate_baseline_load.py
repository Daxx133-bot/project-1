#!/usr/bin/env python3
"""
generate_baseline_load.py — Generate Load and Confirm Traces
=============================================================
Generates baseline traffic against the Social Network to produce Jaeger traces.

Two modes:
  1. wrk2 (preferred): Builds and runs wrk2 inside Docker, using DSB's own
     Lua workload scripts. Gives constant-throughput, open-loop load — faithful
     to how the benchmark is designed.
  2. Locust (fallback): Pure-Python load generator. Use if wrk2 Docker build
     fails or if you need to run from Windows without Docker.

After load generation, the script queries Jaeger to confirm traces were captured.

Usage:
    python infra/generate_baseline_load.py [--mode wrk2|locust]
                                            [--duration 60] [--rate 50]
                                            [--dsb-dir PATH]
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Defaults ───────────────────────────────────────────────────────────────
DEFAULT_NGINX_URL = "http://localhost:8080"
DEFAULT_JAEGER_URL = "http://localhost:16686"
DEFAULT_DURATION = 60       # seconds of load
DEFAULT_RATE = 50           # requests per second
DEFAULT_DSB_RELATIVE_PATH = "../DeathStarBench"


def get_project_root() -> Path:
    """Return the project root (parent of /infra)."""
    return Path(__file__).resolve().parent.parent


from infra.docker_utils import find_docker_executable


# ============================================================================
# Mode 1: wrk2 via Docker
# ============================================================================

def build_wrk2_image(dsb_dir: Path) -> bool:
    """
    Build the wrk2 Docker image from our Dockerfile.
    The build context must be the socialNetwork directory so COPY wrk2/ works.
    """
    dockerfile = get_project_root() / "infra" / "Dockerfile.wrk2"
    context = dsb_dir
    docker_exe = find_docker_executable()

    print("[INFO] Building wrk2 Docker image...")
    try:
        subprocess.run(
            [
                docker_exe, "build",
                "-t", "dsb-wrk2",
                "-f", str(dockerfile),
                str(context),
            ],
            check=True,
            timeout=300,
        )
        print("[INFO] wrk2 image built successfully.")
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"[ERROR] Failed to build wrk2 image: {e}")
        return False


def run_wrk2_load(
    duration: int,
    rate: int,
    nginx_url: str,
    script: str = "/wrk2/scripts/social-network/mixed-workload.lua",
) -> bool:
    """
    Run wrk2 inside Docker targeting the Nginx gateway.

    We use --network host so the wrk2 container can reach localhost:8080
    where Nginx is exposed.
    """
    print(f"[INFO] Running wrk2: {rate} req/s for {duration}s...")
    print(f"[INFO] Script: {script}")
    docker_exe = find_docker_executable()

    cmd = [
        docker_exe, "run", "--rm",
        "--network", "host",          # Access localhost:8080
        "dsb-wrk2",
        "-t", "4",                    # 4 threads
        "-c", "50",                   # 50 connections
        "-d", f"{duration}s",         # Duration
        "-R", str(rate),              # Target request rate (open-loop)
        "-L",                         # Enable latency tracking
        "-s", script,                 # Lua workload script
        nginx_url,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=duration + 60,   # Extra minute for warmup/cooldown
        )

        print("\n=== wrk2 Output ===")
        print(result.stdout)
        if result.stderr:
            print("=== wrk2 Errors ===")
            print(result.stderr)

        if result.returncode != 0:
            print(f"[WARNING] wrk2 exited with code {result.returncode}")
            return False

        print("[INFO] wrk2 load generation complete.")
        return True

    except subprocess.TimeoutExpired:
        print("[ERROR] wrk2 timed out.")
        return False
    except Exception as e:
        print(f"[ERROR] wrk2 failed: {e}")
        return False


# ============================================================================
# Mode 2: Locust (fallback)
# ============================================================================

def run_locust_load(duration: int, rate: int, nginx_url: str) -> bool:
    """
    Run a quick Locust-based load test as a fallback if wrk2 isn't available.

    We generate the Locust file inline and run it in headless mode.
    """
    import random
    import string
    import tempfile

    locustfile_content = f'''
"""Auto-generated Locust load test for DeathStarBench Social Network."""
import random
import string
from locust import HttpUser, task, between


class SocialNetworkUser(HttpUser):
    """Simulates a user performing social network operations."""
    # Wait between 0.5 and 1.5 seconds between tasks
    wait_time = between(0.5, 1.5)

    def _random_string(self, length=8):
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    @task(3)
    def compose_post(self):
        """Compose a new post (most common operation)."""
        self.client.post(
            "/wrk2-api/post/compose",
            data={{
                "username": f"user_{{random.randint(1, 962)}}",
                "user_id": str(random.randint(1, 962)),
                "text": f"Load test post {{self._random_string(16)}}",
                "media_ids": "[]",
                "media_types": "[]",
                "post_type": "0",
            }},
        )

    @task(5)
    def read_home_timeline(self):
        """Read home timeline (most frequent read operation)."""
        self.client.get(
            "/wrk2-api/home-timeline/read",
            params={{
                "user_id": str(random.randint(1, 962)),
                "start": "0",
                "stop": "10",
            }},
        )

    @task(2)
    def read_user_timeline(self):
        """Read a specific user\\'s timeline."""
        self.client.get(
            "/wrk2-api/user-timeline/read",
            params={{
                "user_id": str(random.randint(1, 962)),
                "start": "0",
                "stop": "10",
            }},
        )
'''

    # Write the locustfile to a temp file
    locustfile_path = get_project_root() / "infra" / "_locustfile_baseline.py"
    locustfile_path.write_text(locustfile_content)

    print(f"[INFO] Running Locust: ~{rate} users for {duration}s...")
    print(f"[INFO] Locustfile: {locustfile_path}")

    cmd = [
        sys.executable, "-m", "locust",
        "-f", str(locustfile_path),
        "--host", nginx_url,
        "--headless",                         # No web UI
        "--users", str(rate),                 # Number of concurrent users
        "--spawn-rate", str(min(rate, 10)),    # Spawn 10 users/second
        "--run-time", f"{duration}s",
        "--only-summary",                     # Less verbose output
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=duration + 60,
        )

        print("\n=== Locust Output ===")
        print(result.stdout[-2000:])  # Last 2000 chars (summary)
        if result.stderr:
            # Locust prints stats to stderr
            print(result.stderr[-1000:])

        print("[INFO] Locust load generation complete.")
        return True

    except subprocess.TimeoutExpired:
        print("[ERROR] Locust timed out.")
        return False
    except Exception as e:
        print(f"[ERROR] Locust failed: {e}")
        return False


# ============================================================================
# Trace verification
# ============================================================================

def verify_traces(jaeger_url: str, min_traces: int = 5) -> bool:
    """
    Query Jaeger to confirm that traces were captured during the load test.
    Returns True if at least min_traces traces are found.
    """
    print(f"\n[INFO] Verifying traces in Jaeger (expecting >={min_traces})...")

    try:
        # First, get the list of services
        resp = requests.get(f"{jaeger_url}/api/services", timeout=10)
        services_data = resp.json()
        services = services_data.get("data") or []
        print(f"[INFO] Services registered in Jaeger: {services}")

        if not services:
            print("[WARNING] No services found in Jaeger. Traces may not be flowing.")
            return False

        # Pick the first non-jaeger service and query its traces
        target_service = None
        for svc in services:
            if "jaeger" not in svc.lower():
                target_service = svc
                break

        if not target_service:
            print("[WARNING] Only jaeger-related services found.")
            return False

        # Query traces for the target service from the last 2 hours
        resp = requests.get(
            f"{jaeger_url}/api/traces",
            params={
                "service": target_service,
                "lookback": "2h",
                "limit": 100,
            },
            timeout=30,
        )
        traces_data = resp.json()
        traces = traces_data.get("data") or []

        print(f"[INFO] Found {len(traces)} traces for service '{target_service}'")

        if len(traces) >= min_traces:
            print("[INFO] Trace verification PASSED")
            # Print sample trace info
            if traces:
                sample = traces[0]
                span_count = len(sample.get("spans", []))
                print(f"[INFO] Sample trace: {sample['traceID']}, {span_count} spans")
            return True
        else:
            print(f"[WARNING] Only {len(traces)} traces found (need >= {min_traces}).")
            print("[WARNING] Load may not have been sufficient, or tracing is misconfigured.")
            return False

    except requests.RequestException as e:
        print(f"[ERROR] Failed to query Jaeger: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate baseline load and verify Jaeger traces"
    )
    parser.add_argument(
        "--mode", choices=["wrk2", "locust", "auto"], default="auto",
        help="Load generator: wrk2 (Docker), locust (Python), or auto (try wrk2, fall back to locust)",
    )
    parser.add_argument(
        "--duration", type=int, default=DEFAULT_DURATION,
        help=f"Load duration in seconds (default: {DEFAULT_DURATION})",
    )
    parser.add_argument(
        "--rate", type=int, default=DEFAULT_RATE,
        help=f"Request rate — req/s for wrk2, concurrent users for Locust (default: {DEFAULT_RATE})",
    )
    parser.add_argument(
        "--nginx-url", default=DEFAULT_NGINX_URL,
        help=f"Nginx URL (default: {DEFAULT_NGINX_URL})",
    )
    parser.add_argument(
        "--jaeger-url", default=DEFAULT_JAEGER_URL,
        help=f"Jaeger URL (default: {DEFAULT_JAEGER_URL})",
    )
    parser.add_argument(
        "--dsb-dir", type=str, default=None,
        help="Path to DeathStarBench repo (needed for wrk2 mode)",
    )
    parser.add_argument(
        "--skip-verify", action="store_true",
        help="Skip Jaeger trace verification after load",
    )
    args = parser.parse_args()

    project_root = get_project_root()
    dsb_dir = Path(args.dsb_dir).resolve() if args.dsb_dir else (
        project_root / DEFAULT_DSB_RELATIVE_PATH
    ).resolve()

    success = False

    # ── Mode selection ─────────────────────────────────────────────────
    if args.mode in ("wrk2", "auto"):
        print("=" * 60)
        print("  Baseline Load Generation - wrk2 mode")
        print("=" * 60)

        # Try building and running wrk2
        if build_wrk2_image(dsb_dir):
            success = run_wrk2_load(
                args.duration, args.rate, args.nginx_url
            )

        if not success and args.mode == "auto":
            print("\n[INFO] wrk2 failed, falling back to Locust...")
            args.mode = "locust"

    if args.mode == "locust":
        print("=" * 60)
        print("  Baseline Load Generation - Locust mode")
        print("=" * 60)
        success = run_locust_load(
            args.duration, args.rate, args.nginx_url
        )

    if not success:
        print("\n[ERROR] Load generation failed.")
        sys.exit(1)

    # ── Verify traces ──────────────────────────────────────────────────
    if not args.skip_verify:
        # Wait a few seconds for traces to be ingested by Jaeger
        print("\n[INFO] Waiting 5s for Jaeger to ingest traces...")
        time.sleep(5)

        if not verify_traces(args.jaeger_url):
            print("[WARNING] Trace verification did not pass.")
            print("[WARNING] Check Jaeger UI at http://localhost:16686")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("  Baseline load generation complete!")
    print(f"  Duration: {args.duration}s, Rate: {args.rate}")
    print(f"  Jaeger UI: {args.jaeger_url}")
    print("=" * 60)


if __name__ == "__main__":
    main()
