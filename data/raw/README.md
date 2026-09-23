# `data/raw/` — Single Source of Truth for Experimental Data

Built by [`tools/build_raw_dataset.py`](../../tools/build_raw_dataset.py).
Re-verify at any time with `python tools/build_raw_dataset.py --verify-only`.

Each file is a **copy** of a genuine experiment batch, every original column retained,
plus one added column `batch`. **Nothing here is merged, deduplicated or filtered** —
those are analysis-time decisions, recorded in `PREREGISTRATION.md`, not storage-time ones.

Originals remain in place under `measurement/` pending a later cleanup commit.

> **The contaminated log is not here.** `measurement/results/experiment_log.csv` mixed 48
> fabricated rows with 59 real ones and is quarantined
> (`_quarantine/QUARANTINE_LOG.md` item 4). Its genuine rows are recovered here as
> `sn_legacy.csv`, rebuilt from the per-run JSON records, which `populate_results.py`
> never touched.

---

## Batches

| File | Rows | Application | Dates (UTC) | md5 (12) |
|---|---:|---|---|---|
| `sn_controlled_sep18-20.csv` | 122 | Social Network (12 svc) | 2026-09-18 17:53 → 09-20 09:28 | `550a8fd361e1` |
| `hr_controlled_sep18-20.csv` | 81 | Hotel Reservation (7 svc) | 2026-09-18 18:03 → 09-20 09:23 | `421086d072e5` |
| `hr_sep13.csv` | 42 | Hotel Reservation (7 svc) | 2026-09-13 05:40 → 07:06 | `39e7497f3393` |
| `sn_legacy.csv` | 59 | Social Network (12 svc) | 2026-09-05 04:27 → 09-09 06:24 | `2af4dba418b0` |

**Total genuine runs: 304.** (The manuscript's claimed 72 + 42 = 114 matches no batch or
combination of batches. See `_audit/AUDIT_REPORT.md` §C.)

---

### `sn_controlled_sep18-20.csv` — 122 runs — **best available dataset**

Source: `measurement/results_controlled/socialnetwork/experiment_log.csv`

- **Services (12):** compose-post, home-timeline, media, nginx-web-server, post-storage,
  social-graph, text, unique-id, url-shorten, user-mention, user, user-timeline.
- **Fault types:** kill 41 / latency 41 / cpu 40.
- **Repetitions:** 3 per (service × fault) for 33 of 36 cells; **unbalanced** —
  `compose-post-service` has 8/8/7 and `nginx-web-server` 3. The over-sampling of
  compose-post-service is the very service the paper's central claim is about, and it is
  not disclosed in the manuscript.
- **Cadence:** median 131 s between runs (min 81 s), no duplicate timestamps.

| Column | Trust |
|---|---|
| `baseline_p95_ms`, `baseline_p99_ms` | **Usable** — non-zero in 105/122. Range 0–299 ms. |
| `fault_p95_ms`, `fault_p99_ms` | **Usable with care** — non-zero in 88/122. Max 6513 ms. A zero here after a `kill` fault is genuine signal (traces vanish), not a gap; after latency/cpu it is a gap. Must be disambiguated per fault type. |
| `fault_error_rate`, `error_rate_delta` | **Weak** — non-zero in only 29/122. |
| `downstream_affected_count` | **Usable** — non-zero in 71/122, range 0–11. |
| `recovery_time_s` | **BROKEN — container-restart-time, NOT validated recovery.** See below. |
| `health_check_pass`, `integration_tests_pass` | Usable as booleans. |

---

### `hr_controlled_sep18-20.csv` — 81 runs

Source: `measurement/results_controlled/hotelreservation/experiment_log.csv`

- **Services (7):** frontend, geo, profile, rate, recommendation, reservation, search.
  **`user` is absent** — it is in the ground-truth manifest
  (`sdg/hotel_expected_services.py`) but appears in no trace and no run.
- **Fault types:** 27 kill / 27 latency / 27 cpu.
- **Repetitions:** 3 per (service × fault) for 18 of 21 cells; `reservation` has **9** per
  fault type. **Unbalanced**, and again on the service carrying the paper's HR anomaly claim.
- **Cadence:** median 97 s (min 76 s), no duplicate timestamps.

| Column | Trust |
|---|---|
| `baseline_p95_ms`, `baseline_p99_ms` | **Usable** — non-zero in 69/81. |
| `fault_p95_ms` | **Usable** — non-zero in 68/81, max 12 732 ms. |
| `fault_error_rate` | **Weak** — non-zero in 18/81. |
| `downstream_affected_count` | **Usable** — non-zero in **37/81**, range 0–6. |
| `recovery_time_s` | **BROKEN — container-restart-time, NOT validated recovery.** |

