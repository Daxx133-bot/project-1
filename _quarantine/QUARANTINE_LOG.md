# Quarantine Log

Files moved here are **not deleted** (per `CLAUDE.md` rule 5). They are preserved at their
original relative paths under `_quarantine/` so the provenance chain stays auditable.

**Nothing in this directory may be cited, re-run, or used to produce a number in the paper.**

Authority: `_audit/AUDIT_REPORT.md` (2026-09-23).
Quarantined: 2026-09-23.

---

## 1. `scripts/populate_results.py` → `_quarantine/scripts/populate_results.py`

**Defect: fabricates experimental measurements.**

Calls `random.seed(42)` and generates every impact value with `random.uniform()` /
`random.randint()` from hand-written ranges **selected by reading the service's own
centrality scores** (`out_degree`, `in_degree`, `composite_rank` from
`centrality/output/centrality_table.csv`). Its docstring claims it "Generates the
empirical failure measurements across all 12 microservices"; it measures nothing.

Audit refs: §D.2 (fabrication), §E.3/E.4/E.5 (circularity — impact derived from the same
centrality the study claims to validate).

Violates `CLAUDE.md` rules 1 and 3.

---

## 2. `scripts/generate_fig5.py` → `_quarantine/scripts/generate_fig5.py`

**Defect: Figure 5 is fabricated end to end.**

The 12 plotted points are hardcoded literal arrays under the author's own comment
`# Define the 12 data points to roughly match the rho values`. The correlation
coefficients are drawn as matplotlib `text()` labels (`rho = 0.897`, line 37;
`rho = 0.234`, line 53), not computed from anything. The script reads no data file.
The plotted ranges match no real variable: real `hybrid_criticality` spans 0.036–0.301
and real `recovery_time_s` is ~0.1 / ~1 / ~61 s.

It also writes its output **outside the repository**
(`C:\Users\daksh\.gemini\antigravity-ide\brain\554b5cc2-.../`), so the figure in the
paper is not reproducible from this repo at all.

Audit refs: §D.1, §F (Figure 5 row).

Violates `CLAUDE.md` rules 1 and 2.

---

## 3. `q1_p1.py` → `_quarantine/q1_p1.py`

**Defect: every number is hand-typed; contains a previously undetected fabricated value.**

A `.docx` manuscript generator with **zero data reads** — no `read_csv`, no `open()`,
no `json`, no `Path()`. Verified by grep. Every figure in its prose was typed by hand.

Beyond the known `rho = 0.897` string (line 133), it asserts:

| Line | Claim | Reality |
|---|---|---|
| 134 | `rho = 0.841, p = 0.009 in Hotel Reservation` | **Newly detected fabrication.** Real HR hybrid-vs-recovery is **rho = 0.0891, p = 0.8494** (`_audit/repro/recomputed_correlations.csv`). Not a rounding error — opposite conclusion. |
| 130 | "96 controlled experiment runs" | A **fourth** mutually incompatible run count (paper says 72+42=114; disk holds 107 / 122 / 81 / 42 / 59). |
| 131 | Hotel Reservation "with 8 loosely coupled services" | Observed graph is **7 nodes**; `user` absent from every trace. |
| 140 | compose-post "empirical blast-radius rank 2" | The manuscript elsewhere claims rank 1. |

Quarantined wholesale rather than repaired: there is no computed content to preserve.
The docx **layout helpers** (`_fr`, `_fp`, `h1`, `tbl_row`, `set_page`,
`add_footer_pagenum`, etc., lines 1–110) are reusable and defect-free — extract them into
a clean `tools/docx_style.py` if a generator is rebuilt. Do not reuse lines 111–150
(`build_abstract`, `build_title`).

Audit refs: §D.3.

Violates `CLAUDE.md` rules 1 and 2.

---

## 4. `measurement/results/experiment_log.csv` → `_quarantine/measurement/results/experiment_log.csv`

