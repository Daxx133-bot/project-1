# Zero-Telemetry Diagnosis (Step 3)

**Date:** 2026-09-23 · **Scope:** diagnosis only, no fixes applied.
No containers were started; every conclusion below rests on artefacts already on disk.

---

## 0. The premise needs correcting first

The session brief states *"HR's `downstream_affected_count` is zero across all real runs."*
**That is true only of the older batch.** Measured across `data/raw/`:

| Batch | `downstream_affected_count` non-zero | `fault_p95_ms` non-zero | `baseline_p95_ms` non-zero |
|---|---:|---:|---:|
| `hr_sep13` (42) | **0 / 42** | 0 / 42 | **0 / 42** |
| `hr_controlled_sep18-20` (81) | **37 / 81** | 68 / 81 | 69 / 81 |
| `sn_legacy` (59) | **0 / 59** | 0 / 59 | 58 / 59 |
| `sn_controlled_sep18-20` (122) | **71 / 122** | 88 / 122 | 105 / 122 |

**The zero-telemetry failure is confined to the two older batches (`hr_sep13`, `sn_legacy`)
and was largely fixed before the Sep 18–20 controlled runs.** This matters: it means the
project already has working telemetry, and step 3 is a post-mortem on superseded data
rather than a blocker on re-collection.

It also means the two batches are **not** a single fault. They have different signatures
and different causes.

---

## 1. Two distinct failure signatures

| | `hr_sep13` | `sn_legacy` |
|---|---|---|
| Baseline p95 | **zero** (0/42) | **present** (58/59) |
| Fault-window p95 | zero | zero |
| Diagnosis | **No traffic at all** during runs | **Near-zero traffic**; baselines computed from stray traces |

A total-telemetry outage produces zeros in *both* windows (`hr_sep13`). A workload that
never really ramped produces a populated-but-garbage baseline and an empty fault window
(`sn_legacy`). They cannot share one root cause.

---

## 2. Evidence, hypothesis by hypothesis

### (a) Was Jaeger running and receiving spans? — **YES. Ruled out.**

`sdg/raw_traces/hotel/raw_traces.json` is a live Jaeger capture:

```
metadata: {"collected_at": "2026-09-13T11:07:46+0530",   # = 05:37:46 UTC
           "trace_count": 1644, "span_count": 16970}
span time range: 2026-09-13 05:34:14 -> 05:37:41 UTC
services present: frontend 1639, profile 1265, search 1000, rate 1000,
                  reservation 1000, geo 1000, recommendation 265
```

The `hr_sep13` batch began at **05:40:02 UTC** — **2 min 16 s after** this capture.
Jaeger was healthy, indexing, and serving 1 644 traces across all 7 services minutes
before a batch that recorded 0.0 for every metric in all 42 runs.

**Jaeger is exonerated for `hr_sep13`.** The collector was demonstrably up; the runs
simply sent it nothing.

### (b) Was the workload intense enough / were containers OOM-killed? — **NO OOM EVIDENCE. Not the primary cause, but real contention exists in `sn_legacy`.**

- **Against OOM:** `health_check_pass` is `True` in **304/304 runs across all four
  batches**. An OOM-kill cascade would show as gateway health failures, and does not.
  `integration_tests_pass` fails in 18/81 (HR) and 32/122 (SN) of the controlled runs —
  but those are the runs where a service was *deliberately killed*, which is expected.
- **For contention in `sn_legacy` specifically:** its `baseline_p95_ms` reaches
  **4816 ms**, with 5 of 59 runs above 1000 ms. The controlled SN batch never exceeds
  **299 ms**. A 16× spread in baseline tail latency between batches on identical hardware
  indicates the Sep 5–9 runs executed under heavy contention — consistent with a 15.7 GB
  machine hosting the full 12-service stack plus Jaeger, MongoDB, Redis and Memcached.
- **But contention does not explain zeros.** A loaded system produces *slow* traces, not
  *absent* ones. See (c).

**Verdict: contention is real in `sn_legacy` and corrupts its baselines, but it is not
the cause of the zeros.** RAM pressure remains a live risk for re-collection and should
be mitigated, not dismissed.

### (c) Metric-collection bug — **THIS IS THE PRIMARY CAUSE, in two parts.**

**(c1) `start_load()` silently no-op'd under `--load-mode wrk2`.**

Documented contemporaneously in `docs/TELEMETRY_DIAGNOSTIC_REPORT.md` (Sep 19):
`faultinjection/fault_runner.py::start_load()` handled `mode == "locust"` but had **no
`elif mode == "wrk2"` branch**, so it fell through to `return None`. The batch runner
`scripts/run_controlled_experiment.py` passes `--load-mode wrk2` (line ~225). Result:
no load generator was ever spawned, no requests reached the gateway, Jaeger recorded
nothing for the run windows, and the collector faithfully reported 0.0.

