"""
recovery_probe.py — measure application recovery, not container restart.

Two distinct quantities are measured here. Keeping them separate is the point of this
module; conflating them is what produced the defect documented in
`_audit/AUDIT_REPORT.md` §C.

1. `container_restart_time_s` — elapsed time until the target container reports
   `State.Running == true`. This is the *old* measurement, preserved under its honest
   name. It is a legitimate infrastructure metric. It is NOT application recovery, and
   for latency/CPU faults (which never stop the container) it returns almost immediately
   and is meaningless.

2. `recovery_time_s` — elapsed time from fault injection until delta-p95, delta-p99,
   delta-error-rate AND downstream-affected-count have *simultaneously* returned to
   within a tolerance of their pre-fault baseline, and stayed there for a confirmation
   period. This is the quantity the manuscript's definition describes.

Censoring
---------
If recovery is not observed within `max_wait_s`, the result is **censored**: `recovered`
is False and `recovery_time_s` is None. It is NOT filled with `max_wait_s`, and it is NOT
filled with anything else. A censored observation means "did not recover within the
window" and must be handled with survival-analysis methods (Kaplan-Meier, Cox, or a
log-rank test), never averaged in as if it were a measured duration.

The old implementation's failure mode was exactly this: on timeout it returned the
elapsed wall time, producing values like 61.07 s that look like measurements but are the
`max_wait = 60` ceiling. Every such value in `data/raw/` is an artefact.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, asdict, field
from typing import Any, Callable, Optional

from measurement.metrics_collector import (
    collect_baseline_metrics,
    compute_error_rate,
    compute_latency_percentiles,
    get_traces_in_window,
)

# ── Defaults ──────────────────────────────────────────────────────────────────
# Chosen so a real recovery is never artificially truncated: the old 60 s cap was
# shorter than several genuine recoveries and silently censored them as measurements.
DEFAULT_POLL_INTERVAL_S = 3.0
DEFAULT_MAX_WAIT_S = 180.0
DEFAULT_TOLERANCE = 0.10          # "within 10% of baseline"
DEFAULT_CONFIRM_S = 6.0           # must hold for this long before declaring recovery
DEFAULT_PROBE_WINDOW_S = 10.0     # width of each trace query window


@dataclass
class RecoveryResult:
    """Outcome of one recovery probe.

    Attributes:
        recovered:        True only if every indicator returned within tolerance and
                          held for `confirm_seconds`.
        recovery_time_s:  Seconds from fault injection to the START of the sustained
                          in-tolerance period. None when censored.
        censored:         True when the probe hit `max_wait_s` without recovery.
                          Feed these to survival analysis; do not average them.
        observed_until_s: How long the probe actually watched. For censored
                          observations this is the survival-analysis follow-up time.
        first_ok_at_s:    When all indicators first fell inside tolerance (may be
                          earlier than recovery_time_s if it did not then hold).
        blocking_indicator: Which indicator was still out of tolerance at the end.
                          Diagnostic for censored runs.
        samples:          Per-poll record, for auditing and for plotting the recovery curve.
    """

    recovered: bool
    recovery_time_s: Optional[float]
    censored: bool
    observed_until_s: float
    first_ok_at_s: Optional[float] = None
    blocking_indicator: Optional[str] = None
    tolerance: float = DEFAULT_TOLERANCE
    confirm_seconds: float = DEFAULT_CONFIRM_S
    max_wait_s: float = DEFAULT_MAX_WAIT_S
    samples: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _within_tolerance(current: float, baseline: float, tolerance: float) -> bool:
    """Has `current` returned to within `tolerance` of `baseline`?

    Recovery is one-sided: being *faster* or *less errored* than baseline is recovered.
    Only exceeding the baseline band counts as still-degraded.

    A zero baseline cannot support a relative band, so we fall back to requiring the
    current value to be zero as well. This is strict by design: with a zero baseline we
    have no scale, and guessing one would be fabricating a threshold.
    """
    if baseline <= 0.0:
        return current <= 0.0
    return current <= baseline * (1.0 + tolerance)


def probe_recovery(
    jaeger_url: str,
    gateway_service: str,
    all_services: list[str],
    baseline: dict[str, dict[str, float]],
    fault_start_us: int,
    *,
    poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
    max_wait_s: float = DEFAULT_MAX_WAIT_S,
    tolerance: float = DEFAULT_TOLERANCE,
    confirm_seconds: float = DEFAULT_CONFIRM_S,
    probe_window_s: float = DEFAULT_PROBE_WINDOW_S,
    degradation_factor: float = 2.0,
    error_rate_abs_threshold: float = 0.05,
    now_fn: Callable[[], float] = time.time,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> RecoveryResult:
    """Poll until all four indicators return to within `tolerance` of baseline.

    Indicators, all relative to the pre-fault baseline of the same service:
      - p95 of the gateway service
      - p99 of the gateway service
      - error rate of the gateway service
      - downstream-affected count across `all_services` (recovered == 0 affected)

    Args:
        jaeger_url: Jaeger query base URL.
        gateway_service: Service whose tail latency defines end-to-end impact
            ("nginx-web-server" for Social Network, "frontend" for Hotel Reservation).
        all_services: Every service to consider for the downstream-affected count.
        baseline: Output of `collect_baseline_metrics` taken BEFORE fault injection.
        fault_start_us: Fault injection instant, microseconds since epoch. Recovery time
            is measured from here, per the manuscript's definition.
        now_fn, sleep_fn: Injected for testing. Do not override in production.

    Returns:
        RecoveryResult. Check `.censored` before using `.recovery_time_s`, which is None
        whenever `.censored` is True.
    """
    gw_baseline = baseline.get(gateway_service, {})
    base_p95 = float(gw_baseline.get("p95_ms", 0.0))
    base_p99 = float(gw_baseline.get("p99_ms", 0.0))
    base_err = float(gw_baseline.get("error_rate", 0.0))

    fault_start_s = fault_start_us / 1_000_000.0
    deadline = fault_start_s + max_wait_s

    samples: list[dict[str, Any]] = []
    ok_since: Optional[float] = None
    first_ok_at: Optional[float] = None
    last_blocking: Optional[str] = None

    while True:
        now = now_fn()
        if now >= deadline:
            break

        window_end_us = int(now * 1_000_000)
        window_start_us = int((now - probe_window_s) * 1_000_000)
        # Never look back before the fault: pre-fault traces would make a still-degraded
        # system appear recovered.
        window_start_us = max(window_start_us, fault_start_us)

        traces = get_traces_in_window(
            jaeger_url, gateway_service, window_start_us, window_end_us
        )
        lat = compute_latency_percentiles(traces)
        err = compute_error_rate(traces)
        trace_count = lat["count"]

        affected = _count_affected(
            jaeger_url, all_services, baseline, window_start_us, window_end_us,
            degradation_factor, error_rate_abs_threshold,
        )

        checks = {
            "p95": _within_tolerance(lat["p95_ms"], base_p95, tolerance),
            "p99": _within_tolerance(lat["p99_ms"], base_p99, tolerance),
            "error_rate": _within_tolerance(err, base_err, tolerance),
            "downstream_affected": affected == 0,
        }

        # No traces at all means we cannot assert recovery. Treat it as not-recovered
        # rather than as zero latency -- that conflation is the bug described in
        # _audit/TELEMETRY_DIAGNOSIS.md section 2(c2).
        have_signal = trace_count > 0
        all_ok = have_signal and all(checks.values())

        elapsed = now - fault_start_s
        samples.append({
            "t_s": round(elapsed, 2),
            "trace_count": trace_count,
            "p95_ms": lat["p95_ms"], "p99_ms": lat["p99_ms"],
            "error_rate": err, "downstream_affected": affected,
            "all_ok": all_ok, "have_signal": have_signal,
        })

        if all_ok:
            if ok_since is None:
                ok_since = now
                if first_ok_at is None:
                    first_ok_at = elapsed
            if now - ok_since >= confirm_seconds:
                return RecoveryResult(
                    recovered=True,
                    recovery_time_s=round(ok_since - fault_start_s, 2),
                    censored=False,
                    observed_until_s=round(elapsed, 2),
                    first_ok_at_s=round(first_ok_at, 2) if first_ok_at is not None else None,
                    blocking_indicator=None,
                    tolerance=tolerance, confirm_seconds=confirm_seconds,
                    max_wait_s=max_wait_s, samples=samples,
                )
        else:
            ok_since = None
            if not have_signal:
                last_blocking = "no_traces"
            else:
                last_blocking = next(k for k, v in checks.items() if not v)

        sleep_fn(poll_interval_s)

    # Censored: watched the full window and never saw a sustained return to baseline.
    # recovery_time_s stays None on purpose -- see module docstring.
    return RecoveryResult(
        recovered=False,
        recovery_time_s=None,
        censored=True,
        observed_until_s=round(now_fn() - fault_start_s, 2),
        first_ok_at_s=round(first_ok_at, 2) if first_ok_at is not None else None,
        blocking_indicator=last_blocking,
        tolerance=tolerance, confirm_seconds=confirm_seconds,
        max_wait_s=max_wait_s, samples=samples,
    )


def _count_affected(
    jaeger_url: str,
    all_services: list[str],
    baseline: dict[str, dict[str, float]],
    window_start_us: int,
    window_end_us: int,
    degradation_factor: float,
    error_rate_abs_threshold: float,
) -> int:
    """Number of services still degraded in this window, same rule as compute_blast_radius."""
    affected = 0
    for service in all_services:
        if "jaeger" in service.lower() or "mongo" in service.lower():
            continue
        base = baseline.get(service, {})
        base_p95 = float(base.get("p95_ms", 0.0))
        base_err = float(base.get("error_rate", 0.0))

        traces = get_traces_in_window(jaeger_url, service, window_start_us, window_end_us)
        if not traces:
            continue
        lat = compute_latency_percentiles(traces)
        if base_p95 > 0 and lat["p95_ms"] > degradation_factor * base_p95:
            affected += 1
            continue
        if compute_error_rate(traces) > base_err + error_rate_abs_threshold:
            affected += 1
    return affected


# ── The old measurement, preserved under its honest name ──────────────────────

def container_restart_time_s(
    container_name: str,
    docker_exe: str,
    *,
    max_wait_s: float = 60.0,
    poll_interval_s: float = 2.0,
    now_fn: Callable[[], float] = time.time,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Seconds until the container reports State.Running == true.

    This is what `fault_runner.restore_service()` has always measured. It is a real and
    useful infrastructure metric -- it is simply not application recovery, and it must
    never again be written to a column named `recovery_time_s`.

    Unlike the original, this returns an explicit `censored` flag instead of silently
    returning the elapsed time on timeout. The original's timeout return is the origin of
    the 61.07 s figure in the manuscript.

    Returns:
        {"container_restart_time_s": float | None, "censored": bool,
         "observed_until_s": float}
    """
    start = now_fn()
    deadline = start + max_wait_s

    while now_fn() < deadline:
        try:
            result = subprocess.run(
                [docker_exe, "inspect", "--format", "{{.State.Running}}", container_name],
                capture_output=True, text=True, check=True,
            )
            if "true" in result.stdout.lower():
                return {
                    "container_restart_time_s": round(now_fn() - start, 2),
                    "censored": False,
                    "observed_until_s": round(now_fn() - start, 2),
                }
        except subprocess.CalledProcessError:
            pass
        sleep_fn(poll_interval_s)

    return {
        "container_restart_time_s": None,
        "censored": True,
        "observed_until_s": round(now_fn() - start, 2),
    }
