# Preregistration v2

**Study:** Identifying Failure-Prone Microservices Using Graph Centrality Metrics
**Version:** 2 (2026-09-25). Supersedes v1 (2026-09-23).
**Status:** READY TO LOCK, pending two open decisions in §10.
**Supersedes:** every analysis in `_quarantine/` and every number in the current manuscript drafts.

Changes from v1 are marked **[v2]** and all stem from measured pilot behaviour
(`_audit/PILOT_FINDINGS.md`), not from preference.

---

## 0. Why this exists

An audit (`_audit/AUDIT_REPORT.md`) found the prior results were produced by a dataset in
which 48 of 107 rows came from `random.uniform()` keyed to each service's own centrality,
by weights grid-searched against the outcome they were then validated on, and by an
outcome variable that measured container restart rather than application recovery. The
headline ρ = 0.897 was a maximum over a search on 49%-synthetic data; on the cleanest real
dataset the same quantity is ρ = 0.0605, p = 0.85.

---

## 1. Hypotheses **[v2 — H1 reversed]**

The pilot re-derived the causal chain and **falsified the direction H1 was built on**.

Let `X -> Y` mean "X calls Y", and kill Y:

* **X (a caller, i.e. an ANCESTOR of Y)** issues an RPC to Y, receives connection-refused
  or a timeout, and therefore errors or slows. **X degrades.** Its own callers then see X
  slow, so the effect climbs transitively through the ancestor set.
* **Z (a callee, i.e. a DESCENDANT of Y)** is never called, because Y — the thing that
  called Z — is dead. Z receives *less* traffic and goes **idle**. An idle service shows
  no latency or error anomaly.

Failure propagates **up** the call graph, toward callers. Therefore the size of the
degraded set is governed by **|ancestors(Y)|**, a transitive *in-degree* property.
Out-degree predicts how many services go idle, which is not an impact at all.

Measured across all 8 kill-fault pilot runs: `ancestor_affected_count == |ancestors|` in
**8/8**, and **0 descendants degraded in any run** — including `compose-post-service`,
which has 10.

**H1 [v2].** `ancestor_affected_count` is predicted by |ancestors| (and by in-degree),
**not** by out-degree or by the fan-out-corrected hybrid metric.

**H2 (unchanged).** Classical composite centrality ranking demotes high-fan-out
orchestrator services relative to their measured impact.

> **Note on H2's status.** Under the corrected direction, `compose-post-service` has
> **|ancestors| = 1, the lowest in the Social Network analysis set**, while having the
> highest out-degree (7). The corrected predictor therefore ranks it as *least* impactful,
> and the pilot agrees (blast radius 1). H2's "false negative" may not be a false negative
> at all — classical in-degree-facing metrics may have been ranking it correctly. The
> campaign tests this; the paper must be prepared to report it.

**H0 for both:** no monotone association beyond chance. **H0 is a publishable outcome.**

---

## 2. The hybrid metric — exact formula (unchanged)

$$
\mathrm{Criticality}(v) = w_{in}C_{in}(v) + w_{out}C_{out}(v)\phi(v) + w_{btw}C_{btw}(v),
\qquad \phi(v) = \frac{d^{+}(v)}{\max_u d^{+}(u)}
$$

| Term | Definition | NetworkX |
|---|---|---|
| $C_{in}$ | in-degree centrality, $d^-/(n-1)$ | `in_degree_centrality` |
| $C_{out}$ | out-degree centrality, $d^+/(n-1)$ | `out_degree_centrality` |
| $C_{btw}$ | betweenness, **directed** normalisation | `betweenness_centrality(normalized=True)` |
| $\phi$ | fan-out weight, **linear** | — |

Three corrections carried into the manuscript: $\phi$ is **linear** (the manuscript also
states a quadratic form the code never implemented; they coincide only for the
maximum-out-degree node); degree centrality divides by $(n-1)$, not $2(n-1)$; eigenvector
centrality is **L2**-normalised and is **degenerate — 0.0 for all 12 SN services**, since
the reconstructed graph is a DAG. It is reported as a baseline with that stated.

---

## 3. Weight protocol (unchanged: cross-arch)

