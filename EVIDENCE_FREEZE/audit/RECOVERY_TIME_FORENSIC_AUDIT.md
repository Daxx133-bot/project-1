# Recovery Time Forensic Audit

This document traces the exact physical meaning and computational logic behind the `recovery_time_s` metric.

## Code Provenance
**Source Script:** `implementation/fault_runner.py` (Lines 111-140)
**Function:** `restore_service(service, fault_type)`

## Exact Logic & Timestamps
- **Start Timestamp:** Measured at the very beginning of the `restore_service` function (`start_time = time.time()`).
- **Fault Timestamp:** N/A for this metric. The measurement starts *after* the physical fault period (30s or 60s) has concluded and the restoration process begins.
- **Recovery Condition:** The script executes a bash command: `docker inspect -f '{{.State.Running}}' <container_name>`. The service is considered "recovered" when this command returns exactly `"true"`.
- **Polling Interval:** `time.sleep(2)` (2 seconds).
- **Timeout Limit:** `time.time() - start_time > 60` (60 seconds).
- **Returned Value on Timeout:** The script returns exactly `60.0`.
- **Returned Value on Command Failure:** The `subprocess.run` blocks inside a `try/except` loop. If the Docker command fails, it catches the exception and sleeps for 2 seconds.
- **Rounding:** `round(time.time() - start_time, 2)`.
- **Units:** Seconds.

## Modality-Specific Behaviors

1. **Kill Faults:** 
   - The container is physically stopped. 
   - The `docker inspect` command correctly identifies `false` initially.
   - Wait loops continue until the infrastructure restart policy brings the container back online. 
   - Result: Values typically between 10s - 60s, heavily right-censored at exactly 60.0s (timeout).

2. **CPU and Latency Faults:** 
   - These faults degrade the container's performance *internally* using `stress-ng` or `tc`.
   - The container itself never physically exits; its Docker `.State.Running` property remains `true` the entire time.
   - Result: The very first `docker inspect` call immediately returns `"true"`. The `recovery_time_s` strictly measures the execution overhead of a single bash `docker inspect` call (between `0.01s` and `0.05s`, or ~`2.0s` if the exact microsecond polling happens to trip an initial edge case).
   - This metric **does not** measure telemetry stabilization or application-level recovery for these faults.
