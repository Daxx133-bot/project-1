# Step 1 — Is per-timestep telemetry retroactively recoverable?

**Date:** 2026-09-24

## Verdict: **MUST BE RE-RUN**

Per-timestep telemetry — p95/p99/error-rate/downstream-count sampled at multiple points
*during* the fault window — **does not exist anywhere** for the 122-run SN batch or the
81-run HR batch, and cannot be reconstructed. Three independent lines of evidence, any
one of which is sufficient.

---

## Evidence 1 — The collection code was never capable of it

The old pipeline took exactly **two point measurements** per run:

- `collect_baseline_metrics(...)` — one query over the warm-up window
- `collect_fault_window_metrics(...)` — one query over `[fault_start_us, fault_end_us]`

A grep for any sampling loop across `measurement/`, `faultinjection/` and `scripts/`
returns exactly one `while` loop — `fault_runner.py:232`, the `docker inspect` restart
poll, which records no telemetry at all. Nothing in the codebase ever sampled latency or
error rate more than once per window. **The data was never generated.**

## Evidence 2 — The stored artefacts are scalar-only

All **304** run JSONs (`measurement/results_controlled/`, `measurement/results/`) contain
**exactly the same 18 keys**, every one a scalar:

```
baseline_error_rate  baseline_p95_ms  baseline_p99_ms  downstream_affected_count
downstream_affected_services  error_rate_delta  fault_error_rate  fault_p95_ms
fault_p99_ms  fault_type  health_check_pass  integration_tests_pass
latency_p95_delta_ms  latency_p99_delta_ms  recovery_time_s  repetition
service  timestamp
```

No list-valued or dict-valued field appears in any file. `run_manifest.csv` adds only
`start_time`/`end_time`/`status`/`notes` — still one row per run. There is no metrics
database, no `.db`/`.sqlite`/`.tsdb`/badger file anywhere in the repository.

## Evidence 3 — The raw spans are gone, so recomputation is impossible

The one remaining route would be to re-query Jaeger over the original windows with a fine
grid. That route is closed:

- **Storage is in-memory.** The Jaeger containers run `jaegertracing/all-in-one:1.62.0`
  with **no `SPAN_STORAGE_TYPE`** set (default = `memory`) and **no storage volume** —
  the single mount on `socialnetwork-jaeger-agent-1` is an anonymous volume on `/tmp`.
- **Verified empty.** `GET /api/services` returns `{"data":null,"total":0}`, and an
  explicit query over the controlled-batch window
  (2026-09-18 17:00 → 2026-09-20 10:00 UTC) returns **0 traces**.
- **The container has restarted since**, under `restart: always`, which wipes memory
  storage. `socialnetwork-jaeger-agent-1` was itself created 2026-09-20 14:53 IST —
  *during* the batch it was supposedly recording.
- **No raw exports cover the period.** Only two trace dumps exist:
  `sdg/raw_traces/raw_traces.json` (2026-09-09, 43 spans) and
  `sdg/raw_traces/hotel/raw_traces.json` (2026-09-13, 16 970 spans). Both **predate** the
  Sep 18–20 batches.

---

## Consequence for scope

| | |
|---|---|
| Reusable from the 203 controlled runs | **Nothing for a time-resolved outcome.** The scalar Δp95 / Δp99 / Δerror / downstream-count remain usable as *secondary* outcomes, but `recovery_time_s` in those batches is container-restart time and must be discarded entirely. |
| Must be re-collected | The **primary outcome** in full. Every run in the campaign must be re-executed with `recovery_probe.py`. |
| Timeline impact | The 300-run campaign in `PREREGISTRATION.md` §7 is **not** reducible by reusing old runs. It must run from scratch. |

This is the expected answer given the audit, but it is now established from the artefacts
rather than assumed.