Tune $(w_{in}, w_{out}, w_{btw})$ on **Social Network only**, grid step 0.05 (231
triplets); freeze to `centrality/output/tuned_weights.lock.json`; evaluate **once** on
**Hotel Reservation**. The tuning-set ρ is not a result and is reported only as "maximum
over 231 triplets". Enforced in code: `--protocol` is required, re-tuning over an existing
lockfile is refused, and a second evaluation is refused.

> **[v2] Power warning on the held-out set.** After gateway exclusion (§4), Hotel
> Reservation retains 7 services whose |ancestors| takes only **2 distinct values**
> (five 1s, two 2s). Computed from `data/analysis/predictor_table.csv`:
>
> | | n | predictor levels | best attainable ρ | permutation FPR at α=0.05 |
> |---|---:|---:|---:|---:|
> | Social Network | 11 | 4 | 0.941 (p<0.0001) | 0.054 |
> | **Hotel Reservation** | **7** | **2** | **0.791 (p=0.034)** | **0.097** |
>
> Even a *perfect* HR result is barely significant, and the asymptotic Spearman p-value is
> **anti-conservative** under this tie structure. **Therefore: all HR inference uses exact
> permutation tests, never the asymptotic p-value**, and the held-out evaluation is
> reported as *directional evidence, not confirmation*. See §10 open question 1.

---

## 4. Analysis set — gateway exclusion **[v2, amendment (a)]**

Services with **in-degree 0 in the SDG** are excluded from all quantitative correlation
analysis. Such a service receives traffic only from the external load generator, which is
not a graph node, so it has no ancestors by construction and cannot have a meaningful
ancestor-affected count.

| Architecture | Excluded | Analysis n |
|---|---|---:|
| Social Network | `nginx-web-server` | **11** |
| Hotel Reservation | `frontend` | **7** |

Both remain in the qualitative tables, labelled:
**"excluded from correlation analysis — sole entry point confounds any downstream-facing
outcome measure."**

Implemented as `measurement/blast_radius.is_gateway` / `analysis_services`.

> This costs Hotel Reservation its highest-fan-out service. `frontend` (out-degree 5) *is*
> the gateway whose p95/p99/error-rate define the outcome, so killing it leaves the outcome
> undefined. That is a scope limitation to state, not a result.

---

## 5. Primary outcomes **[v2 — restructured]**

### 5.1 Blast radius — three columns, not one

For every service flagged as degraded during the fault window, classify its graph
relation to the faulted node and store all three counts separately
(`measurement/blast_radius.classify_affected`):

| Column | Meaning |
|---|---|
| **`ancestor_affected_count`** | **PRIMARY.** Degraded services that are transitive callers of the faulted node. |
| `descendant_affected_count` | Degraded transitive callees. Expected ≈ 0 for kill faults. |
| `unrelated_affected_count` | Neither — shared-resource or synchronous-fan-out contention. |

They are never summed into a single total. In the pilot `unrelated` was non-zero only for
`media-service` (5 services, identical in both reps), where the degraded set included its
caller's *other* callees — a contention mechanism, not dependency propagation.

### 5.2 Recovery time $T_{rec}$ **[v2, amendment (b)]**

> Elapsed seconds **from fault REMOVAL** — the restart command returning, or the
> netem/stress rule expiring — until Δp95, Δp99, Δerror-rate and downstream-affected-count
> are **simultaneously** within **10%** of their pre-fault baseline and **hold** for a
> **5 s** confirmation period.

- Measured from removal, not injection: v1 measured from injection, which made $T_{rec}$ =
  `fault_duration` + restart + convergence and floored it at ~34 s. Re-basing the 8 pilot
  runs moved them from 42–56 s to **8.5–22.1 s**.
- Tolerance is **one-sided**; an empty or thin window is "no signal", never "recovered";
  a window never reaches back before the fault instant.
- **Tolerance stays at 10% [amendment (c)].** No exception is made for the one censored
  run; the cold-cache hypothesis for it is a footnote in `_audit/PILOT_FINDINGS.md` §A4.

**Censoring.** Not recovered within **180 s** ⇒ `recovery_time_s = None`,
`recovery_censored = True`, `recovery_observed_until_s` records follow-up. **Never filled
with a number.**

### 5.3 Sampling **[v2, amendment (e)]**

