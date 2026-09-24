"""
compare_fault_types.py — is each impact indicator valid for each fault type?

Answers two questions the pilot was run to settle:
  1. Does T_rec cluster near the probe's resolution floor for latency/cpu faults, the way
     the OLD container-restart metric did? (Clustering => measurement artefact.)
  2. Does delta-p95 behave invalidly for latency/cpu the way it does for kill faults,
     where a dead service fails fast and SHRINKS the tail?

Reads data/pilot/*.json only. Nothing is re-run.
"""
from __future__ import annotations
import glob, json, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

runs = [json.loads(Path(f).read_text(encoding="utf-8"))
        for f in sorted(glob.glob(str(ROOT / "data" / "pilot" / "pilot_*.json")))]

print("=" * 112)
print("INDICATOR VALIDITY BY FAULT TYPE")
print("=" * 112)
print(f"{'app':<4}{'service':<22}{'fault':<9}{'rep':<4}{'base_p95':>10}{'fault_p95':>11}"
      f"{'d_p95':>11}{'d_err':>8}{'A/D/U':>9}{'T_rec':>9}{'eff_res':>9}")
print("-" * 112)
for r in runs:
    s = r.get("recovery_samples") or []
    gaps = [round(s[i + 1]["t_s"] - s[i]["t_s"], 2) for i in range(len(s) - 1)]
    eff = statistics.median(gaps) if gaps else float("nan")
    d_p95 = (r["fault_p95_ms"] - r["baseline_p95_ms"]) if r.get("fault_p95_ms") is not None else None
    d_err = (r["fault_error_rate"] - r["baseline_error_rate"]) if r.get("fault_error_rate") is not None else None
    t = "CENS" if r["recovery_censored"] else f"{r['recovery_time_s']:.2f}"
    adu = (f"{r.get('ancestor_affected_count','-')}/"
           f"{r.get('descendant_affected_count','-')}/"
           f"{r.get('unrelated_affected_count','-')}")
    print(f"{r['app'][:2]:<4}{r['service']:<22}{r['fault_type']:<9}{r['repetition']:<4}"
          f"{r['baseline_p95_ms']:>10.2f}{r['fault_p95_ms']:>11.2f}{d_p95:>11.2f}"
          f"{d_err:>8.3f}{adu:>9}{t:>9}{eff:>9.2f}")

print("\n" + "=" * 112)
print("PER-FAULT-TYPE SUMMARY")
print("=" * 112)
for ft in sorted({r["fault_type"] for r in runs}):
    sub = [r for r in runs if r["fault_type"] == ft]
    rec = [r["recovery_time_s"] for r in sub if not r["recovery_censored"]]
    dp = [r["fault_p95_ms"] - r["baseline_p95_ms"] for r in sub
          if r.get("fault_p95_ms") is not None]
    de = [r["fault_error_rate"] - r["baseline_error_rate"] for r in sub]
    effs = []
    for r in sub:
        s = r.get("recovery_samples") or []
        g = [s[i + 1]["t_s"] - s[i]["t_s"] for i in range(len(s) - 1)]
        if g:
            effs.append(statistics.median(g))
    floor = statistics.median(effs) if effs else float("nan")

    print(f"\n{ft.upper()}  (n={len(sub)}, recovered={len(rec)}, censored={len(sub)-len(rec)})")
    if rec:
        near = [v for v in rec if v <= floor * 1.5]
        print(f"  T_rec: {[round(v,2) for v in sorted(rec)]}")
        print(f"     min={min(rec):.2f}  max={max(rec):.2f}  distinct={len(set(round(v,2) for v in rec))}/{len(rec)}")
        print(f"     effective resolution={floor:.2f}s;  at/near floor (<={floor*1.5:.2f}s): {len(near)}/{len(rec)}")
        print(f"     CLUSTERING VERDICT: "
              + ("ARTEFACT - all values at the resolution floor" if len(near) == len(rec)
                 else "weak - majority at the floor" if len(near) > len(rec) / 2
                 else "no clustering - values are spread above the floor"))
    if dp:
        neg = sum(1 for v in dp if v < 0)
        print(f"  delta_p95: {[round(v,1) for v in dp]}")
        print(f"     negative in {neg}/{len(dp)} runs  ->  "
              + ("INVALID for this fault type (tail shrinks while impact is real)" if neg == len(dp)
                 else "MIXED - sign is not stable" if neg
                 else "VALID for this fault type (tail inflates as expected)"))
    print(f"  delta_error_rate: {[round(v,3) for v in de]}  ->  "
          + ("carries no signal for this fault type" if max(de) < 0.01
             else "carries signal"))
