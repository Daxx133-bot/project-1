"""Unit tests for measurement/recovery_probe.py.

These use a fake clock and a scripted fake Jaeger. No containers, no network, no
randomness -- the sequences below are hand-written fixtures, not synthetic measurements.
"""

from __future__ import annotations

import pytest

from measurement import recovery_probe as rp


class FakeClock:
    def __init__(self, start: float = 1_000_000.0):
        self.t = start

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


def make_traces(duration_ms: float, n: int = 20, error: bool = False):
    """Build a trace list whose root spans all have the given duration."""
    out = []
    for i in range(n):
        tags = [{"key": "http.status_code", "type": "int64", "value": 500}] if error else []
        out.append({
            "traceID": f"t{i}",
            "spans": [{
                "spanID": f"s{i}", "operationName": "op", "references": [],
                "startTime": 0, "duration": int(duration_ms * 1000), "tags": tags,
            }],
            "processes": {},
        })
    return out


@pytest.fixture
def baseline():
    return {
        "gw": {"p95_ms": 100.0, "p99_ms": 150.0, "error_rate": 0.0},
        "svc_a": {"p95_ms": 50.0, "error_rate": 0.0},
    }


def install_fake_jaeger(monkeypatch, gateway_sequence, downstream_sequence=None):
    """Serve a scripted response per poll. Index advances on each gateway query."""
    state = {"i": 0}
    downstream_sequence = downstream_sequence or []

    def fake_get_traces(jaeger_url, service, start_us, end_us, limit=500):
        if service == "gw":
            idx = min(state["i"], len(gateway_sequence) - 1)
            state["i"] += 1
            return gateway_sequence[idx]
        # downstream service
        if not downstream_sequence:
            return []
        idx = min(max(state["i"] - 1, 0), len(downstream_sequence) - 1)
        return downstream_sequence[idx]

    monkeypatch.setattr(rp, "get_traces_in_window", fake_get_traces)
    return state


def test_recovers_when_all_indicators_return_and_hold(monkeypatch, baseline):
    clock = FakeClock()
    # degraded, degraded, then recovered and holding
    seq = [make_traces(900.0), make_traces(800.0)] + [make_traces(100.0)] * 10
    install_fake_jaeger(monkeypatch, seq)

    res = rp.probe_recovery(
        "http://jaeger", "gw", ["svc_a"], baseline,
        fault_start_us=int(clock.t * 1_000_000),
        poll_interval_s=3.0, max_wait_s=180.0, confirm_seconds=6.0,
        now_fn=clock.now, sleep_fn=clock.sleep,
    )

    assert res.recovered is True
    assert res.censored is False
    # polls at t=0 (bad), t=3 (bad), t=6 (first ok) -> confirmed at t=12
    assert res.recovery_time_s == pytest.approx(6.0)
    assert res.first_ok_at_s == pytest.approx(6.0)
    assert res.blocking_indicator is None


def test_censored_when_never_recovers(monkeypatch, baseline):
    clock = FakeClock()
    install_fake_jaeger(monkeypatch, [make_traces(5000.0)])

    res = rp.probe_recovery(
        "http://jaeger", "gw", ["svc_a"], baseline,
        fault_start_us=int(clock.t * 1_000_000),
        poll_interval_s=3.0, max_wait_s=30.0,
        now_fn=clock.now, sleep_fn=clock.sleep,
    )

    assert res.censored is True
    assert res.recovered is False
    # The whole point: NOT filled with max_wait_s or any other number.
    assert res.recovery_time_s is None
    assert res.observed_until_s >= 30.0
    assert res.blocking_indicator == "p95"


def test_transient_dip_does_not_count_as_recovery(monkeypatch, baseline):
    """One good poll surrounded by bad ones must not be reported as recovery."""
    clock = FakeClock()
    seq = [
        make_traces(900.0),   # t=0  bad
        make_traces(100.0),   # t=3  ok  (transient)
        make_traces(900.0),   # t=6  bad again
        make_traces(900.0),   # t=9  bad
    ]
    install_fake_jaeger(monkeypatch, seq)

    res = rp.probe_recovery(
        "http://jaeger", "gw", ["svc_a"], baseline,
        fault_start_us=int(clock.t * 1_000_000),
        poll_interval_s=3.0, max_wait_s=12.0, confirm_seconds=6.0,
        now_fn=clock.now, sleep_fn=clock.sleep,
    )

    assert res.recovered is False
    assert res.censored is True
    assert res.recovery_time_s is None
    # It did briefly touch baseline, and we record that separately.
    assert res.first_ok_at_s == pytest.approx(3.0)