- **Lagged probe window:** query `[now − 15 s, now − 5 s]`, not `[now − 10 s, now]`.
  Jaeger flushes spans in batches; a window ending at "now" samples a partially-written
  interval.
- **Minimum 20 traces** per sample before its percentiles may vote for recovery.
- Nominal poll 1 s; **measured effective resolution 1.4–2.4 s** (each iteration issues
  `1 + N_services` Jaeger queries). The paper reports the measured figure.

Verified by 2 confirmation runs on the condition that exhibited the defect: median traces
per sample **13–18 → 34–38**, thin samples voting for recovery **6 and 4 → 0 and 0**.

### 5.4 Which indicator is valid for which fault type **[v2, amendment (d)]**

**Δp95 is invalid as a severity measure for kill faults.** Every HR kill produced
Δp95 of **−44 to −53 ms** while 51–56% of requests were failing: when a service dies its
requests fail fast, so the surviving latency distribution is dominated by fast failures and
p95 *drops*. In SN the largest Δp95 (+8867 ms) coincided with the *lowest* error rate.

| Fault type | Primary indicator | Δp95 status |
|---|---|---|
| **kill** | **error rate** | descriptive only |
| latency | *see §10 open question 2* | *see §10* |
| cpu | *see §10 open question 2* | *see §10* |

---

## 6. Baseline metrics for comparison (unchanged set, reordered)

All are computed for every analysis-set service and compared against every outcome. None
may be dropped after seeing results.

| # | Metric | Rationale |
|---|---|---|
| 1 | **|ancestors|** | **[v2]** the predictor the causal chain supports |
| 2 | In-degree | direct-caller count |
| 3 | Degree | `degree_centrality` |
| 4 | Out-degree | fan-out — predicted *not* to work |
| 5 | Betweenness | directed |
| 6 | Closeness | — |
| 7 | Eigenvector | L2; **degenerate**, disclosed |
| 8 | PageRank | α = 0.85 |
| 9 | Composite | mean of 7 normalised ranks, ties `method="min"` |
| 10 | Descendant count | reachable set |
| 11 | Dominator subtree size | nodes disconnected on failure |
| — | **Hybrid (under test)** | §2 |

---

## 7. Statistical plan

**Primary test.** Spearman ρ between each metric and each primary outcome, **per
architecture**, at the **service level** (n = 11 SN, n = 7 HR), aggregating repetitions by
the **median**.

**[v2] All p-values come from exact permutation tests** (10 000 permutations, or the exact
enumeration where n! permits), never the asymptotic Spearman approximation. Justification
is in §3: with HR's 5/2 tie structure the asymptotic test has a measured false-positive
rate of 0.097 against a nominal 0.05.

**Censoring.** $T_{rec}$ is censored, so its confirmatory test is survival-based:
Kaplan–Meier by metric tercile, **log-rank**, and **Cox proportional hazards** with the
metric as a continuous covariate (hazard ratio + 95% CI) as the primary inferential
result. Spearman ρ is reported alongside, computed on uncensored observations only and
**labelled biased toward fast recoveries**. If under 10% of observations are censored,
Spearman is promoted to primary — that threshold is fixed here, in advance.

**Multiple comparisons.** Confirmatory family = **11 metrics × 2 primary outcomes
(ancestor_affected_count, $T_{rec}$) × 2 architectures = 44 tests**, corrected by
**Benjamini–Hochberg FDR at q = 0.05** across the whole family. Secondary outcomes
(Δp95, Δp99, Δerror, descendant/unrelated counts) form a separate exploratory family,
corrected separately and labelled exploratory.

**Effect size.** ρ with bootstrap BCa 95% CI (10 000 resamples); hazard ratio with 95% CI.
A significant result whose CI crosses a negligible effect is reported as **inconclusive**,
not as support.

**Power.** n = 11 and n = 7 services. **This study is underpowered at the service level
and will say so plainly.** Increasing repetitions does not help — the unit of analysis is
the service, and there are only 11 and 7. HR additionally cannot exceed ρ = 0.791 even
with a perfect result (§3). This is a structural limit of two-benchmark designs and
belongs in Limitations, not in a hedge.

---

## 8. Data collection plan

**Target: 5 repetitions per (service × fault type), balanced.**

