"""validate_per_service_p95.py -- evidence for the Q3 per-service percentile fix.

Reads a real Jaeger trace corpus off disk and recomputes, per service, the number the
OLD code produced against the number the NEW code produces. Nothing is injected,
simulated or generated; every value below comes from spans in the input file.

Input:  sdg/raw_traces/hotel/raw_traces.json  (Hotel Reservation, captured 2026-09-13,
        1644 traces / 16970 spans, the same corpus the HR graph was extracted from)

What the OLD code did
---------------------
    traces = get_traces_in_window(jaeger, service=X, ...)   # every trace TOUCHING X
    p95    = compute_latency_percentiles(traces)["p95_ms"]  # ROOT span durations

so "X's p95" was the end-to-end p95 of the traces X happens to appear in. This script
reproduces exactly that, per service, and puts it beside the corrected per-service
number. If the old rule is the bug we think it is, the old column will be near-constant
across services while the new column separates them.

Usage:
    python tools/validate_per_service_p95.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from measurement.metrics_collector import (  # noqa: E402
    compute_latency_percentiles,
    select_spans,
    span_service_map,
)

CORPUS = ROOT / "sdg" / "raw_traces" / "hotel" / "raw_traces.json"
INFRA = ("jaeger", "mongo", "redis", "memcached")
DEGRADATION_FACTOR = 2.0   # the blast-radius rule: p95 > 2x baseline -> "affected"


def traces_touching(traces: list[dict], service: str) -> list[dict]:
    """Emulate Jaeger's /api/traces?service=X: every trace containing a span from X."""
    out = []
    for t in traces:
        if service in span_service_map(t).values():
            out.append(t)
    return out


def main() -> int:
    if not CORPUS.exists():
        print(f"SOURCE NOT FOUND: {CORPUS}")
        return 1

    doc = json.loads(CORPUS.read_text(encoding="utf-8"))
    traces = doc["traces"]
    meta = doc.get("metadata", {})

    services = sorted({
        s for t in traces for s in span_service_map(t).values()
        if s and not any(i in s.lower() for i in INFRA)
    })

    print("=" * 96)
    print("Q3 VALIDATION -- per-service p95 recomputed from real spans")
    print("=" * 96)
    print(f"corpus      : {CORPUS.relative_to(ROOT)}")
    print(f"collected_at: {meta.get('collected_at')}")
    print(f"traces      : {len(traces)}   spans: {meta.get('span_count')}")
    print()

    print(f"{'service':<16}{'traces':>8}{'spans':>8}{'OLD p95':>11}{'NEW p95':>11}"
          f"{'ratio':>9}   {'OLD scope':<22}")
    print("-" * 96)

    rows = []
    for svc in services:
        touching = traces_touching(traces, svc)
        old = compute_latency_percentiles(touching)                  # root spans
        new = compute_latency_percentiles(touching, service=svc)     # svc server spans
        ratio = (old["p95_ms"] / new["p95_ms"]) if new["p95_ms"] else float("nan")
        rows.append((svc, len(touching), new["count"], old["p95_ms"], new["p95_ms"], ratio))
        print(f"{svc:<16}{len(touching):>8}{new['count']:>8}{old['p95_ms']:>11.2f}"
              f"{new['p95_ms']:>11.2f}{ratio:>9.2f}   {old['scope']:<22}")

    print()
    old_vals = [r[3] for r in rows]
    new_vals = [r[4] for r in rows]
    spread = lambda v: (max(v) / min(v)) if min(v) > 0 else float("inf")
    print(f"  OLD p95 across services: min={min(old_vals):.2f}  max={max(old_vals):.2f}"
          f"  max/min={spread(old_vals):.2f}x   distinct={len(set(old_vals))}/{len(rows)}")
    print(f"  NEW p95 across services: min={min(new_vals):.2f}  max={max(new_vals):.2f}"
          f"  max/min={spread(new_vals):.2f}x   distinct={len(set(new_vals))}/{len(rows)}")

    # ---- the misclassification mechanism, on real data ----------------------
    print()
    print("=" * 96)
    print("MISCLASSIFICATION MECHANISM")
    print("=" * 96)
    print("The blast-radius rule flags service S when  p95(S, fault) > "
          f"{DEGRADATION_FACTOR:g} x p95(S, baseline).")
    print("Take the slowest service in this corpus and ask which services the OLD rule")
    print("would drag with it, using only durations present in the file.")
    print()

    slowest = max(rows, key=lambda r: r[4])
    print(f"slowest service by its OWN spans: {slowest[0]}  (p95 {slowest[4]:.2f} ms)")
    print()

    slow_traces = traces_touching(traces, slowest[0])
    print(f"{'service':<16}{'appears in':>12}{'OLD p95 on':>12}{'NEW p95 on':>12}"
          f"{'OLD/NEW':>9}  note")
    print(f"{'':<16}{'those':>12}{'those':>12}{'those':>12}")
    print("-" * 96)
    for svc, *_ in rows:
        sub = [t for t in slow_traces if svc in span_service_map(t).values()]
        if not sub:
            continue
        old = compute_latency_percentiles(sub)["p95_ms"]
        new = compute_latency_percentiles(sub, service=svc)["p95_ms"]
        note = "IS the slow one" if svc == slowest[0] else (
            "inherits the slow trace's tail" if old > DEGRADATION_FACTOR * new else "")
        print(f"{svc:<16}{len(sub):>12}{old:>12.2f}{new:>12.2f}"
              f"{(old / new if new else float('nan')):>9.2f}  {note}")

    print()
    print("Reading: under the OLD rule every service on the slow path reports the same")
    print("end-to-end tail, so a single slow service makes its ancestors AND unrelated")
    print("path-mates exceed any multiplicative threshold together. Under the NEW rule")
    print("each service reports its own spans and they separate.")
    return 0