def test_no_traces_is_not_treated_as_recovered(monkeypatch, baseline):
    """Empty trace list must never read as 'zero latency, therefore recovered'."""
    clock = FakeClock()
    install_fake_jaeger(monkeypatch, [[]])

    res = rp.probe_recovery(
        "http://jaeger", "gw", ["svc_a"], baseline,
        fault_start_us=int(clock.t * 1_000_000),
        poll_interval_s=3.0, max_wait_s=15.0,
        now_fn=clock.now, sleep_fn=clock.sleep,
    )

    assert res.recovered is False
    assert res.censored is True
    assert res.blocking_indicator == "no_traces"


def test_error_rate_blocks_recovery_even_when_latency_is_fine(monkeypatch, baseline):
    clock = FakeClock()
    install_fake_jaeger(monkeypatch, [make_traces(100.0, error=True)])

    res = rp.probe_recovery(
        "http://jaeger", "gw", ["svc_a"], baseline,
        fault_start_us=int(clock.t * 1_000_000),
        poll_interval_s=3.0, max_wait_s=12.0,
        now_fn=clock.now, sleep_fn=clock.sleep,
    )

    assert res.recovered is False
    assert res.blocking_indicator == "error_rate"


def test_downstream_affected_blocks_recovery(monkeypatch, baseline):
    """Gateway healthy but a downstream service still degraded -> not recovered."""
    clock = FakeClock()
    install_fake_jaeger(
        monkeypatch,
        gateway_sequence=[make_traces(100.0)],
        downstream_sequence=[make_traces(500.0)],   # svc_a baseline p95 is 50 -> 10x
    )

    res = rp.probe_recovery(
        "http://jaeger", "gw", ["svc_a"], baseline,
        fault_start_us=int(clock.t * 1_000_000),
        poll_interval_s=3.0, max_wait_s=12.0,
        now_fn=clock.now, sleep_fn=clock.sleep,
    )

    assert res.recovered is False
    assert res.blocking_indicator == "downstream_affected"


def test_probe_window_never_reaches_back_before_the_fault(monkeypatch, baseline):
    """Pre-fault traces must not leak into the recovery window."""
    clock = FakeClock()
    seen = []

    def fake_get_traces(jaeger_url, service, start_us, end_us, limit=500):
        seen.append(start_us)
        return make_traces(900.0)

    monkeypatch.setattr(rp, "get_traces_in_window", fake_get_traces)
    fault_start_us = int(clock.t * 1_000_000)

    rp.probe_recovery(
        "http://jaeger", "gw", [], baseline, fault_start_us=fault_start_us,
        poll_interval_s=3.0, max_wait_s=9.0, probe_window_s=30.0,
        now_fn=clock.now, sleep_fn=clock.sleep,
    )

    assert seen, "probe made no queries"
    assert all(s >= fault_start_us for s in seen)


def test_within_tolerance_is_one_sided():
    # faster than baseline counts as recovered
    assert rp._within_tolerance(50.0, 100.0, 0.10) is True
    # inside the +10% band
    assert rp._within_tolerance(109.0, 100.0, 0.10) is True
    # outside it
    assert rp._within_tolerance(111.0, 100.0, 0.10) is False


def test_zero_baseline_requires_zero_current():
    """With no baseline scale we refuse to invent a threshold."""
    assert rp._within_tolerance(0.0, 0.0, 0.10) is True
    assert rp._within_tolerance(0.1, 0.0, 0.10) is False


def test_container_restart_time_censors_instead_of_returning_the_cap(monkeypatch):
    """The old function returned elapsed time on timeout -- the origin of 61.07 s."""
    clock = FakeClock()

    class Result:
        stdout = "false"

    monkeypatch.setattr(rp.subprocess, "run", lambda *a, **k: Result())

    out = rp.container_restart_time_s(
        "c1", "docker", max_wait_s=60.0, poll_interval_s=2.0,
        now_fn=clock.now, sleep_fn=clock.sleep,
    )

    assert out["censored"] is True
    assert out["container_restart_time_s"] is None
    assert out["observed_until_s"] >= 60.0


def test_container_restart_time_returns_elapsed_when_it_comes_back(monkeypatch):
    clock = FakeClock()
    calls = {"n": 0}

    class Result:
        def __init__(self, s):
            self.stdout = s

    def fake_run(*a, **k):
        calls["n"] += 1
        return Result("true" if calls["n"] > 2 else "false")

    monkeypatch.setattr(rp.subprocess, "run", fake_run)

    out = rp.container_restart_time_s(
        "c1", "docker", max_wait_s=60.0, poll_interval_s=2.0,
        now_fn=clock.now, sleep_fn=clock.sleep,
    )

    assert out["censored"] is False
    assert out["container_restart_time_s"] == pytest.approx(4.0)