| Architecture | Services faulted | Fault types | Reps | Runs |
|---|---:|---:|---:|---:|
| Social Network | 11 (gateway excluded) | *§10 Q2* | 5 | up to 165 |
| Hotel Reservation | 7 (gateway excluded) | *§10 Q2* | 5 | up to 105 |
| | | | | **up to 270** |

- **Balance is mandatory.** Prior batches were unbalanced precisely on the services
  carrying the headline claims. A failed run is re-run, never topped up unevenly.
- Faults: Pumba `kill --signal SIGKILL`; `netem delay --time 500 --jitter 100`;
  `stress --cpu 2`. **[v2]** netem/stress are launched with `Popen` and the runner waits
  for that process before recording the removal instant — running them synchronously let
  the rule expire before the fault window began (`_quarantine/QUARANTINE_LOG.md` item 10).
- Protocol per run: 60 s warm-up → baseline → 30 s fault → recovery probe to 180 s → 20 s
  cooldown. **This is what will actually run**; the manuscript's stated 60 s warm-up was
  never what the code did.
- **A run with `telemetry_ok = False` is discarded and re-run**, never analysed as zeros.
- **[v2]** The runner holds a PID lockfile and refuses to start concurrently.

**Measured timing.** Median run 116 s, mean 129 s over 10 pilot runs (max 244 s, the
censored one). At the pilot's 1-in-8 censoring rate, 270 runs ≈ **9–10 h**; **12–16 h
realistic** with stack swaps, seeding and re-runs. One stack at a time is a hard
constraint (`_audit/MEMORY_CEILING.md`).

---

## 9. Reporting commitments

1. **If the result is null, it is reported as null.** If the hybrid metric does not beat
   in-degree on the held-out architecture after FDR correction, the paper says the fan-out
   correction did not predict impact under this measurement setup. No metric redefined, no
   fault type dropped, no service excluded, no outcome swapped to improve it.
2. **[v2] The reversed causal direction is reported prominently**, including that it
   contradicts the hybrid metric's premise, and including that `compose-post-service` —
   the paper's central "false negative" — has the *lowest* |ancestors| in its analysis set.
3. **Every number is produced by a script reading `data/raw/` or `data/pilot/`**, with
   script and commit recorded. No number is typed into the manuscript by hand.
4. **All 44 confirmatory tests are reported**, significant or not, with corrected p-values.
5. **Deviations from this document are listed** in a "Deviations from preregistration"
   section with dates and reasons.
6. **The audit is cited.** The paper states that an earlier analysis was withdrawn after
   fabricated data was found, and what changed.
7. **The structural result stands on its own.** That classical composite ranking demotes
   high-fan-out orchestrators is reproducible from `data/centrality/` alone and needs no
   fault-injection data. If H1 is null this becomes the paper's main claim.

---

## 10. Open decisions before locking

**Q1 — Hotel Reservation's role.** With n = 7, two predictor levels, a ρ ceiling of 0.791
and an anti-conservative asymptotic test, HR cannot confirm or refute anything decisively.
Options: **(a)** keep it as the held-out set with permutation tests and report it as
directional only *(recommended)*; **(b)** drop the cross-arch protocol, fix weights a
priori per `metric_constants.py`, and use both architectures descriptively; **(c)** add a
third benchmark — out of scope for this timeline.

**Q2 — Fault types in the campaign, and their valid indicators.** Pending the 4
latency/CPU pilot runs now in flight. Kill is settled: error rate primary, Δp95
descriptive. Latency/CPU recommendation follows from that data and will be filled in
before locking.

**Q3 — `per-service` metric semantics.** `_audit/PER_SERVICE_METRIC_SEMANTICS.md`:
per-service p95 is currently the *end-to-end* p95 of traces touching that service, because
percentiles are computed from root spans. This does not affect the kill-fault ancestor
result but makes the A/D/U classification non-comparable across fault types.
**Recommended: fix for the campaign, treat the 10 pilot runs as method development.**

| | |
|---|---|
| Q1 — HR's role | ☐ (a) held-out, permutation, directional ☐ (b) fixed weights, descriptive ☐ (c) third benchmark |
| Q2 — fault types | ☐ pending pilot data |
| Q3 — metric semantics | ☐ fix for campaign ☐ fix + re-run pilot ☐ keep and rename |
| Approved by | ______________________ |
| Date | ______________________ |
