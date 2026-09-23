#!/usr/bin/env python3
"""
preflight_environment.py — Safe Architecture Switching Preflight
================================================================

This script safely manages the transition between DeathStarBench architectures
by ensuring that the active stack is cleanly shut down (releasing host ports)
before a new architecture is brought up.

Usage:
    python scripts/preflight_environment.py --architecture socialnetwork
    python scripts/preflight_environment.py --architecture hotelreservation
    python scripts/preflight_environment.py --teardown-all
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
import urllib.request
import urllib.error


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_dsb_dir(project_root: Path) -> Path:
    dsb_dir = (project_root / "../DeathStarBench").resolve()
    if not dsb_dir.exists():
        print(f"[ERROR] DeathStarBench not found at {dsb_dir}")
        sys.exit(1)
    return dsb_dir


def check_docker():
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[ERROR] Docker daemon is not running or 'docker' is not in PATH.")
        sys.exit(1)


def get_container_ports():
    """Returns a list of dicts: {'name': '...', 'ports': ['16686', '8080']}"""
    try:
        res = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}||{{.Ports}}"],
            capture_output=True, text=True, check=True
        )
        containers = []
        for line in res.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("||")
            if len(parts) == 2:
                name, ports_raw = parts
                # ports_raw looks like "0.0.0.0:16686->16686/tcp, :::16686->16686/tcp"
                ports = []
                for p in ports_raw.split(","):
                    if "->" in p and ":" in p.split("->")[0]:
                        host_port = p.split("->")[0].split(":")[-1]
                        ports.append(host_port)
                containers.append({"name": name, "ports": ports})
        return containers
    except subprocess.CalledProcessError:
        return []


def check_port_conflicts(target_ports: list, allow_prefix: str) -> bool:
    """Checks if any target ports are bound by containers not matching allow_prefix."""
    containers = get_container_ports()
    conflict = False
    for c in containers:
        for p in c["ports"]:
            if p in target_ports:
                if not c["name"].startswith(allow_prefix):
                    print(f"[ERROR] Port {p} is occupied by conflicting container: {c['name']}")
                    conflict = True
    return not conflict


def teardown_architecture(dsb_dir: Path, arch_name: str):
    """
    Safely tears down the specified architecture.
    Uses 'docker-compose down' WITHOUT '-v' to preserve database state.
    """
    arch_dir = dsb_dir / arch_name
    if not arch_dir.exists():
        return
    print(f"[INFO] Tearing down {arch_name}...")
    try:
        subprocess.run(
            ["docker-compose", "down"],
            cwd=str(arch_dir),
            capture_output=True, check=True
        )
        print(f"[INFO] Successfully shut down {arch_name}.")
    except subprocess.CalledProcessError as e:
        print(f"[WARNING] Failed to shut down {arch_name} cleanly: {e.stderr.decode('utf-8', 'ignore')}")


def startup_architecture(dsb_dir: Path, arch_name: str):
    """Starts the architecture using docker-compose up -d."""
    arch_dir = dsb_dir / arch_name
    print(f"[INFO] Starting up {arch_name}...")
    try:
        subprocess.run(
            ["docker-compose", "up", "-d"],
            cwd=str(arch_dir),
            capture_output=True, check=True
        )
        print(f"[INFO] Successfully started {arch_name}.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to start {arch_name}: {e.stderr.decode('utf-8', 'ignore')}")
        sys.exit(1)


def check_jaeger_health():
    """Verifies Jaeger API is reachable on port 16686."""
    print("[INFO] Checking Jaeger health...")
    for _ in range(30):
        try:
            req = urllib.request.Request("http://localhost:16686/api/services")
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    print("[INFO] Jaeger is healthy and reachable.")
                    return True
        except Exception:
            pass
        time.sleep(2)
    print("[ERROR] Jaeger health check failed.")
    return False


def check_app_health(arch_name: str):
    """Verifies the primary application entrypoint is reachable."""
    print(f"[INFO] Checking {arch_name} application health...")
    url = "http://localhost:8080" if arch_name == "socialNetwork" else "http://localhost:5000"
    for _ in range(30):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                if response.status < 500:
                    print(f"[INFO] {arch_name} is healthy.")
                    return True
        except Exception:
            pass
        time.sleep(2)
    print(f"[ERROR] {arch_name} health check failed.")
    return False


def main():
    parser = argparse.ArgumentParser(description="Preflight environment manager")
    parser.add_argument("--architecture", choices=["socialnetwork", "hotelreservation"], help="Architecture to start")
    parser.add_argument("--teardown-all", action="store_true", help="Tear down all managed architectures")
    args = parser.parse_args()

    project_root = get_project_root()
    dsb_dir = get_dsb_dir(project_root)

    check_docker()

    arch_map = {
        "socialnetwork": {"dir": "socialNetwork", "prefix": "socialnetwork", "ports": ["16686", "8080"]},
        "hotelreservation": {"dir": "hotelReservation", "prefix": "hotelreservation", "ports": ["16686", "5000"]}
    }

    if args.teardown_all:
        teardown_architecture(dsb_dir, "socialNetwork")
        teardown_architecture(dsb_dir, "hotelReservation")
        sys.exit(0)

    if not args.architecture:
        print("[ERROR] Must specify --architecture or --teardown-all")
        sys.exit(1)

    target_config = arch_map[args.architecture]
    other_arch = "hotelReservation" if args.architecture == "socialnetwork" else "socialNetwork"

    # Step 1: Tear down the other architecture
    teardown_architecture(dsb_dir, other_arch)

    # Step 2: Check for conflicting ports
    if not check_port_conflicts(target_config["ports"], target_config["prefix"]):
        print("[ERROR] Aborting due to port conflict. Please manually stop conflicting containers.")
        sys.exit(1)

    # Step 3: Start target architecture
    startup_architecture(dsb_dir, target_config["dir"])

    # Step 4: Verify health
    time.sleep(5)  # Give containers a moment to bind ports
    if not check_jaeger_health():
        sys.exit(1)
    
    if not check_app_health(target_config["dir"]):
        sys.exit(1)

    print("\n[SUCCESS] Preflight complete. Environment is ready for fault injection.")


if __name__ == "__main__":
    main()
