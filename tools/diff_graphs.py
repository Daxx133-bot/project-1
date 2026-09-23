"""
diff_graphs.py — compare two service dependency graphs node-for-node and edge-for-edge.

Written to answer one question honestly: does a freshly captured graph reproduce the one
the manuscript's Table 1 was computed from?

Usage:
    python tools/diff_graphs.py --old sdg/output/sdg.json --new data/graphs/sn_2026-09-24.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import networkx as nx


def load(path: Path) -> nx.DiGraph:
    with open(path, "r", encoding="utf-8") as fh:
        return nx.node_link_graph(json.load(fh), edges="edges")


def call_counts(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return {(e["source"], e["target"]): e.get("call_count", 0) for e in data["edges"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True, type=Path)
    ap.add_argument("--new", required=True, type=Path)
    args = ap.parse_args()

    old, new = load(args.old), load(args.new)
    old_counts, new_counts = call_counts(args.old), call_counts(args.new)

    print("=" * 78)
    print(f"OLD: {args.old}   {old.number_of_nodes()} nodes  {old.number_of_edges()} edges")
    print(f"NEW: {args.new}   {new.number_of_nodes()} nodes  {new.number_of_edges()} edges")
    print("=" * 78)

    on, nn = set(old.nodes()), set(new.nodes())
    print("\n-- NODES --")
    print(f"  identical: {on == nn}")
    if on - nn:
        print(f"  only in OLD (lost): {sorted(on - nn)}")
    if nn - on:
        print(f"  only in NEW (gained): {sorted(nn - on)}")
    if on == nn:
        print(f"  all {len(on)} nodes match exactly")

    oe, ne = set(old.edges()), set(new.edges())
    print("\n-- EDGES --")
    print(f"  in both : {len(oe & ne)}")
    print(f"  only OLD: {len(oe - ne)}")
    print(f"  only NEW: {len(ne - oe)}")

    if oe - ne:
        print("\n  LOST (in Table 1's graph, absent now):")
        for a, b in sorted(oe - ne):
            print(f"    {a:<24} -> {b:<24}  old call_count={old_counts.get((a, b))}")
    if ne - oe:
        print("\n  GAINED (absent from Table 1's graph, present now):")
        for a, b in sorted(ne - oe):
            print(f"    {a:<24} -> {b:<24}  new call_count={new_counts.get((a, b))}")

    print("\n-- STRUCTURAL PROPERTIES --")
    for label, G in (("OLD", old), ("NEW", new)):
        cycles = list(nx.simple_cycles(G))
        print(f"  {label}: DAG={nx.is_directed_acyclic_graph(G)}  cycles={len(cycles)}"
              + (f"  e.g. {cycles[0]}" if cycles else ""))

    print("\n-- DEGREE COMPARISON --")
    print(f"  {'service':<24} {'out_OLD':>8} {'out_NEW':>8} {'in_OLD':>7} {'in_NEW':>7}")
    for n in sorted(on | nn):
        oo = old.out_degree(n) if n in old else "-"
        no = new.out_degree(n) if n in new else "-"
        oi = old.in_degree(n) if n in old else "-"
        ni = new.in_degree(n) if n in new else "-"
        flag = "  <-- CHANGED" if (oo, oi) != (no, ni) else ""
        print(f"  {n:<24} {str(oo):>8} {str(no):>8} {str(oi):>7} {str(ni):>7}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