I verified the fix is now present (`fault_runner.py:339`, `elif mode == "wrk2":`). The
report's before/after is consistent with the batch data: baseline p95 `0.0 → 25.89 ms`,
fault p95 `0.0 → 1625.37 ms`, blast radius `0 → 1`.

This fully explains **`hr_sep13`** (zeros in *both* windows) and the graph/run paradox:
the 1 644-trace capture came from `infra/generate_hotel_load.py` driven **manually** for
graph extraction, while the fault-injection runs minutes later drove no load at all.

**(c2) A latent design bug that made (c1) invisible — still unfixed.**

`measurement/metrics_collector.py` conflates three different states into the same output:

```python
except requests.RequestException as e:          # line 68
    print(f"  [WARNING] Failed to fetch traces for {service}: {e}")
    return []                                    # Jaeger unreachable -> []
...
if len(durations_ms) == 0:                       # line 102
    return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, ...}
```

`0.0` therefore means **"Jaeger is down"**, **"no traffic was generated"**, and
**"the service was healthy with zero latency"** — indistinguishable in the CSV.
`trace_count` is computed but **never written to the output schema**, so the one field
that would disambiguate is discarded before it reaches disk.

This is why a total workload outage ran undetected across 101 runs and two applications
for two weeks, and why the numbers looked like legitimate measurements.

**Not found:** no off-by-one or unit error in the windows. Baseline uses
`[now - window*1e6, now]`, fault uses `[fault_start_us, fault_end_us]`, both microseconds,
both via the same `get_traces_in_window()`. `total_duration = warmup + fault_duration + 30`
correctly spans the fault window. The endpoint (`/api/traces?service=&start=&end=&limit=`)
and the service names both match what Jaeger registers. **The query mechanics are correct.**

One residual risk not testable offline: `limit=500` truncation. At 50 RPS over a 60 s
window a service can produce far more than 500 traces, and Jaeger returns the newest 500.
This would bias percentiles toward the end of the window rather than zero them — it does
not cause this failure, but it should be fixed before re-collection.

### (d) Was Prometheus (or any per-service error-rate scraper) running? — **NOT APPLICABLE.**

**There is no Prometheus in this project.** A case-insensitive grep across all `.py`,
`.yml` and `.yaml` files returns zero hits. Per-service error rates are derived entirely
from Jaeger spans (`error=true` tag or `http.status_code >= 500`) in
`compute_error_rate()`. There is no second telemetry path that could have failed, and
none that needs to be started for re-collection.

---

## 3. Additional finding: the `user` service (answers step 7's question with evidence)

`user` is absent from every HR trace and therefore from the dependency graph. The cause
is now established exactly, and it is **not** a tracing problem — the requests are
rejected before any RPC is made.

`hotel_load_stats_failures.csv` (Locust, 2026-09-18):

```
GET,  /user [lookup],        HTTPError('400 Client Error: Bad Request'),  33 occurrences
POST, /reservation [book],   HTTPError('400 Client Error: Bad Request'),  55 occurrences
```

**100 % failure rate on both** (33/33 and 55/55 in `hotel_load_stats_stats.csv`).

Cause, from DeathStarBench source `services/frontend/server.go`:

```go
mux.Handle("/user", http.HandlerFunc(s.userHandler))          // line 99
func (s *Server) userHandler(...) {
    username, password := r.URL.Query().Get("username"), r.URL.Query().Get("password")
    if username == "" || password == "" {
        http.Error(w, "Please specify username and password", http.StatusBadRequest)
        return                                   // <-- returns BEFORE s.userClient.CheckUser
    }
```

`infra/_locustfile_hotel.py::get_user()` sends **`params={"username": ...}` and no
`password`** → 400 → `userClient.CheckUser()` is never reached → no `frontend→user` span
is ever emitted → `user` cannot appear in the graph. The chain is complete.

The same file's `make_reservation()` has **two** bugs against the same handler:

```go
func (s *Server) reservationHandler(...) {
    inDate, outDate := r.URL.Query().Get("inDate"), r.URL.Query().Get("outDate")   // QUERY params
    ...
    username, password := r.URL.Query().Get("username"), r.URL.Query().Get("password")
    num := r.URL.Query().Get("number")
```

1. The locustfile sends a **JSON body** (`json={...}`); the handler reads **query
   parameters** only → `inDate` empty → 400 on the first check.
2. Even as query params it would fail: no `username`/`password`, and it sends
   `roomNumber` where the handler reads `number`.

