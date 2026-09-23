"""
extract_graph.py — rebuild a service dependency graph from live Jaeger spans.

Queries every service Jaeger knows about, walks parent/child span references, and emits
the cross-service call edges as a NetworkX node-link JSON, plus a provenance block
recording when it was captured and against which DeathStarBench commit.

Provenance is not optional here: the previous Social Network graph
(sdg/output/sdg.json) had its source traces overwritten, so Table 1 became
unreproducible. Every graph this script writes carries enough metadata to rebuild it.

Usage:
    python tools/extract_graph.py --jaeger http://localhost:16686 \\
        --out data/graphs/sn_2026-09-24.json --app socialnetwork --lookback 1h
"""

from __future__ import annotations

import argparse
import collections
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent

# Infrastructure that carries spans but is not an application microservice.
INFRA_MARKERS = ("jaeger", "mongodb", "memcached", "redis", "consul")


def is_app_service(name: str) -> bool:
    low = name.lower()
    return not any(m in low for m in INFRA_MARKERS)


def dsb_commit(dsb_dir: Path) -> dict:
    """Record the DeathStarBench commit and whether the tree is dirty."""
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=dsb_dir,
                              capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=dsb_dir,
                               capture_output=True, text=True, check=True).stdout.strip()
        return {
            "commit": head,
            "short": head[:7],
            "dirty": bool(dirty),
            "modified_files": [ln for ln in dirty.splitlines() if ln.startswith(" M")],
        }
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        return {"commit": "UNKNOWN", "error": str(exc)}


def fetch(jaeger: str, service: str, lookback: str, limit: int) -> list[dict]:
    r = requests.get(f"{jaeger}/api/traces",
                     params={"service": service, "lookback": lookback, "limit": limit},
                     timeout=60)
    r.raise_for_status()
    return r.json().get("data") or []


def build(jaeger: str, lookback: str, limit: int) -> tuple[dict, dict]:
    services = requests.get(f"{jaeger}/api/services", timeout=30).json().get("data") or []
    app_services = sorted(s for s in services if is_app_service(s))

    edges: collections.Counter = collections.Counter()
    latency: dict[tuple[str, str], list[int]] = collections.defaultdict(list)
    seen_traces: set[str] = set()
    spans_examined = 0

    for svc in app_services:
        for trace in fetch(jaeger, svc, lookback, limit):
            tid = trace.get("traceID")
            if tid in seen_traces:
                continue
            seen_traces.add(tid)

            procs = {k: v["serviceName"] for k, v in (trace.get("processes") or {}).items()}
            spans = {s["spanID"]: s for s in trace.get("spans", [])}
            for span in trace.get("spans", []):
                spans_examined += 1
                for ref in span.get("references") or []:
                    parent = spans.get(ref.get("spanID"))
                    if parent is None:
                        continue
                    a = procs.get(parent.get("processID"))
                    b = procs.get(span.get("processID"))
                    if a and b and a != b and is_app_service(a) and is_app_service(b):
                        edges[(a, b)] += 1
                        latency[(a, b)].append(span.get("duration", 0))

    nodes = sorted({n for e in edges for n in e} | set(app_services))
    graph = {
        "directed": True,
        "multigraph": False,
        "graph": {},
        "nodes": [{"id": n} for n in nodes],
        "edges": [
            {
                "source": a, "target": b,
                "weight": c, "call_count": c,
                "avg_latency_us": round(sum(latency[(a, b)]) / len(latency[(a, b)]), 2),
                "avg_latency_ms": round(sum(latency[(a, b)]) / len(latency[(a, b)]) / 1000, 2),
            }
            for (a, b), c in sorted(edges.items())
        ],
    }
    stats = {
        "traces_examined": len(seen_traces),
        "spans_examined": spans_examined,
        "services_in_jaeger": sorted(services),
        "app_services": app_services,
    }
    return graph, stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jaeger", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--app", required=True)
    ap.add_argument("--lookback", default="1h")
    ap.add_argument("--limit", type=int, default=1500)
    ap.add_argument("--dsb-dir", type=Path, default=ROOT.parent / "DeathStarBench")
    args = ap.parse_args()

    graph, stats = build(args.jaeger, args.lookback, args.limit)
    graph["graph"] = {
        "application": args.app,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "jaeger_url": args.jaeger,
        "lookback": args.lookback,
        "deathstarbench": dsb_commit(args.dsb_dir),
        **stats,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(graph, indent=2), encoding="utf-8")

    print(f"[WROTE] {args.out}")
    print(f"  traces={stats['traces_examined']}  spans={stats['spans_examined']}")
    print(f"  nodes={len(graph['nodes'])}  edges={len(graph['edges'])}")
    print(f"  DSB commit={graph['graph']['deathstarbench'].get('short')} "
          f"dirty={graph['graph']['deathstarbench'].get('dirty')}")
    print()
    for e in graph["edges"]:
        print(f"    {e['source']:<24} -> {e['target']:<24} {e['call_count']:>6} calls  "
              f"{e['avg_latency_ms']:>8.2f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
