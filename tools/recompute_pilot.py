"""
recompute_pilot.py — reprocess the existing pilot runs under the amended definitions.

Reprocesses only. No fault is injected, no container is touched. Every number comes from
the per-run JSON already on disk (including its full per-poll `recovery_samples` trace).

Applies, per the 2026-09-25 decisions:
  * blast-radius reclassification into ancestor / descendant / unrelated
  * amendment (a) gateway exclusion flag
  * amendment (b) T_rec measured from fault REMOVAL rather than injection
  * amendment (e) min-trace floor, replayed against the recorded samples

Recovering the fault-removal instant from an existing run
--------------------------------------------------------
`probe_recovery` captures `now` at the TOP of each loop iteration, before it issues any
query, and `run_pilot.one_run` calls it immediately after the restart subprocess returns.
So the first recorded sample's `t_s` is the probe's start instant, which is the moment
the fault was lifted. `t_removal = samples[0]["t_s"]` is therefore read from logged data,
not estimated. Runs written after this change record `fault_removal_offset_s` directly.

Usage:
    python tools/recompute_pilot.py
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from measurement.blast_radius import classify_affected, is_gateway  # noqa: E402

GRAPHS = {
    "socialnetwork": ROOT / "data" / "graphs" / "sn_CANONICAL.json",
    "hotelreservation": ROOT / "data" / "graphs" / "hr_CANONICAL.json",
}

MIN_TRACES = 20          # amendment (e), matches recovery_probe.DEFAULT_MIN_TRACES
CONFIRM_S = 5.0          # as used by the pilot runs being reprocessed


def load_graph(app: str) -> nx.DiGraph:
    return nx.node_link_graph(json.loads(GRAPHS[app].read_text(encoding="utf-8")),
                              edges="edges")


def replay_recovery(samples: list[dict], t_removal: float, min_traces: int,
                    confirm_s: float) -> dict:
    """Re-derive recovery from the recorded samples under the min-trace floor.

    Mirrors probe_recovery's state machine exactly: a sample may only vote for recovery
    if it has at least `min_traces` traces AND all indicators are in tolerance; recovery
    is declared once that has held continuously for `confirm_s`.
    """
    ok_since = None
    first_ok = None
    for s in samples:
        thick = s["trace_count"] >= min_traces
        ok = bool(s["all_ok"]) and thick
        t = s["t_s"]
        if ok:
            if ok_since is None:
                ok_since = t
                if first_ok is None:
                    first_ok = t
            if t - ok_since >= confirm_s:
                return {"recovered": True,
                        "recovery_from_removal_s": round(ok_since - t_removal, 2),
                        "first_ok_from_removal_s": round(first_ok - t_removal, 2)}
        else:
            ok_since = None
    return {"recovered": False, "recovery_from_removal_s": None,
            "first_ok_from_removal_s": (round(first_ok - t_removal, 2)
                                        if first_ok is not None else None)}


def main() -> int:
    rows = []
    for f in sorted(glob.glob(str(ROOT / "data" / "pilot" / "pilot_*.json"))):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        G = load_graph(d["app"])
        svc = d["service"]

        cls = classify_affected(
            G, svc, d.get("downstream_affected_services", "").split(","))

        samples = d.get("recovery_samples") or []
        # Fault-removal offset: recorded directly if present, else the first sample's t_s.
        t_removal = d.get("fault_removal_offset_s")
        derived = t_removal is None
        if derived:
            t_removal = samples[0]["t_s"] if samples else None

        old_rec = d.get("recovery_time_s")
        row = {
            "app": d["app"], "service": svc, "fault_type": d["fault_type"],
            "repetition": d["repetition"],
            "is_gateway": is_gateway(G, svc),
            "excluded_from_correlation": is_gateway(G, svc),
            **cls,
            "old_blast_total": d.get("downstream_affected_count"),
            "old_recovery_from_injection_s": old_rec,
            "old_censored": d.get("recovery_censored"),
            "fault_removal_offset_s": round(t_removal, 2) if t_removal is not None else None,
            "fault_removal_offset_derived": derived,
            "baseline_p95_ms": d.get("baseline_p95_ms"),
            "fault_p95_ms": d.get("fault_p95_ms"),
            "delta_p95_ms": (round(d["fault_p95_ms"] - d["baseline_p95_ms"], 2)
                             if d.get("fault_p95_ms") is not None else None),
            "fault_error_rate": d.get("fault_error_rate"),
            "baseline_trace_count": d.get("baseline_trace_count"),
            "fault_trace_count": d.get("fault_trace_count"),
        }

        # (b) simple re-basing of the ORIGINAL recovery decision onto fault removal
        row["recovery_from_removal_s"] = (
            round(old_rec - t_removal, 2)
            if (old_rec is not None and t_removal is not None) else None)

        # (e) replay under the min-trace floor
        if samples and t_removal is not None:
            replay = replay_recovery(samples, t_removal, MIN_TRACES, CONFIRM_S)
            row["minfloor_recovered"] = replay["recovered"]
            row["minfloor_recovery_from_removal_s"] = replay["recovery_from_removal_s"]
            thin = [s for s in samples if s["trace_count"] < MIN_TRACES]
            row["thin_samples"] = len(thin)
            row["thin_samples_that_voted_ok"] = len([s for s in thin if s["all_ok"]])
            row["total_samples"] = len(samples)
        rows.append(row)

    out = ROOT / "data" / "pilot" / "recomputed_pilot_outcomes.csv"
    import csv
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ── Report ────────────────────────────────────────────────────────────────
    print("=" * 108)
    print("BLAST RADIUS RECLASSIFIED  (A=ancestor  D=descendant  U=unrelated)")
    print("=" * 108)
    print(f"{'app':<4}{'service':<22}{'rep':<4}{'out':>4}{'|anc|':>6}{'|desc|':>7}"
          f"{'A':>4}{'D':>4}{'U':>4}{'old_total':>11}  {'A==|anc|':>9}")
    print("-" * 108)
    for r in rows:
        match = "yes" if r["ancestor_affected_count"] == r["n_ancestors"] else "NO"
        print(f"{r['app'][:2]:<4}{r['service']:<22}{r['repetition']:<4}"
              f"{r['out_degree_raw']:>4}{r['n_ancestors']:>6}{r['n_descendants']:>7}"
              f"{r['ancestor_affected_count']:>4}{r['descendant_affected_count']:>4}"
              f"{r['unrelated_affected_count']:>4}{r['old_blast_total']:>11}  {match:>9}")

    nA = sum(r["ancestor_affected_count"] == r["n_ancestors"] for r in rows)
    nD = sum(r["descendant_affected_count"] for r in rows)
    print(f"\n  ancestor_affected == |ancestors| in {nA}/{len(rows)} runs")
    print(f"  total descendants that degraded across all runs: {nD}")

    print("\n" + "=" * 108)
    print("RECOVERY TIME RE-BASED ON FAULT REMOVAL, AND REPLAYED UNDER THE MIN-TRACE FLOOR")
    print("=" * 108)
    print(f"{'app':<4}{'service':<22}{'rep':<4}{'from_inject':>12}{'removal_off':>12}"
          f"{'from_removal':>13}{'minfloor':>10}{'thin/total':>12}{'thin_voted_ok':>14}")
    print("-" * 108)
    for r in rows:
        oi = "CENS" if r["old_censored"] else f"{r['old_recovery_from_injection_s']:.2f}"
        fr = "CENS" if r["old_censored"] else f"{r['recovery_from_removal_s']:.2f}"
        mf = ("CENS" if not r.get("minfloor_recovered")
              else f"{r['minfloor_recovery_from_removal_s']:.2f}")
        print(f"{r['app'][:2]:<4}{r['service']:<22}{r['repetition']:<4}{oi:>12}"
              f"{r['fault_removal_offset_s']:>12.2f}{fr:>13}{mf:>10}"
              f"{str(r.get('thin_samples', '-')) + '/' + str(r.get('total_samples', '-')):>12}"
              f"{str(r.get('thin_samples_that_voted_ok', '-')):>14}")

    print(f"\n[WROTE] {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
