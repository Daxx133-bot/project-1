"""
analyze_pilot.py — report the pilot's telemetry health and recovery-time distribution.

Specifically looks for clustering of recovery_time_s near the poll interval, which would
mean the number is a measurement artefact (the probe's resolution floor) rather than real
recovery dynamics. That is the same class of defect as the old 61.07 s ceiling, at the
other end of the scale.

Usage:
    python tools/analyze_pilot.py
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    files = sorted(glob.glob(str(ROOT / "data" / "pilot" / "pilot_*.json")))
    if not files:
        print("no pilot runs found in data/pilot/")
        return 1
    runs = [json.loads(Path(f).read_text(encoding="utf-8")) for f in files]

    print("=" * 96)
    print(f"PILOT: {len(runs)} runs")
    print("=" * 96)
    hdr = (f"{'app':<17}{'service':<22}{'rep':<5}{'tele_ok':<9}{'base_tr':<9}"
           f"{'fault_tr':<10}{'recovery_s':<12}{'restart_s':<11}{'wall_s':<8}")
    print(hdr)
    print("-" * 96)
    for r in runs:
        rt = "CENSORED" if r["recovery_censored"] else f"{r['recovery_time_s']}"
        print(f"{r['app']:<17}{r['service']:<22}{r['repetition']:<5}"
              f"{str(r['telemetry_ok']):<9}{r['baseline_trace_count']:<9}"
              f"{r['fault_trace_count']:<10}{rt:<12}"
              f"{r['container_restart_time_s']:<11}{r['wall_clock_s']:<8}")

    # ── Telemetry health ─────────────────────────────────────────────────────
    ok = [r for r in runs if r["telemetry_ok"]]
    print(f"\n-- TELEMETRY HEALTH --")
    print(f"  telemetry_ok (baseline AND fault traces > 0): {len(ok)}/{len(runs)}")
    zb = [r for r in runs if r["baseline_trace_count"] == 0]
    zf = [r for r in runs if r["fault_trace_count"] == 0]
    print(f"  zero baseline traces: {len(zb)}    zero fault-window traces: {len(zf)}")
    if zf:
        print("    (for a kill fault on the gateway, zero fault traces is expected,"
              " not a bug)")
        for r in zf:
            print(f"      {r['app']}/{r['service']} rep{r['repetition']}")

    # ── Recovery distribution ────────────────────────────────────────────────
    rec = [r for r in runs if not r["recovery_censored"] and r["recovery_time_s"] is not None]
    cen = [r for r in runs if r["recovery_censored"]]
    print(f"\n-- RECOVERY TIME --")
    print(f"  recovered: {len(rec)}/{len(runs)}    censored: {len(cen)}/{len(runs)}")
    if cen:
        for r in cen:
            print(f"    CENSORED: {r['app']}/{r['service']} rep{r['repetition']} "
                  f"observed_until={r['recovery_observed_until_s']}s "
                  f"blocked_on={r['recovery_blocking_indicator']}")
    if rec:
        vals = sorted(r["recovery_time_s"] for r in rec)
        print(f"  values: {vals}")
        print(f"  min={min(vals)}  max={max(vals)}  "
              f"median={vals[len(vals)//2]}  spread={round(max(vals)-min(vals), 2)}")

        # ── Artefact check ───────────────────────────────────────────────────
        polls = {r["recovery_poll_interval_s"] for r in rec}
        poll = min(polls)
        print(f"\n-- ARTEFACT CHECK (poll interval = {poll}s) --")
        floor = [v for v in vals if v <= poll * 1.5]
        print(f"  at/near the resolution floor (<= {poll*1.5}s): {len(floor)}/{len(vals)}")
        distinct = len(set(vals))
        print(f"  distinct values: {distinct}/{len(vals)}")
        if len(floor) == len(vals):
            print("  VERDICT: ALL recovery times sit at the probe's resolution floor.")
            print("           T_rec carries no rank information for this fault type at")
            print("           this poll interval. This is a measurement artefact.")
        elif len(floor) > len(vals) / 2:
            print("  VERDICT: MAJORITY at the floor. T_rec is weakly informative at best.")
        elif distinct <= 2 and len(vals) > 3:
            print("  VERDICT: values collapse onto very few levels -- near-degenerate.")
        else:
            print("  VERDICT: values are spread above the floor -- T_rec looks like it is")
            print("           measuring real dynamics, not the poll grid.")

        # Are the values multiples of the poll interval?
        mult = [v for v in vals if abs((v / poll) - round(v / poll)) < 0.02]
        print(f"  values landing on exact poll multiples: {len(mult)}/{len(vals)} "
              f"(expected: the probe can only resolve to the poll grid)")

    # ── Timing for campaign planning ─────────────────────────────────────────
    walls = [r["wall_clock_s"] for r in runs]
    print(f"\n-- WALL CLOCK --")
    print(f"  per run: min={min(walls)}s  max={max(walls)}s  "
          f"mean={round(sum(walls)/len(walls), 1)}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
