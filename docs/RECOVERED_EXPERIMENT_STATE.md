# Recovered Experiment State

## 1. Exact Number of Completed Runs
A total of **25 runs** were found in the `measurement/results_controlled/` directory.
- **12 runs** from September 18th (Pre-fix, failed telemetry).
- **1 validation run** for Social Network on September 19th.
- **12 pilot runs** (6 Social Network, 6 Hotel Reservation) on September 19th.

No additional runs beyond the 12-run pilot were executed while you were away.

## 2. Exact Run IDs (Timestamps)
### Social Network (`compose-post-service`)
**Pre-fix runs (Sept 18):**
- `2026-09-18T23-23-49p0530` (kill)
- `2026-09-18T23-25-13p0530` (kill)
- `2026-09-18T23-26-39p0530` (latency)
- `2026-09-18T23-28-05p0530` (latency)
- `2026-09-18T23-29-27p0530` (cpu)
- `2026-09-18T23-30-48p0530` (cpu)

**Validation run (Sept 19):**
- `2026-09-19T00-04-03p0530` (kill) - *This is your last known validation.*

**Pilot runs (Sept 19):**
- `2026-09-19T00-15-49p0530` (kill)
- `2026-09-19T00-17-25p0530` (kill)
- `2026-09-19T00-18-57p0530` (latency)
- `2026-09-19T00-20-26p0530` (latency)
- `2026-09-19T00-22-08p0530` (cpu)
- `2026-09-19T00-24-04p0530` (cpu)

### Hotel Reservation (`reservation`)
**Pre-fix runs (Sept 18):**
- `2026-09-18T23-33-32p0530` (kill)
- `2026-09-18T23-35-51p0530` (kill)
- `2026-09-18T23-37-08p0530` (latency)
- `2026-09-18T23-38-24p0530` (latency)
- `2026-09-18T23-39-40p0530` (cpu)
- `2026-09-18T23-40-57p0530` (cpu)

**Pilot runs (Sept 19):**
- `2026-09-19T00-26-50p0530` (kill)
- `2026-09-19T00-29-12p0530` (kill)
- `2026-09-19T00-30-30p0530` (latency)
- `2026-09-19T00-31-48p0530` (latency)
- `2026-09-19T00-33-08p0530` (cpu)
- `2026-09-19T00-34-26p0530` (cpu)

## 3. Architecture Distribution
- **Social Network:** 13 total runs (6 pre-fix + 1 validation + 6 pilot)
- **Hotel Reservation:** 12 total runs (6 pre-fix + 6 pilot)

## 4. Service Distribution
- `compose-post-service` (Social Network): 13 runs
- `reservation` (Hotel Reservation): 12 runs

## 5. Fault Distribution
- **kill:** 9 runs total (4 pre-fix, 1 validation, 4 pilot)
- **latency:** 8 runs total (4 pre-fix, 4 pilot)
- **cpu:** 8 runs total (4 pre-fix, 4 pilot)

## 6. Successful Runs (Data Integrity Valid)
Only **5 runs** (all from Social Network's pilot/validation phase) passed full data integrity checks (non-zero baselines and fault impacts):
1. `2026-09-19T00:04:03` (Validation - SN, kill)
2. `2026-09-19T00:15:49` (Pilot - SN, kill) - *Note: Low fault impact (baseline 20.49ms, fault 21.86ms) but valid data structure.*
3. `2026-09-19T00:17:25` (Pilot - SN, kill)
4. `2026-09-19T00:18:57` (Pilot - SN, latency)
5. `2026-09-19T00:24:04` (Pilot - SN, cpu)

## 7. Failed Runs
A total of **18 runs** are classified as FAILED due to complete lack of metrics (baseline = 0.0, fault = 0.0):
- All 12 pre-fix runs from Sept 18th (6 SN, 6 HR).
- All 6 pilot runs for Hotel Reservation from Sept 19th. It appears the telemetry fix only successfully captured data for Social Network.

## 8. Partial Runs
- `2026-09-19T00:20:26` (Pilot - SN, latency): Baseline was captured (`20.49ms`), but the fault value was `0.0ms` and blast radius was 0.
- `2026-09-19T00:22:08` (Pilot - SN, cpu): Baseline was captured (`26.63ms`), but fault value actually decreased (`18.91ms`), with blast radius 0.

## 9. Missing Runs
- **0 missing runs** for the intended pilot matrix. The script successfully iterated through all 12 expected jobs before exiting.

## 10. Last Completed Run Timestamp
- **2026-09-19T00:34:26+0530** (Hotel Reservation, cpu, rep 2)

## 11. Current Docker State
The Docker daemon is currently inaccessible or stopped (API connection failed via `docker ps`). No containers were found running. 

## 12. Current Workload State
The Python process (`fault_runner.py`), `locust`, and `wrk2` are **not running**. The pipeline stopped cleanly upon finishing the pilot loop.

## 13. Safety of Existing Results
**Yes, it is safe to preserve the existing results.** 
No cleanup processes are active, and the CSVs and JSON files contain valid historic records that should not be deleted. However, due to the failed metrics in Hotel Reservation, those rows are unusable for analysis and will need to be re-run after diagnosing the HR telemetry issue.

## 14. Remaining Runs Required
To complete a fully valid 12-run pilot with proper telemetry:
- **Social Network:** 1 run needs to be repeated (the partial latency run with 0.0 fault metric).
- **Hotel Reservation:** All 6 runs need to be repeated, as they all failed data integrity checks (0.0 metrics).

## 15. Validation of the Telemetry Fix
The modified `fault_runner.py` is still present and intact. It correctly evaluates `--load-mode wrk2` and initiates the `dsb-wrk2` workload container via Docker as requested. However, it seems this fix only resolved metric collection for Social Network and did not work for Hotel Reservation (which may need a different endpoint, load script, or Jaeger configuration).