**Consequence for the paper:** the HR workload exercised only `/hotels` (search) and
`/recommendations`. The observed 6-edge graph — `frontend→{search, recommendation,
reservation, profile}`, `search→{geo, rate}` — is exactly the union of those two call
paths (`frontend→reservation` comes from `searchHandler`'s availability check, not from
booking). **The reservation *write* path was never exercised**, which undercuts the
manuscript's narrative around the `reservation` anomaly. `sdg/hotel_expected_services.py`
correctly lists 8 services and 8 edges; the 2 missing edges are both `→user`.

This is a **fixable workload bug**, not a limitation of the architecture.

---

## 4. Additional finding: the Social Network graph's raw traces no longer exist

Not part of the brief, but it blocks reproducibility and should be recorded.

| Artefact | Modified | Content |
|---|---|---|
| `sdg/output/sdg.json` (SN graph) | **2026-08-24** | 12 nodes, 19 edges, **9 091 recorded calls** |
| `sdg/raw_traces/raw_traces.json` (SN traces) | **2026-09-09** | 26 traces, **43 spans**, of which **23 traces are `jaeger-all-in-one` self-instrumentation** — only **3 real application traces** |

The surviving dump postdates the graph by 16 days and contains ~0.5 % of the spans the
graph encodes. **The trace capture that produced the Social Network dependency graph was
overwritten and is gone.** Table 1, the 19 edges, and compose-post-service's out-degree
of 7 — the structural backbone of the paper — currently cannot be regenerated from any
file in this repository.

The Hotel Reservation graph does **not** have this problem: its dump (16 970 spans,
Sep 13) is intact and consistent with its 5 530 recorded calls.

The 3-real-traces dump also independently corroborates §2(c1): on Sep 9 the Social
Network stack was receiving essentially no traffic, which is why `sn_legacy`'s baselines
are built from a handful of stray traces and reach 4816 ms.

---

## 5. Probable causes, ranked

| # | Cause | Confidence | Evidence | Affects |
|---|---|---|---|---|
| 1 | **`start_load()` no-op under `--load-mode wrk2`** — no workload generated during runs | **High** | `docs/TELEMETRY_DIAGNOSTIC_REPORT.md` §1/§7 with matching before/after; Jaeger proven healthy 2 min before the batch; fix now present at `fault_runner.py:339` | `hr_sep13` (all 42), `sn_legacy` (fault windows) |
| 2 | **`0.0` overloaded across "Jaeger down" / "no traffic" / "no degradation"**, and `trace_count` discarded before it is written | **High** | `metrics_collector.py:68, 102`; `trace_count` computed but absent from the output schema | All batches — **still unfixed**; this is why #1 went unnoticed for two weeks |
| 3 | **Malformed `/user` and `/reservation` requests** → 400 at the gateway → RPCs never issued | **Certain** | 33/33 and 55/55 failures in `hotel_load_stats_failures.csv`; DSB `server.go` handlers read query params and require `password` | Missing `user` node and both its edges in every HR graph |
| 4 | **Resource contention** on a 15.7 GB host | **Moderate** | `sn_legacy` baseline p95 up to 4816 ms vs 299 ms max in the controlled batch | Corrupts `sn_legacy` baselines; a forward risk, not the cause of zeros |
| 5 | `limit=500` trace truncation | **Low / latent** | `metrics_collector.py:36` | Would bias percentiles in high-RPS windows; not implicated here |

**Ruled out:** Jaeger collector failure (#a — disproven by the 1 644-trace capture);
query window off-by-one or unit error (#c — windows verified correct);
Prometheus/scraper failure (#d — no Prometheus exists in this project).

---

## 6. Recommended fixes — for approval, not yet applied

1. **Write `trace_count` (baseline and fault) into the output schema**, and record an
   explicit `telemetry_ok` flag. Make a run with zero traces **fail loudly** rather than
   log `0.0`. Without this, any future outage is again invisible. *(Highest value, lowest risk.)*
2. **Fix `_locustfile_hotel.py`**: add `password` to `/user`; convert `/reservation` to
   query parameters with `username`, `password` and `number`. Then re-extract the HR
   graph — it should gain the `user` node and the `frontend→user` and
   `reservation→user` edges, giving the 8-node/8-edge graph the manifest expects.
3. **Assert non-empty load before injecting**: probe the gateway after warm-up and abort
   the run if the baseline trace count is zero.
4. **Raise or paginate the `limit=500`** trace cap.
5. **Re-capture the Social Network traces** and re-derive `sdg/output/sdg.json`, so the
   graph underpinning Table 1 has surviving provenance.
6. **Reduce concurrent memory pressure** during re-collection (bring up one application
   at a time; cap container memory) given the 4816 ms baseline excursions.

Items 1–4 and 6 are prerequisites for trustworthy re-collection. Item 5 is a
reproducibility debt that must be paid before the graph results can be defended.
