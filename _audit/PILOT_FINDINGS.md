# Pilot Findings (Step 5)

**Date:** 2026-09-24 · **Scope:** 8 runs (2 services × kill × 2 reps × 2 apps).
One stack at a time. No weights tuned. No manuscript touched.

Raw records: `data/pilot/pilot_*.json` (each carries the full per-poll recovery trace).
Analysis: `python tools/analyze_pilot.py`.

> **3 additional SN runs were discarded**, not included here. A detached first pilot
> launch survived undetected and ran concurrently with a second, so two processes injected
> faults into the same stack. See `_quarantine/QUARANTINE_LOG.md` item 9. A PID lockfile
> now prevents this (`tools/run_pilot.py::RunLock`).

---

## 1. Service selection, and one protocol conflict it exposed

| App | Orchestrator | Leaf |
|---|---|---|
| Social Network | `compose-post-service` (out-deg 7, the paper's central service) | `media-service` (out-deg 0) |
| Hotel Reservation | `search` (out-deg 2) | `geo` (out-deg 0) |

**`frontend` was deliberately not used for HR**, despite being the paper's HR headline
service. In Hotel Reservation the highest-fan-out service **is the gateway**, and the
gateway is also the service whose p95/p99/error-rate define the outcome. Killing it means
the outcome variable is undefined by construction — zero traces, guaranteed censoring.

This is a **structural conflict in the preregistered design**, not a pilot artefact, and
it needs resolving before the campaign. See §7, item (a).

---

## 2. Telemetry health — **fixed**

**`telemetry_ok = True` in 8/8 runs.** Every run recorded non-zero trace counts in both
the baseline and fault windows. For comparison, the two older batches
(`hr_sep13`, `sn_legacy`) had this failure in **101/101** runs.

The instrumentation added in step 4 is what makes this checkable at all: `trace_count`
and `telemetry_ok` are now written per run, so an outage can no longer masquerade as a
measurement of zero.

**But two new sampling defects were found, and both matter.**

### 2a. `limit=500` truncation is binding

8 of 12 HR windows returned **exactly 500** traces — the API cap. At ~24 req/s over a
30 s window (~720 requests), Jaeger returns only the newest 500, so percentiles are
computed on a biased tail of each window. **Must be raised or paginated before the campaign.**

### 2b. Thin probe windows can produce a false recovery signal

In `compose-post-service` rep1, the probe read `all_ok = True` at t=35.15 s and
t=36.53 s from windows containing **2 and 1 traces**. A p95 from one trace is not a
measurement. The sequence of per-sample trace counts was:

```
8, 2, 1, 38, 31, 23, 17, 13, 8, 2, 46
```

That oscillation is the signature of **Jaeger's batch flushing**: a 10 s window ending at
"now" sometimes catches a flush and sometimes misses it. Killing `compose-post-service`
also collapses load-generator throughput, which thins the windows further.

The 5 s confirmation window absorbed it this time — the `False` at t=37.93 s reset the
counter. But with ~1.4 s effective sampling, only ~4 consecutive samples are needed, so a
false recovery is reachable. **In that run the declared recovery at t=42.26 s itself
rested on windows of 17, 13, 8 and 2 traces**, so its value should be treated as
provisional.

Two fixes required, both in `measurement/recovery_probe.py`:

- a **minimum trace count** per sample (below it, the sample is "no signal", not "ok");
- a **lagged probe window** — query `[now-15s, now-5s]` rather than `[now-10s, now]`,
  so spans have settled before they are read.

This also retrospectively supports the audit's ingestion-lag hypothesis for `sn_legacy`'s
empty fault windows.

---

## 3. Recovery time — real dynamics, but with a protocol floor

| App | Service | Rep | `T_rec` (s) | `container_restart` (s) | Ratio |
|---|---|---|---|---|---|
| HR | `geo` | 1 | 56.47 | 0.65 | 87× |
| HR | `geo` | 2 | **CENSORED** (181.3 s, blocked on p95) | 1.22 | — |
| HR | `search` | 1 | 46.52 | 0.79 | 59× |
| HR | `search` | 2 | 46.41 | 0.65 | 71× |
| SN | `compose-post-service` | 1 | 42.26 | 0.69 | 61× |
| SN | `compose-post-service` | 2 | 44.01 | 0.81 | 54× |
| SN | `media-service` | 1 | 48.35 | 0.70 | 69× |
| SN | `media-service` | 2 | 45.85 | 0.69 | 66× |

### The two metrics are decisively different — separating them was correct

Container restart is **0.65–1.22 s**; application recovery is **42–56 s or censored**.
A **54–87× gap**. The old pipeline reported the former under the name of the latter.

### No clustering at the poll interval

Values are 42.26, 44.01, 45.85, 46.41, 46.52, 48.35, 56.47 — **7 distinct values from 7
recovered runs, spanning 14.2 s**, none within 1.5× of the poll interval. `T_rec` is measuring real dynamics, not the
sampling grid.

The recovery curves confirm this. For HR `search` rep1, error rate decayed smoothly from
54% to 0% over ~12 s as the container returned:

```
 t_s  traces    p95     err  down    ok
34.5     244   5.41  0.5388     1  False
38.5     243  36.90  0.4115     1  False
41.5     240  44.16  0.2625     1  False
44.8     232  49.64  0.0776     1  False
46.5     237  52.49  0.0000     0   True   <- recovered
```

That is a genuine recovery trajectory, and nothing in the old pipeline could have produced it.

### But `T_rec` has a hard floor at ~34 s

The first probe sample cannot occur before:

```
30.0 s  deliberate fault hold (--fault-duration)
 3.7 s  fault-window metric collection (1 gateway + N downstream Jaeger queries)
 0.8 s  container restart command
------
~34.5 s  earliest observable T_rec
```

One discarded run was already recovered at its **first** sample. So `T_rec` as currently
defined is **`fault_duration` + restart + convergence**, not convergence alone. Because
`fault_duration` is constant, *rank* correlations are unaffected — but the absolute values
are inflated by ~35 s and are not comparable to any external literature. See §7, item (b).

### The censored run is a real phenomenon, not a bug

`geo` rep2 never returned to within 10% of baseline in 180 s. Error rate went to 0 and
downstream count to 0 within ~70 s, but p95 settled at **~95 ms against a 49.9 ms
baseline** and stayed there:

```
t=105 s  p95=80.5  err=0.0  down=1
t=176 s  p95=95.0  err=0.0  down=0
```

This is a **cold-cache steady-state shift** — after restart the system stabilises at a
new, slower equilibrium. It is exactly what `container_restart_time_s = 1.22 s` would
have missed entirely, and it raises a real definitional question (§7, item c).

### Effective poll resolution is not the nominal one

| App | Services | Nominal poll | **Measured median gap** |
|---|---:|---:|---:|
| HR | 8 | 1.0 s | **1.6–2.4 s** |
| SN | 12 | 1.0 s | **1.41 s** |

Each iteration issues `1 + N_services` Jaeger queries. The `--poll` value is a **lower
bound** on the sampling period. The preregistration must state the measured resolution,
not the requested one.

---

## 4. Δp95 is invalid as a severity measure for kill faults

This is the clearest methodological result of the pilot.

| App | Service | Δp95 (ms) | fault error rate |
|---|---|---:|---:|
| HR | `geo` rep1 | **−44.11** | 0.546 |
| HR | `geo` rep2 | **−44.04** | 0.514 |
| HR | `search` rep1 | **−45.46** | 0.560 |
| HR | `search` rep2 | **−53.37** | 0.522 |
| SN | `compose-post-service` rep1 | **+2527** | 0.253 |
| SN | `compose-post-service` rep2 | **+2480** | 0.282 |
| SN | `media-service` rep1 | **+8867** | 0.154 |
| SN | `media-service` rep2 | **+7939** | 0.254 |

**Every Hotel Reservation kill produced a large *negative* Δp95 while the system was
50–56% failing.** The mechanism is simple: when a service dies, requests that would have
taken the slow path now fail fast (HTTP 500 in ~5 ms), so the surviving latency
distribution is dominated by fast failures and p95 *drops*.

Note also that in SN the **largest** Δp95 (+8867 ms) coincides with the **lowest** error
rate (0.154), while its own replicate (+7939 ms) had a 65% higher error rate. Δp95 and error rate are not merely differently scaled — they can be
**anti-correlated**.

The manuscript's Tables 3 and 4 use Δp95 and Δp99 as primary impact indicators. **That
choice is not defensible for kill faults.** Error rate is the consistent signal.

---

## 5. Measured blast radius does not track fan-out — and inverts it

| App | Service | out-deg | descendants | ancestors | **measured blast radius** |
|---|---|---:|---:|---:|---:|
| HR | `search` | 2 | 2 | 1 | **1** |
| HR | `geo` | 0 | 0 | 2 | **2** |
| SN | `compose-post-service` | **7** | **10** | 1 | **1** |
| SN | `media-service` | **0** | **0** | 2 | **7** (both reps, identical set) |

**The high-fan-out orchestrator the entire paper is built around produced the *smallest*
measured blast radius (1). The leaf produced the largest (7).** Both replicated across
repetitions.

An intermediate hypothesis — that the metric measures the *ancestor* set, since
degradation propagates toward callers — fitted 3 of 4 services and was then **falsified**
by `media-service`, whose affected set was:

```
compose-post-service, nginx-web-server, text-service, unique-id-service,
url-shorten-service, user-mention-service, user-service
```

That is neither its ancestors (2), nor its descendants (0), nor ancestors ∪ siblings — it
includes `text-service`'s callees and excludes three of `compose-post`'s own. **No simple
structural rule fits.** The measured blast radius is genuinely empirical, reflecting
runtime latency coupling through synchronous fan-out, and it does not reduce to graph
position.

Two consequences:

1. The field name `downstream_affected_count` is **wrong**. It counts services that
   *degrade*, which are mostly upstream of or lateral to the faulted service, never its
   descendants. It should be renamed (`services_degraded_count`) and the manuscript's
   interpretation corrected.
2. This is **direct evidence against H1's proposed mechanism**. The hybrid metric
   amplifies out-degree on the theory that fan-out determines blast radius. In this pilot
   the relationship ran the other way. n = 4 services is far too small to conclude
   anything, but it is a genuine warning that the campaign may return a null — and per
   `CLAUDE.md` rule 4 and `PREREGISTRATION.md` §8.1, a null will be reported as null.

---

## 6. Campaign timing estimate

Measured wall clock per run: **109.7, 112.0, 113.7, 115.0, 115.0, 116.2, 125.1, 243.5 s**
— median **115 s**, mean **131 s**. The 244 s run is the censored one (it pays the full 180 s `max_wait`).

For the preregistered 300 runs (SN 180 + HR 120):

| Censoring rate | Per run | Pure run time |
|---:|---:|---:|
| 0% | 118 s | **9.9 h** |
| 25% | 150 s | **12.5 h** |
| 50% | 181 s | **15.1 h** |

The pilot censored 1 of 8 (12.5%), which projects to **~11 hours**. Add stack swaps
(~3 min each), per-app data seeding (~2 min), and re-runs for any
`telemetry_ok = False` run.

**Realistic estimate: 12–16 hours of machine time**, best split across sessions by
application to minimise stack swaps. This is unattended time, but it cannot be
parallelised — one stack at a time is a hard constraint (§ `_audit/MEMORY_CEILING.md`).

---

## 7. Proposed amendments to the preregistration — **for your decision**

The document is not yet locked. Five items, all arising from measured pilot behaviour
rather than from preference.

**(a) The HR gateway/orchestrator conflict.** In Hotel Reservation the highest-fan-out
service (`frontend`, out-deg 5) *is* the gateway that defines the outcome. Killing it
guarantees zero traces and automatic censoring.
*Options:* (i) exclude gateways from the faulted set and state it as a scope limitation;
(ii) measure the outcome at a non-gateway observation point; (iii) for gateway faults,
switch the outcome to external probe success rate.
*My recommendation:* **(i)**, with the limitation stated plainly. It loses the HR headline
service, which is a real cost — flagging it rather than deciding for you.

**(b) `T_rec` origin.** Currently measured from fault *injection*, so it includes the
30 s deliberate hold and floors at ~34 s.
*Options:* (i) keep it, disclose the offset, rely on the constant to preserve ranks;
(ii) measure from fault *removal* (restart command).
*My recommendation:* **(ii)** — it makes the number mean what its name says. It does not
change rank correlations, since the offset is constant.

**(c) Recovery tolerance vs. steady-state shift.** The censored `geo` run reached a stable
new equilibrium at ~1.9× baseline p95 with zero errors. Is that "not recovered"?
*Options:* (i) keep the strict 10% rule and let cold-cache cases censor — clean, but
censoring rates may be high and driven by cache behaviour rather than failure severity;
(ii) add a secondary "stabilised but shifted" outcome state.
*My recommendation:* **(i)** for the confirmatory analysis — changing the definition after
seeing pilot data is exactly the flexibility preregistration exists to prevent — with the
shift recorded as a descriptive secondary.

**(d) Demote Δp95/Δp99 from the outcome set.** Given §4, Δp95 is not a valid severity
measure for kill faults. *Recommendation:* retain it as **descriptive only**, promote
error rate, and state the sign-flip finding explicitly in the paper. This is a
methodological correction, not a result-driven swap — the direction was not chosen to
favour any hypothesis.

**(e) Two mandatory probe fixes before the campaign** (§2a, §2b): a minimum-trace-count
floor per sample, and a lagged probe window. *Recommendation:* apply both, then re-run
**2 confirmation runs** to verify the floor does not change the recovery values already
observed. These are correctness fixes; I regard them as required rather than optional.

---

## 8. Status

- Steps 1–5 complete. **Stopped before the campaign, as instructed.**
- Nothing tuned, no weights fitted, no manuscript edited.
- `data/pilot/` holds 8 clean runs; 3 contaminated runs are quarantined.
- Preregistration remains **unlocked**, pending decisions on (a)–(e).

---

# Addendum — 2026-09-25 recomputation under the amended definitions

Produced by `tools/recompute_pilot.py` (reprocessing only, no fault re-injected) and two
confirmation runs. Raw output: `data/pilot/recomputed_pilot_outcomes.csv`.

## A1. Blast radius reclassified

| app | service | out-deg | \|anc\| | \|desc\| | **A** | **D** | **U** | old total |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| HR | geo | 0 | 2 | 0 | **2** | 0 | 0 | 2 |
| HR | geo | 0 | 2 | 0 | **2** | 0 | 0 | 2 |
| HR | search | 2 | 1 | 2 | **1** | 0 | 0 | 1 |
| HR | search | 2 | 1 | 2 | **1** | 0 | 0 | 1 |
| SN | compose-post-service | 7 | 1 | 10 | **1** | 0 | 0 | 1 |
| SN | compose-post-service | 7 | 1 | 10 | **1** | 0 | 0 | 1 |
| SN | media-service | 0 | 2 | 0 | **2** | 0 | **5** | 7 |
| SN | media-service | 0 | 2 | 0 | **2** | 0 | **5** | 7 |

- `ancestor_affected_count == |ancestors|` in **8/8** runs.
- **0 descendants degraded in any run**, including `compose-post-service`'s 10.
- `unrelated` is non-zero only for `media-service` (5 services, identical both reps).

## A2. Recovery re-based on fault removal, and replayed under the min-trace floor

| app | service | rep | from injection | removal offset | **from removal** | under min-trace floor |
|---|---|---|---:|---:|---:|---|
| HR | geo | 1 | 56.47 | 34.41 | **22.06** | 22.06 |
| HR | geo | 2 | CENSORED | 35.22 | CENSORED | CENSORED |
| HR | search | 1 | 46.52 | 34.50 | **12.02** | 12.02 |
| HR | search | 2 | 46.41 | 34.32 | **12.09** | 12.09 |
| SN | compose-post-service | 1 | 42.26 | 33.78 | 8.48 | **CENSORED** |
| SN | compose-post-service | 2 | 44.01 | 34.17 | 9.84 | **CENSORED** |
| SN | media-service | 1 | 48.35 | 34.02 | 14.33 | **CENSORED** |
| SN | media-service | 2 | 45.85 | 34.31 | 11.54 | **CENSORED** |

The removal offset is a near-constant **33.8–35.2 s**, confirming it was a fixed protocol
offset rather than signal. Re-basing removes it: `T_rec` becomes **8.5–22.1 s**.

**The floor censors all four SN runs and none of the HR runs.** HR had 0 thin samples;
SN had 7–11 thin samples per run, 4–6 of which had voted for recovery. The original SN
recovery values were resting on 1–17 trace windows. This is a real defect the floor
correctly exposes — but the floor alone makes SN unmeasurable, which is why the lagged
window matters.

## A3. Confirmation runs for amendment (e)

Same condition (`compose-post-service` / kill) that exhibited the defect:

| run | median traces | thin/total | thin voted ok | T_rec (from removal) |
|---|---:|---:|---:|---:|
| BEFORE rep1 | 13 | 7/11 | **6** | 8.48 |
| BEFORE rep2 | 18 | 7/12 | **4** | 9.84 |
| **AFTER rep1** | **38** | 2/15 | **0** | **13.84** |
| **AFTER rep2** | **34** | 1/17 | **0** | **16.47** |

The lagged window roughly tripled the median trace count and no thin sample voted in
either run. The floor is visible in rep1: at t=12.40 s all four indicators were in
tolerance but `trace_count=19` blocked the vote; recovery was declared 1.44 s later on a
46-trace window. `T_rec` is *larger* after the fix because the earlier values recovered
"early" on thin evidence.

## A4. Footnote on the censored `geo` rep2 run (amendment c)

Per the decision, the strict 10% threshold stands and no rule exception is made. For the
record, the hypothesis for that single censored observation is a **cold-cache
steady-state shift**: error rate reached 0 and downstream count 0 within ~70 s, but
gateway p95 stabilised at ~95 ms against a 49.9 ms baseline and held there to 180 s. This
is recorded as a hypothesis about one run, not as grounds to relax the threshold.
