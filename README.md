# Identifying Failure-Prone Microservices Using Graph Centrality Metrics

This repository contains a fault-injection study testing whether dependency-graph
centrality predicts how far a microservice failure spreads. We reconstructed service
dependency graphs from distributed traces for two DeathStarBench applications (Social
Network and Hotel Reservation), then ran a preregistered campaign of 180 fault-injection
runs — every non-gateway service, two fault types (process kill and 500 ms network delay),
five repetitions each, fully balanced — and measured which other services degraded. The
analysis plan, including the hypotheses, the primary predictor and outcome, the test
statistic and the multiple-comparisons correction, was written and locked before any
campaign data was collected.

## Outcome

**The preregistered confirmatory test was null after correction.** The primary test
(Social Network, `ancestor_count` versus measured `ancestor_affected_count`, kill faults)
gives rho = 0.785 with an uncorrected permutation p of 0.0080, which becomes a
Benjamini-Hochberg adjusted p of 0.3451 across the 44-test confirmatory family. **None of
the 44 confirmatory tests, and none of the 44 replication-family tests, is significant at
q = 0.05.** The hybrid criticality metric that this work set out to evaluate has a negative
correlation with measured blast radius in all four architecture-by-fault cells and is
distinguishable from zero in none of them.

The study also records a structural observation that required no inference: no descendant
of a faulted service degraded in 179 of the 180 runs, and the service-level median
descendant count is zero for every service in every condition. Because that outcome has no
variance, it cannot be expressed as a correlation, and 88 of the 154 attempted exploratory
tests are undefined rather than null.

`paper/CLAIMS_LEDGER.md` is the authority on what these data do and do not support. It
marks every claim the manuscript might make as SUPPORTED, UNSUPPORTED or POST-HOC, and
names the `paper/numbers.csv` row backing each supported one. Claims marked UNSUPPORTED
there should not be made from this repository's results.

## Directory map

| Path | Contents |
|---|---|
| `data/raw/` | Trace corpora collected before the current campaign, retained as method-development material and not pooled with campaign results. |
| `data/campaign/` | The 180 campaign run records, one JSON per run, plus the run manifest and the runner's stdout logs. ~2 MB. |
| `data/spans/` | Raw Jaeger spans persisted per run, gzipped, for both the baseline and the fault window. ~53 MB across 366 files. These make every metric definition replayable without re-running the experiment. |
| `data/graphs/` | The frozen service dependency graphs reconstructed from traces. Every structural predictor is computed from these files. |
| `analysis/final/` | The preregistered analysis: `run_confirmatory_analysis.py` and its outputs, plus the supplementary leave-one-out, exact-p and blind-recomputation checks. |
| `paper/` | Everything the manuscript cites. `numbers.csv` holds one row per citable number with its source file and producing script; `tables/` and `figures/` hold the table- and figure-ready outputs; `draft/` holds section drafts; `CLAIMS_LEDGER.md` holds the claim-by-claim verdict. |
| `_audit/` | The research-integrity audit: the audit report, the locked preregistration and its version history, and the validation records for individual measurement decisions. |
| `_quarantine/` | Withdrawn files, preserved rather than deleted, with `QUARANTINE_LOG.md` recording what each item is and why it was removed. |

Supporting code sits in `sdg/` (trace collection and graph building), `centrality/` (metric
computation), `measurement/` (metric collection and blast-radius classification),
`faultinjection/` and `tools/` (the campaign runner), `infra/` (stack and load generation),
and `tests/`.

## Audit history

An earlier version of this analysis was withdrawn. A self-audit of the pipeline found that
part of what the earlier manuscript presented as experimental findings had not been
measured: impact values and recovery times were produced by code drawing from hard-coded
numeric ranges, and the metric weights carrying the headline correlation had been selected
by a grid search maximising that same correlation against the same outcome the manuscript
then reported, with no held-out data.

Those results were withdrawn in full. The affected scripts and outputs were **not deleted**;
they were moved to `_quarantine/`, which holds 13 numbered items, each documented in
`_quarantine/QUARANTINE_LOG.md` with what was removed and why. The findings themselves are
written up in `_audit/AUDIT_REPORT.md`.

**Nothing from the withdrawn material is used in the current results, with one exception:
the hybrid metric's weights.** The measurement pipeline, the metric implementation and the
analysis were rebuilt, and the campaign in `data/campaign/` was collected fresh under the
locked preregistration. The weights 0.4, 0.4 and 0.2 (`centrality/metric_constants.py`) were
inherited from the original proposal. In the earlier, withdrawn analysis they had been chosen
by an empirical search, so they are not a priori. We did not re-tune them on the campaign
data. The preregistered protocol, which tuned weights on Social Network and froze them for
Hotel Reservation, was not carried out (Deviation 10). Because the original search favoured
the metric, this is unlikely to explain a failure to find an association. Deviations from
the locked plan are logged in `PREREGISTRATION.md` §12 and tabulated in
`paper/tables/tbl_deviations.csv`; there are twelve, and the 17 runs invalidated across them
were quarantined and re-collected rather than analysed or dropped.