---

### `hr_sep13.csv` — 42 runs — **recovery-time only**

Source: `measurement/results/hotel/experiment_log.csv`

The only batch whose run count matches a number in the manuscript ("42 runs"). One clean
86-minute sequential block, median gap 122 s, perfectly balanced at **2 repetitions per
(service × fault)** across 7 services × 3 fault types.

**Every latency, percentile, error-rate and blast-radius column is exactly `0.0` for all
42 runs.** The only informative column is `recovery_time_s` — and that column is broken
in the sense described below. Supersedes nothing; superseded by
`hr_controlled_sep18-20.csv`.

| Column | Trust |
|---|---|
| `baseline_p95_ms`, `fault_p95_ms`, `*_p99_ms`, `*_error_rate`, `downstream_affected_count` | **UNUSABLE — identically zero in all 42 runs.** Telemetry did not reach the collector. |
| `recovery_time_s` | **BROKEN — container-restart-time, NOT validated recovery.** This batch is the source of the manuscript's Table 6, including the 61.07 s `reservation` figure. |

---

### `sn_legacy.csv` — 59 runs — **superseded, baseline-only**

Source: rebuilt from `measurement/results/run_*.json` (Sep 5–9), **not** from the
contaminated CSV. Carries an extra `_source_file` column naming the JSON each row came from.

- **Repetitions:** highly unbalanced — 15 cells have 1 rep, 13 have 2, 6 have 3.
- Superseded by `sn_controlled_sep18-20.csv`. Retained for provenance and for the
  baseline-latency distribution only.

| Column | Trust |
|---|---|
| `baseline_p95_ms`, `baseline_p99_ms` | **Usable** — non-zero in 58/59. Note max 4816 ms, far above the controlled batch's 299 ms: this batch ran under heavier contention. |
| `fault_p95_ms`, `fault_p99_ms`, `*_error_rate`, `downstream_affected_count` | **UNUSABLE — identically zero in all 59 runs.** Fault-window telemetry never arrived. |
| `recovery_time_s` | **BROKEN — container-restart-time, NOT validated recovery.** |

---

## `recovery_time_s` — read this before using it

**In every batch, `recovery_time_s` is container-restart-time, NOT validated recovery.**

It was produced by `faultinjection/fault_runner.py::restore_service()`, which polls
`docker inspect --format {{.State.Running}}` every 2 s with `max_wait = 60` and returns
the elapsed wall time. It answers *"is the container process running again?"* — not
*"has the application returned to baseline latency and error rate?"*, which is what the
manuscript's definition claims.

Three consequences:

1. **For `latency` and `cpu` faults the value is meaningless.** These faults never stop
   the container, so the poll loop succeeds on its first iteration. The recorded
   0.05–0.18 s is the round-trip latency of a single `docker inspect` call. Every such
   value in every batch is measurement noise.
2. **The variable is effectively three-valued**: ~0.1 s (non-kill), ~1–2 s (kill that
   restarted), ~61 s (kill that did not restart within the cap).
3. **Values near 61 s are censored, not measured.** They are the `max_wait = 60` ceiling
   plus one poll interval. Observed ceilings across batches: 60.82, 60.87, 60.92, 60.98,
   61.05, 61.07, 61.09, 61.46, 61.68, 62.03. **No value in any batch can exceed ~62 s by
   construction.** The manuscript's 61.07 s `reservation` figure is this ceiling, not a
   MongoDB connection-pool timeout.

A corrected implementation (`recovery_time_s` proper, with explicit censoring) is in
`measurement/recovery_probe.py`; the old measurement is preserved under its honest name
`container_restart_time_s`. **No existing batch contains the corrected metric** — it
requires re-collection.

---

## Known-broken columns at a glance

| Column | `sn_controlled` | `hr_controlled` | `hr_sep13` | `sn_legacy` |
|---|---|---|---|---|
| `baseline_p95_ms` / `p99` | usable (105/122) | usable (69/81) | **zero** | usable (58/59) |
| `fault_p95_ms` / `p99` | usable (88/122) | usable (68/81) | **zero** | **zero** |
| `fault_error_rate` | weak (29/122) | weak (18/81) | **zero** | **zero** |
| `downstream_affected_count` | usable (71/122) | usable (37/81) | **zero** | **zero** |
| `recovery_time_s` | **broken** | **broken** | **broken** | **broken** |

The zero-telemetry failure is confined to the two **older** batches (`hr_sep13`,
`sn_legacy`). The Sep 18–20 controlled batches largely fixed it. See
`_audit/TELEMETRY_DIAGNOSIS.md`.
