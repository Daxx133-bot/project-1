"""
run_pilot.py — small, instrumented pilot. NOT the full campaign.

Runs (service x kill x repetition) for a handful of services against ONE already-running
stack, using the corrected recovery probe. Writes one JSON per run plus a summary CSV
into data/pilot/.

Everything measured here comes from Jaeger and the Docker API. Nothing is estimated.
If telemetry is empty the run is recorded as telemetry_ok=False and the metrics are left
as nulls -- never as zeros, which is the conflation that hid the earlier outage.

Usage:
    python tools/run_pilot.py --app hotelreservation --services frontend,geo --reps 2
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from faultinjection.fault_config import FaultType, DEFAULT_SPECS  # noqa: E402
from infra.docker_utils import find_docker_executable  # noqa: E402
from measurement.metrics_collector import (  # noqa: E402
    collect_baseline_metrics, collect_fault_window_metrics, compute_blast_radius,
)
from measurement.recovery_probe import probe_recovery  # noqa: E402

APPS = {
    "socialnetwork": {
        "jaeger": "http://localhost:16686",
        "gateway": "nginx-web-server",
        "url": "http://localhost:8080",
        "locustfile": ROOT / "infra" / "_locustfile_baseline.py",
        "graph": ROOT / "data" / "graphs" / "sn_CANONICAL.json",
        "compose_dir": ROOT.parent / "DeathStarBench" / "socialNetwork",
    },
    "hotelreservation": {
        "jaeger": "http://localhost:16687",
        "gateway": "frontend",
        "url": "http://localhost:5000",
        "locustfile": ROOT / "infra" / "_locustfile_hotel.py",
        "graph": ROOT / "data" / "graphs" / "hr_CANONICAL.json",
        "compose_dir": ROOT.parent / "DeathStarBench" / "hotelReservation",
    },
}


class RunLock:
    """Refuse to start if another runner instance is live.

    A double-launch silently corrupts runs: two processes inject faults into the same
    stack while each other's load generator and recovery probe are active. That happened
    during the 2026-09-24 pilot and cost 3 runs
    (see _quarantine/QUARANTINE_LOG.md item 9).
    """

    def __init__(self, path: Path):
        self.path = path

    def __enter__(self):
        if self.path.exists():
            holder = self.path.read_text(encoding="utf-8").strip()
            raise SystemExit(
                f"[REFUSED] another runner appears to be active (lock held by {holder}). "
                f"If you are certain it is dead, delete {self.path} and retry."
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(f"pid={os.getpid()} started={datetime.now(timezone.utc).isoformat()}",
                             encoding="utf-8")
        return self

    def __exit__(self, *exc):
        self.path.unlink(missing_ok=True)
        return False


def graph_services(path: Path) -> list[str]:
    return [n["id"] for n in json.loads(path.read_text(encoding="utf-8"))["nodes"]]


def container_for(service: str, docker_exe: str) -> str:
    out = subprocess.run([docker_exe, "ps", "--format", "{{.Names}}"],
                         capture_output=True, text=True, check=True).stdout.split()
    exact = [n for n in out if service in n and "mongodb" not in n and "memcached" not in n]
    if not exact:
        raise SystemExit(f"[FAIL] no running container matches '{service}'")
    # prefer the shortest name, which avoids matching e.g. user-timeline for user
    return min(exact, key=len)


def start_load(cfg: dict, duration: int, users: int) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "locust", "-f", str(cfg["locustfile"]),
         "--host", cfg["url"], "--headless", "--users", str(users),
         "--spawn-rate", "10", "--run-time", f"{duration}s", "--only-summary",
         "--loglevel", "ERROR"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(ROOT),
    )


def one_run(app: str, service: str, rep: int, cfg: dict, args) -> dict:
    docker_exe = find_docker_executable()
    container = container_for(service, docker_exe)
    services = graph_services(cfg["graph"])
    t0 = time.time()

    print(f"\n{'='*70}\n  {app} / {service} / kill / rep {rep}   (container: {container})\n{'='*70}")

    load = start_load(cfg, args.warmup + args.fault_duration + int(args.max_wait) + 60,
                      args.users)
    try:
        print(f"  [WARMUP] {args.warmup}s")
        time.sleep(args.warmup)

        print("  [BASELINE] collecting")
        baseline = collect_baseline_metrics(cfg["jaeger"], services,
                                            window_seconds=args.warmup)
        gw_base = baseline.get(cfg["gateway"], {})
        base_traces = int(gw_base.get("trace_count", 0))
        print(f"  [BASELINE] gateway p95={gw_base.get('p95_ms')}ms "
              f"traces={base_traces}")

        spec = DEFAULT_SPECS[FaultType.KILL]
        fault_start_us = int(time.time() * 1_000_000)
        print(f"  [FAULT] {' '.join(spec.pumba_command(container))}")
        subprocess.run(spec.pumba_command(container), check=True, timeout=60,
                       capture_output=True)

        print(f"  [FAULT] holding {args.fault_duration}s")
        time.sleep(args.fault_duration)
        fault_end_us = int(time.time() * 1_000_000)

        fault_m = collect_fault_window_metrics(cfg["jaeger"], cfg["gateway"],
                                               fault_start_us, fault_end_us)
        fault_traces = int(fault_m.get("trace_count", 0))
        down_n, down_list = compute_blast_radius(cfg["jaeger"], services, service,
                                                 baseline, fault_start_us, fault_end_us)
        print(f"  [FAULT] gateway p95={fault_m.get('p95_ms')}ms traces={fault_traces} "
              f"downstream={down_n}")

        print("  [RESTORE] docker compose up -d")
        restart_t0 = time.time()
        subprocess.run([docker_exe, "compose", "up", "-d", service],
                       cwd=str(cfg["compose_dir"]), capture_output=True, timeout=180)
        restart_s = round(time.time() - restart_t0, 2)

        print(f"  [RECOVERY] probing (poll={args.poll}s, max_wait={args.max_wait}s)")
        rec = probe_recovery(
            cfg["jaeger"], cfg["gateway"], services, baseline, fault_start_us,
            poll_interval_s=args.poll, max_wait_s=args.max_wait,
            tolerance=0.10, confirm_seconds=args.confirm,
        )
        if rec.recovered:
            print(f"  [RECOVERY] recovered at {rec.recovery_time_s}s")
        else:
            print(f"  [RECOVERY] CENSORED at {rec.observed_until_s}s "
                  f"(blocked on {rec.blocking_indicator})")

        return {
            "app": app, "service": service, "fault_type": "kill", "repetition": rep,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "container": container,
            "baseline_p95_ms": gw_base.get("p95_ms"),
            "baseline_p99_ms": gw_base.get("p99_ms"),
            "baseline_error_rate": gw_base.get("error_rate"),
            "baseline_trace_count": base_traces,
            "fault_p95_ms": fault_m.get("p95_ms"),
            "fault_p99_ms": fault_m.get("p99_ms"),
            "fault_error_rate": fault_m.get("error_rate"),
            "fault_trace_count": fault_traces,
            "telemetry_ok": base_traces > 0 and fault_traces > 0,
            "downstream_affected_count": down_n,
            "downstream_affected_services": ",".join(down_list),
            "recovery_time_s": rec.recovery_time_s,
            "recovery_censored": rec.censored,
            "recovery_observed_until_s": rec.observed_until_s,
            "recovery_first_ok_at_s": rec.first_ok_at_s,
            "recovery_blocking_indicator": rec.blocking_indicator,
            "recovery_poll_interval_s": args.poll,
            "container_restart_time_s": restart_s,
            "wall_clock_s": round(time.time() - t0, 2),
            "recovery_samples": rec.samples,
        }
    finally:
        load.terminate()
        try:
            load.wait(timeout=15)
        except subprocess.TimeoutExpired:
            load.kill()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", required=True, choices=list(APPS))
    ap.add_argument("--services", required=True, help="comma-separated")
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--warmup", type=int, default=60)
    ap.add_argument("--fault-duration", type=int, default=30)
    ap.add_argument("--poll", type=float, default=1.0)
    ap.add_argument("--max-wait", type=float, default=180.0)
    ap.add_argument("--confirm", type=float, default=5.0)
    ap.add_argument("--users", type=int, default=25)
    ap.add_argument("--cooldown", type=int, default=20)
    args = ap.parse_args()

    cfg = APPS[args.app]
    out_dir = ROOT / "data" / "pilot"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    with RunLock(out_dir / ".runner.lock"):
        for service in [s.strip() for s in args.services.split(",")]:
            for rep in range(1, args.reps + 1):
                res = one_run(args.app, service, rep, cfg, args)
                results.append(res)
                stamp = res["timestamp"].replace(":", "-").replace("+00:00", "Z")
                (out_dir / f"pilot_{args.app}_{service}_kill_rep{rep}_{stamp}.json").write_text(
                    json.dumps(res, indent=2), encoding="utf-8")
                print(f"  [COOLDOWN] {args.cooldown}s")
                time.sleep(args.cooldown)

    print(f"\n{'='*70}\n  PILOT SUMMARY: {args.app}\n{'='*70}")
    for r in results:
        rt = "CENSORED" if r["recovery_censored"] else f"{r['recovery_time_s']}s"
        print(f"  {r['service']:<22} rep{r['repetition']}  "
              f"telemetry_ok={str(r['telemetry_ok']):<5}  "
              f"base_traces={r['baseline_trace_count']:<5} fault_traces={r['fault_trace_count']:<5} "
              f"recovery={rt:<10} restart={r['container_restart_time_s']}s  "
              f"wall={r['wall_clock_s']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
