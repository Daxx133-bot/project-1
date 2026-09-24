# Open issue: "per-service" latency is actually end-to-end latency

**Found:** 2026-09-25, during the latency/CPU pilot.
**Status:** NOT FIXED. It changes what "affected" means, so it needs your decision.

## What the code does

`measurement/metrics_collector.py::compute_latency_percentiles` builds its distribution
from **root span durations only**:

```python
refs = span.get("references", [])
is_root = not any(r.get("refType") == "CHILD_OF" for r in refs)
if is_root:
    root_durations_us.append(float(span.get("duration", 0)))
```

It is fed by `get_traces_in_window(jaeger_url, service, ...)`, which asks Jaeger for
traces **in which `service` participates**. In both benchmarks the root span of every such
trace is the *gateway's* span (`nginx-web-server` / `frontend`), not the queried service's.

So `baselines["geo"]["p95_ms"]` does not mean "geo's p95". It means:

> the p95 **end-to-end** latency of requests that happened to touch geo.

## Why it matters

`compute_blast_radius` flags a service as affected when that number exceeds 2x its
baseline. Under that definition a service is "affected" whenever **requests passing
through it** slow down — regardless of whether the service itself degraded.

The two fault types then behave completely differently, and the pilot shows both:

| Fault on `search` | What the metric sees | Classification |
|---|---|---|
| **kill** | Traces through `geo`/`rate` vanish (search never calls them), so they are not flagged. Traces through `frontend` carry errors, so it is flagged. | **A=1, D=0** |
| **latency** | Every trace touching `geo`/`rate` also traverses the slowed `search`, so their end-to-end latency doubles and both are flagged. | **A=0, D=2** |

The `D=2` under latency is **not** evidence that failure propagates downstream. It is the
metric attributing the caller's added delay to the callees, because the number being
compared is the whole request's duration.

This does not affect the kill-fault conclusion in `_audit/PILOT_FINDINGS.md` §5 — with a
dead service there are no traces to mis-attribute, and the ancestor result
(`A == |ancestors|` in 8/8, `D == 0` in 8/8) stands. But it means the ancestor/descendant
classification **cannot be compared across fault types** as currently measured.

## The fix, and the trade-off

Compute each service's own latency from **its own spans** rather than the trace root:

```python
spans_of_service = [s for s in trace["spans"]
                    if processes[s["processID"]] == service]
```

- **For:** makes the column mean what its name says; makes the A/D/U classification
  comparable across fault types; is what "this service degraded" should mean.
- **Against:** it is a **definitional change to the primary blast-radius outcome**, and
  the 8 kill-fault runs already collected were measured the old way. Adopting it means
  either re-running those 8 or reporting two differently-defined blast radii.
- It also changes what a "downstream affected" service means in the paper's own terms,
  so the manuscript text has to follow.

## Options

1. **Fix now, re-run the 8 kill runs** (~20 min of machine time). Cleanest; everything
   downstream is then measured one way.
2. **Fix now, apply only to the campaign**, and treat the 8 pilot runs as method
   development rather than data. Also clean, since the pilot was never meant to be data.
3. **Keep root-span semantics**, rename the columns to
   `end_to_end_p95_of_traces_through_service`, and state the limitation explicitly.
   Cheapest, but it leaves the primary outcome measuring something other than what its
   name implies — the exact class of problem the audit was called in for.

**My recommendation: option 2.** The pilot's job was to find this, the campaign has not
started, and re-running 8 throwaway runs buys nothing. Option 3 preserves a known
misnomer in the primary outcome, which I would not defend in review.

Either way the kill-fault ancestor finding survives, because it does not depend on the
distinction.