`EVIDENCE_FREEZE/` is a read-only forensic snapshot taken on 2026-09-20, before the current
campaign. Its 206 raw files are byte-for-byte identical to `measurement/results_controlled/`
and carry a SHA256 manifest. It documents the pre-audit state and is not an input to any
current result.

## Reproducing the results

Two of the three stages need only the data already in this repository. Only data collection
needs Docker.

### Offline — no Docker required

These read exclusively from `data/` and `analysis/final/` and write only inside the
repository.

```bash
python -m pip install -r requirements.txt

# Unit tests. 114 selected, 23 Docker-dependent ones deselected by the marker.
# In a fresh clone 100 pass and 14 fail; see the note below.
python -m pytest -q -m "not integration"

# Rebuild every number, table and figure the paper cites, from analysis/final/
python paper/build_all.py
```

**The 14 failures are expected in a fresh clone and are not analysis failures.** They are
all in `tests/test_campaign_runner.py`, which exercises the campaign runner's Docker
orchestration. The runner locates the benchmark stacks at `<repo parent>/DeathStarBench`,
so those tests need that checkout to exist as a sibling of the repository, and they fail
with `NotADirectoryError` when it does not. They are not marked `integration` even though
they depend on external infrastructure. The remaining 100 tests, which cover the statistics,
the metric definitions and the container-resolution logic, pass with nothing but this
repository present.

`paper/build_all.py` regenerates `paper/numbers.csv`, `paper/numbers.tex`,
`paper/numbers.json`, `paper/tables/`, `paper/figures/` and `paper/INDEX.csv`, then
verifies that every claim in `paper/CLAIMS_LEDGER.md` resolves to a real row. It fails if
any does not.

To re-run the full preregistered analysis from the campaign run records, rather than just
rebuilding the paper artifacts from its outputs:

```bash
# Rewrites analysis/final/*.csv, analysis/final/figures/ and _audit/CONFIRMATORY_ANALYSIS.md in place
python analysis/final/run_confirmatory_analysis.py
```

The supplementary checks are independent of each other and of the above:

```bash
python analysis/final/leave_one_out.py        # post-hoc leave-one-out sensitivity
python analysis/final/exact_p_supplement.py   # exact-enumeration p-values
python analysis/final/blind_recompute.py      # independent recomputation from raw spans
python paper/check_draft_ids.py               # verifies the drafting markers in paper/draft/
```

Every command in this section was executed from a fresh clone of this repository at a
different filesystem location, with no network access and nothing outside the clone present.
`paper/build_all.py` and `analysis/final/run_confirmatory_analysis.py` both reproduced their
outputs exactly: the primary correlation came out at rho = 0.785119 with a BH-adjusted p of
0.3451, and 0 of 44 confirmatory and 0 of 44 replication tests significant, identical to the
committed values. `run_confirmatory_analysis.py` takes roughly a minute; `leave_one_out.py`
and `blind_recompute.py` take several minutes each, the first because it enumerates
permutations exactly and the second because it reads all 366 span files.

### Cloning on Windows

Four tracked paths are 131 to 135 characters long, all under `_quarantine/`. Windows
applies a 260-character limit to the full path unless long-path support is enabled, so a
clone into a deeply nested directory can fail part-way with `Filename too long` and leave an
incomplete checkout. Cloning into a short path such as `C:\projects\` avoids this. To remove
the limit instead:

```bash
git config --global core.longpaths true
```

### Data collection — requires Docker

Re-running the campaign itself needs a working Docker install, roughly 8 GB of memory
available to the Docker VM, and a separate checkout of DeathStarBench (see below). This
stage is **not verified here**, because it needs the live stack:

```bash
python tools/run_campaign.py --status        # inspect the run manifest
python tools/run_campaign.py --max-runs 1    # execute a single pending run
```

The campaign reported in the paper was collected at commit `5976178` ("campaign complete:
180/180 runs, both pre-analysis gates clean").

## Environment

- **Python 3.11 or newer.** Developed and verified on 3.13.2.
- **Packages:** `pip install -r requirements.txt`. Verified with numpy 2.1.2, pandas 2.2.3,
  scipy 1.14.1, statsmodels 0.14.6, matplotlib 3.9.2, networkx 3.6.1, pytest 9.0.3.
- **Docker** is required only for data collection and for the 23 integration tests. The
  offline analysis does not use it.
- **DeathStarBench is not included in this repository** and must be cloned separately. The
  applications were built from commit `6ecb097`
  (`6ecb09706140f8730b5385c08f1386c654c3c526`). The two `docker-compose.override.yml` files
  used to pin the Jaeger version and port assignments are likewise not included, and the
  Hotel Reservation stack was reached on host port 16687 rather than the default 16686.

`lifelines` is not required. The survival models use `statsmodels`.

## Reading order

For an assessor, `paper/CLAIMS_LEDGER.md` first, then
`_audit/preregistration_versions/PREREGISTRATION_v3_LOCKED.md` for what was committed to in
advance, then `_audit/CONFIRMATORY_ANALYSIS.md` for the full analysis narrative, then
`paper/draft/` for the manuscript sections. `paper/numbers.csv` connects any number in those
documents back to the file and script that produced it.