**Defect: 48 of 107 rows are fabricated. This is the file the paper's statistics consumed.**

Rows 1–48 are the output of `populate_results.py` (item 1). Their signature:

- timestamps `2026-08-24T18:00:00Z` … `18:00:47Z`, **incrementing by exactly 1 s per row**
  (generated as `f"...18:00:{len(rows):02d}Z"`, not wall clock);
- `downstream_affected_services` is the literal placeholder `['downstream_<svc>_nodes']`;
- `baseline_error_rate` is exactly `0.001` on all 48 rows;
- `fault_type` is `latency_100ms`, a label appearing in no real run.

Rows 49–107 are **genuine** (Sep 5–9 legacy SN runs) but carry `fault_p95_ms = 0.0` and
`downstream_affected_count = 0` throughout — so **every non-zero blast-radius value in
this file is fabricated**.

The genuine rows are preserved separately and uncontaminated as
`data/raw/sn_legacy.csv`. Nothing is lost by quarantining this file.

Audit refs: §C (forensics), §D.2, §E.3.

---

## 5. `analysis/output/correlation_results.csv` → `_quarantine/analysis/output/correlation_results.csv`

**Defect: computed from the contaminated log (item 4).**

Produced by `analysis/correlation_analysis.py` reading
`measurement/results/experiment_log.csv`. Its current contents give
`hybrid_criticality, recovery_time_s = 0.8471` and `degree = 0.7874` — which already
**disagree with the published 0.897 / 0.867**, because the log grew by 9 real runs after
the paper's numbers were taken.

The analysis script itself is **not** quarantined; it is correct code fed bad input.

Audit refs: §F.

---

## 6. `analysis/output/cross_arch_correlation_comparison.csv` → `_quarantine/analysis/output/cross_arch_correlation_comparison.csv`

**Defect: this is the direct source of the paper's headline numbers, and it is contaminated
*and* stale.**

Contains `hybrid_criticality, recovery_time_s, rho_sn = 0.8969` → paper's **0.897**;
`degree, ..., rho_sn = 0.8669` → paper's **0.867**; `in_degree, ..., 0.2337, p = 0.4647`
→ paper's "rho = 0.234, p = 0.465".

Two independent defects:

1. **Contaminated** — traceable to a version of the log that was 49 % synthetic (48 of
   98 rows). Reproduced exactly by truncating the log at `2026-09-09T11:34:37+0530`.
2. **Stale** — generated from a since-overwritten `correlation_results.csv`. The current
   pipeline no longer produces these values.

On the clean 122-run SN dataset the same quantity is **rho = 0.0605, p = 0.85** (null).

Audit refs: §F (origin of the headline numbers).

---

## 7. `analysis/output/outlier_analysis.{csv,md}` → `_quarantine/analysis/output/`

**Defect: computed from the contaminated log (item 4).**

Not named in the original quarantine instruction, but `analysis/identify_outliers.py`
defaults to `measurement/results/experiment_log.csv` (line 227), so these inherit the
contamination.

**This resolves an item the audit left open.** `_audit/AUDIT_REPORT.md` §F marked the
paper's Table 5 values `3.38` and `7.15%` as SOURCE NOT FOUND. They are here:

```
compose-post-service,7,0.5,3.375,9.3525,0.071525,3.19125,2,5,True,"False Negative (low centrality, high impact)"
```

`downstream_affected_count = 3.375` → paper's **3.38**; `error_rate_delta = 0.071525` →
paper's **7.15 %**. Both are averages over the fabricated rows.

Note this row also assigns compose-post `blast_rank = 2`, matching `q1_p1.py` (item 3)
and contradicting the manuscript's "Rank 1" claim.

---

## 8. `analysis/plots/*.png` (11 files) → `_quarantine/analysis/plots/`

**Defect: rendered from the contaminated log and/or the contaminated correlation CSVs.**