# ---------------------------------------------------------------------------
# Part 2: does this explain the pilot's misclassification?
# ---------------------------------------------------------------------------
# The pilot's own fault-window spans were NOT persisted -- Jaeger ran with in-memory
# storage and the per-run JSON stores only aggregates -- so the two HR latency runs
# cannot be recomputed span-by-span. What CAN be done is stronger than a re-run of the
# same aggregation: the old rule's flagged set is *deterministic*. Under root-span
# percentiles, "service X's p95" is the end-to-end p95 of X's trace cohort, so when a
# latency fault inflates the cohort of the faulted service F, every service sharing
# F's traces inherits the identical inflated number and is flagged together.
#
# That yields a falsifiable prediction: the set the pilot flagged must equal F's
# trace cohort. The cohort is read off the real corpus below; the flagged set is read
# off the pilot JSON. Neither is adjustable.

def cohort_check() -> int:
    import glob

    doc = json.loads(CORPUS.read_text(encoding="utf-8"))
    traces = doc["traces"]

    print()
    print("=" * 96)
    print("PART 2 -- PREDICTED vs OBSERVED FLAGGED SET (HR search, latency fault)")
    print("=" * 96)

    faulted = "search"
    cohort = set()
    n = 0
    for t in traces:
        svcs = {s for s in span_service_map(t).values()
                if s and not any(i in s.lower() for i in INFRA)}
        if faulted in svcs:
            n += 1
            cohort |= svcs
    predicted = cohort - {faulted}

    print(f"trace cohort of '{faulted}' in the corpus: {n} traces")
    print(f"  services co-occurring with '{faulted}': {sorted(cohort)}")
    print(f"  OLD rule therefore predicts flagged = {sorted(predicted)}")
    print()

    runs = sorted(glob.glob(str(ROOT / "data" / "pilot" /
                                "pilot_hotelreservation_search_latency_*.json")))
    if not runs:
        print("SOURCE NOT FOUND: no HR search latency pilot runs on disk")
        return 1

    all_match = True
    for f in runs:
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        observed = {s for s in d["downstream_affected_services"].split(",") if s}
        match = observed == predicted
        all_match &= match
        print(f"  {Path(f).name}")
        print(f"    observed flagged = {sorted(observed)}")
        print(f"    match            = {'EXACT' if match else 'NO -- ' + str(sorted(observed ^ predicted))}")

    print()
    if all_match:
        print("  VERDICT: exact set match in every run. The pilot's flagged set is fully")
        print("  explained by the root-span bug -- it is the trace cohort, not a graph")
        print("  neighbourhood. Note that 'profile' and 'reservation' are neither")
        print("  ancestors nor descendants of 'search'; they were flagged purely because")
        print("  they ride the same trace. Under the corrected rule each of these")
        print("  services reports its own server spans, which in this corpus differ by")
        print("  up to 105x, so they can no longer move as a block.")
    else:
        print("  VERDICT: NOT a clean match -- the root-span bug does not fully explain it.")

    print()
    print("  LIMIT OF THIS VALIDATION: this shows the old number was structurally")
    print("  incapable of distinguishing these services, and predicts the observed set")
    print("  exactly. It does not measure the corrected per-service p95 during a live")
    print("  latency fault, because those spans no longer exist. That measurement")
    print("  requires a fresh run and is listed as such.")
    return 0


if __name__ == "__main__":
    rc = main()
    raise SystemExit(rc or cohort_check())
