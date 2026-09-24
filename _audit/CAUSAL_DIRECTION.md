# Which centrality predicts blast radius? A re-derivation

**Date:** 2026-09-25. **Asked because** the proposed direction looked wrong, and it was.

## The question

The instruction proposed: *"a high-out-degree node's failure should propagate to its many
callers"* — with the caveat to re-derive it and implement whichever direction the causal
chain actually supports.

The proposal contains a contradiction. **Out-degree counts callees, not callers.** A node
with high out-degree has many *downstream* dependencies; that says nothing about how many
services call *it*.

## The causal chain

Let `X -> Y` mean "X calls Y". Kill Y.

**Callers (ancestors) degrade.** X issues an RPC to Y. Y is gone, so X gets
connection-refused or blocks until timeout. X therefore returns an error or takes much
longer. X's own callers then see X slow, and the effect climbs transitively through the
whole ancestor set.

**Callees (descendants) go idle.** Z was called *by* Y. With Y dead, nothing calls Z. Z
receives less traffic. An idle service exhibits no latency inflation and no errors — it
looks perfectly healthy, because it is.

**Failure propagates up the call graph, toward callers.**

It follows that the number of services that degrade is governed by **|ancestors(Y)|**, a
transitive **in-degree** property. Out-degree predicts how many services go *idle*, which
is not an impact.

## The evidence

All 8 kill-fault pilot runs, reclassified by `tools/recompute_pilot.py`:

| app | service | out-deg | \|anc\| | \|desc\| | ancestors degraded | descendants degraded |
|---|---|---:|---:|---:|---:|---:|
| HR | geo | 0 | 2 | 0 | **2** | 0 |
| HR | geo | 0 | 2 | 0 | **2** | 0 |
| HR | search | 2 | 1 | 2 | **1** | 0 |
| HR | search | 2 | 1 | 2 | **1** | 0 |
| SN | compose-post-service | **7** | 1 | **10** | **1** | **0** |
| SN | compose-post-service | **7** | 1 | **10** | **1** | **0** |
| SN | media-service | 0 | 2 | 0 | **2** | 0 |
| SN | media-service | 0 | 2 | 0 | **2** | 0 |

- `ancestor_affected_count == |ancestors|` in **8 of 8** runs. Exactly, every time.
- **Zero descendants degraded in any run** — including `compose-post-service`'s 10.
- Out-degree is *anti*-predictive in this sample: out-degree 7 → 1 service degraded;
  out-degree 0 → 2 degraded.

## What was implemented

`measurement/blast_radius.classify_affected` splits the degraded set three ways and stores
`ancestor_affected_count` as the **primary** blast-radius outcome, with the reasoning above
in the module docstring. The predictor named in `PREREGISTRATION.md` H1 is **|ancestors|**,
not out-degree.

## Consequence for the paper

This **contradicts the premise of the fan-out-corrected hybrid metric**, which amplifies
out-degree on the theory that fan-out drives blast radius.

It also inverts the paper's central example. In the Social Network analysis set,
`compose-post-service` has **|ancestors| = 1 — the lowest of all 11 services** — while
having the highest out-degree (7). The corrected predictor ranks it as the *least*
impactful service, and the measurement agrees: it degraded exactly one service, the fewest
of any service tested.

The "centrality-induced false negative" may therefore not be a false negative. Classical
in-degree-facing metrics may have been ranking `compose-post-service` correctly all along,
and the hybrid metric's promotion of it to rank 1 may be the error.

n = 4 services is far too small to settle this. The campaign tests it properly. But the
direction of the causal chain is not a small-sample question — it follows from what an RPC
does when its callee is absent, and the 8/8 agreement is what that derivation predicts.

## A second, separate mechanism

`unrelated_affected_count` was non-zero only for `media-service` (5 services, identical in
both reps): its caller's *other* callees, and their callees. The likely mechanism is
synchronous fan-out contention — the caller blocks on the dead dependency and its sibling
calls queue behind it.

This is kept as a separate column, never folded into the primary outcome, because it is a
different mechanism. **Caveat:** the `media-service` runs had the thinnest fault windows in
the pilot (52 and 59 traces), and `compute_blast_radius` does not record per-service trace
counts, so a thin-window artefact cannot be ruled out retrospectively. The campaign should
record per-service trace counts so this is decidable.