`analysis/generate_plots.py` reads `analysis/output/correlation_results.csv` (line 283)
and `measurement/results/experiment_log.csv` (line 285). Every top-level plot therefore
inherits the contamination.

Moved: `composite_vs_blast_radius.png`, `correlation_heatmap.png`,
`cross_arch_correlation_bar.png`, `scatter_composite_score_vs_error_rate_delta.png`,
`scatter_composite_score_vs_latency_p95_delta_ms.png`,
`scatter_composite_score_vs_recovery_time_s.png`,
`scatter_degree_vs_error_rate_delta.png`,
`scatter_degree_vs_latency_p95_delta_ms.png`,
`scatter_degree_vs_latency_p99_delta_ms.png`,
`scatter_degree_vs_recovery_time_s.png`,
`scatter_hybrid_criticality_vs_recovery_time_s.png`.

`analysis/generate_plots.py` is **not** quarantined — correct code, bad input.

---

## Explicitly NOT quarantined

| Path | Why kept |
|---|---|
| `centrality/hybrid_weight_optimizer.py` | Leaky protocol, but to be **fixed** (step 5), not discarded. Until then it must not be run. |
| `analysis/plots/hotel/*.png` (6 files) | Rendered by `scripts/generate_hotel_plots.py` from `measurement/results/hotel/experiment_log.csv`, which is **real**. Caveat: any panel plotting `recovery_time_s` is plotting container-restart time (see `_audit/AUDIT_REPORT.md` §C). |
| `analysis/output/hotel/*` | Derived from the real HR batch. |
| `analysis/correlation_analysis.py`, `identify_outliers.py`, `generate_plots.py`, `cross_architecture_analysis.py` | Correct code fed contaminated input. Re-runnable against `data/raw/`. |
| `measurement/results/*.json`, `measurement/results/hotel/*`, `measurement/results_controlled/**` | Genuine run records. |
| `centrality/output/*` | Computed from the dependency graph only. Never touched outcome data. Table 1 and Table 5 of the paper reproduce exactly from these. |
| `EVIDENCE_FREEZE/derived/*` | Contains copies of contaminated derived tables, but the directory is an immutable historical snapshot. Flagged, not moved; it must be regenerated after re-collection. |

---

## 9. `data/pilot/pilot_socialnetwork_*.json` (3 files) → `_quarantine/data/pilot_contaminated_concurrent/`

**Quarantined 2026-09-24. Defect: two pilot processes injected faults into the same
stack concurrently.**

A first Social Network pilot was launched with `nohup ... &`. It appeared not to have
survived (its log was empty and no output arrived), so a second pilot was launched. Both
were in fact running. The duplicate is unmistakable in the artefacts:

```
pilot_socialnetwork_compose-post-service_kill_rep1_2026-09-23T19-17-44.732151+00-00.json
pilot_socialnetwork_compose-post-service_kill_rep1_2026-09-23T19-17-57.595215+00-00.json
```

Two runs labelled `rep1`, **13 seconds apart**, each killing `compose-post-service` while
the other's load generator and recovery probe were active. Their baseline p95 values
differ (56.07 ms vs 57.98 ms) and one recorded recovery at 45.45 s while the other was
already recovered at its first probe sample (35.32 s) — consistent with the second run
measuring a system the first had already perturbed.

Neither run can be attributed to a clean single-fault condition, so **both** are
quarantined along with the third file from the same interleaved period. No attempt is
made to salvage the "good" one: there is no way to establish which samples were taken
while the other pilot's fault was active.

The Hotel Reservation pilot (4 runs) is **unaffected** — it ran to completion as a single
process before this happened, and is retained in `data/pilot/`.

**Lesson, applicable to the campaign:** the runner must refuse to start if another
instance is live. A PID lockfile in `data/pilot/` (or `data/campaign/`) is the minimal
fix, and is required before the 300-run campaign, where an accidental double-launch would
silently corrupt a large fraction of the runs in exactly this way.
