# Phase 4 Recovery After System Crash

## 1. Experiment State Before Crash (Filesystem Reconstruction)
The current controlled experiment (Phase 4) is partially complete. According to the `run_manifest.csv` and the timestamped artifacts in `measurement/results_controlled/`, the experiment was interrupted cleanly after the completion of the `user-timeline-service` matrix cells. No active or partial run logs were detected for the subsequent run, meaning the system crashed or halted between completing the last successful run and starting the next one.

## 2. Manifest Counts
Based on a direct audit of `measurement/results_controlled/run_manifest.csv`:
- **Total Planned Runs**: 171
- **VALID Runs**: 96
- **INVALID Runs**: 3
- **FAILED_INFRASTRUCTURE Runs**: 0
- **INCOMPLETE Runs**: 72

## 3. Completed Run IDs
A total of 99 runs completed execution. The completed services in the `socialnetwork` architecture are:
- `nginx-web-server` (9 runs)
- `home-timeline-service` (9 runs)
- `text-service` (9 runs)
- `user-mention-service` (9 runs)
- `url-shorten-service` (9 runs)
- `media-service` (9 runs)
- `unique-id-service` (9 runs)
- `post-storage-service` (9 runs)
- `social-graph-service` (9 runs)
- `user-service` (9 runs)
- `user-timeline-service` (9 runs)

## 4. Failed/Incomplete Run IDs
- **INVALID (Failed Data Collection)**: 3 runs (`socialnetwork_user-timeline-service_kill_rep01`, `rep02`, `rep03`). These runs are marked `INVALID` with the note "missing experiment_log.csv or missing row".
- **INCOMPLETE (Not Yet Executed)**: 72 runs. This includes all 9 runs for `socialnetwork_compose-post-service`, and all 63 runs for the entire `hotelreservation` architecture.

## 5. Last Known Run
The last successfully completed and logged run is:
- **Run ID**: `socialnetwork_user-timeline-service_cpu_rep03`
- **End Time**: `2026-09-19T23:32:57`

## 6. Remaining Matrix Cells
The remaining 72 runs to execute are:
- `socialnetwork`: `compose-post-service` (all 3 faults, 3 reps = 9 runs)
- `hotelreservation`: All 7 services (`frontend`, `search`, `reservation`, `rate`, `geo`, `profile`, `recommendation`) across all 3 faults and 3 reps = 63 runs.

## 7. Partial-Run Artifacts
There is **no evidence** of partial artifacts from an interrupted run. The `experiment_log.csv` file cleanly ends at the last known run (`user-timeline-service_cpu_rep03`). While there are JSON files in the `socialnetwork` directory for `compose-post-service`, their timestamps are from `2026-09-18` and early `2026-09-19` (prior to the Phase 4 start time of `16:22:03`), indicating they are artifacts from earlier testing phases, not a crashed Phase 4 run. 

## 8. Current Docker/WSL State
- **WSL Status**: Accessible, but distros are stopped. (`wsl -l -v` shows `Ubuntu` and `docker-desktop` in a `Stopped` state).
- **Docker Status**: Not running. Connection to the Docker API failed (`docker ps` returned `failed to connect to the docker API`).

## 9. Exact Recommended Resume Point
The experiment should resume from the first INCOMPLETE run:
**Run ID**: `socialnetwork_compose-post-service_kill_rep01`

---

### RECOVERY_STATUS:
REQUIRES_INTERVENTION

*(Reason: The Docker daemon and WSL distros are currently stopped and must be manually restarted before the experiment can resume from the recommended point).*
