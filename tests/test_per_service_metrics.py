"""Unit tests for the Q3 per-service latency/error attribution fix.

Fixtures below are hand-written trace structures, not synthetic measurements: they
exist to pin down which spans the code selects, not to stand in for data.

The scenario throughout is the one that produced the pilot's misclassification:
    frontend -> search -> geo
with `geo` slow. Under the old root-span rule, "search's p95" and "frontend's p95"
were both the end-to-end trace duration, so a slow leaf made its ancestors look
degraded -- and any unrelated service on the same trace too.
"""

from __future__ import annotations

from measurement.metrics_collector import (
    compute_error_rate,
    compute_latency_percentiles,
    select_spans,
)


def _span(span_id, svc_pid, duration_ms, kind="server", parent=None, error=False):
    tags = [{"key": "span.kind", "type": "string", "value": kind}]
    if error:
        tags.append({"key": "error", "type": "bool", "value": True})
    return {
        "spanID": span_id,
        "processID": svc_pid,
        "operationName": "op",
        "duration": int(duration_ms * 1000),
        "startTime": 0,
        "tags": tags,
        "references": ([{"refType": "CHILD_OF", "spanID": parent}] if parent else []),
    }


def slow_leaf_trace(trace_id="t", geo_ms=900.0, search_own_ms=910.0, e2e_ms=920.0):
    """frontend -> search -> geo, with geo the actual source of the latency."""
    return {
        "traceID": trace_id,
        "processes": {
            "p1": {"serviceName": "frontend"},
            "p2": {"serviceName": "search"},
            "p3": {"serviceName": "geo"},
        },
        "spans": [
            _span("a", "p1", e2e_ms),                              # frontend server (root)
            _span("b", "p1", e2e_ms - 2, kind="client", parent="a"),
            _span("c", "p2", search_own_ms, parent="b"),           # search server
            _span("d", "p2", geo_ms + 1, kind="client", parent="c"),
            _span("e", "p3", geo_ms, parent="d"),                  # geo server
        ],
    }


def test_root_span_scope_is_end_to_end_not_per_service():
    traces = [slow_leaf_trace()]
    assert compute_latency_percentiles(traces)["scope"] == "end_to_end_root"
    assert compute_latency_percentiles(traces, service="geo")["scope"] == (
        "service_server_spans:geo"
    )


def test_per_service_p95_uses_only_that_services_server_spans():
    traces = [slow_leaf_trace(geo_ms=900.0, search_own_ms=910.0, e2e_ms=920.0)]
    assert compute_latency_percentiles(traces, service="geo")["p95_ms"] == 900.0
    assert compute_latency_percentiles(traces, service="search")["p95_ms"] == 910.0
    assert compute_latency_percentiles(traces, service="frontend")["p95_ms"] == 920.0
    # The old behaviour: every service inherited the same end-to-end number.
    assert compute_latency_percentiles(traces)["p95_ms"] == 920.0


def test_client_spans_are_excluded_so_callee_latency_is_not_reattributed():
    """search emits a 901ms client span waiting on geo; that is geo's latency, not search's."""
    traces = [slow_leaf_trace(geo_ms=900.0, search_own_ms=5.0, e2e_ms=910.0)]
    spans = select_spans(traces, "search")
    assert len(spans) == 1
    assert compute_latency_percentiles(traces, service="search")["p95_ms"] == 5.0


def test_unrelated_service_on_the_same_trace_is_not_dragged_up():
    """A fast service sharing a trace with a slow one keeps its own fast p95."""
    trace = slow_leaf_trace(geo_ms=900.0)
    trace["processes"]["p4"] = {"serviceName": "rate"}
    trace["spans"].append(_span("f", "p4", 4.0, parent="b"))
    per_service = compute_latency_percentiles([trace], service="rate")
    assert per_service["p95_ms"] == 4.0
    assert compute_latency_percentiles([trace])["p95_ms"] > 900.0


def test_service_absent_from_traces_yields_zero_count_not_a_borrowed_number():
    traces = [slow_leaf_trace()]
    res = compute_latency_percentiles(traces, service="reservation")
    assert res["count"] == 0
    assert res["p95_ms"] == 0.0


def test_fails_open_to_all_spans_when_span_kind_tags_are_absent():
    trace = {
        "traceID": "t",
        "processes": {"p1": {"serviceName": "geo"}},
        "spans": [{"spanID": "a", "processID": "p1", "duration": 7000,
                   "startTime": 0, "tags": [], "references": []}],
    }
    assert compute_latency_percentiles([trace], service="geo")["p95_ms"] == 7.0


def test_error_rate_is_attributed_to_the_service_that_errored():
    trace = slow_leaf_trace()
    trace["spans"][4]["tags"].append({"key": "error", "type": "bool", "value": True})
    assert compute_error_rate([trace], service="geo") == 1.0
    assert compute_error_rate([trace], service="search") == 0.0
    # Trace-level: the whole trace counts as errored, which is the misattribution.
    assert compute_error_rate([trace]) == 1.0


def test_error_rate_denominator_is_traces_the_service_appears_in():
    with_geo = slow_leaf_trace("t1")
    with_geo["spans"][4]["tags"].append({"key": "error", "type": "bool", "value": True})
    without_geo = {
        "traceID": "t2",
        "processes": {"p1": {"serviceName": "frontend"}},
        "spans": [_span("a", "p1", 5.0)],
    }
    # geo appears in 1 of 2 traces and errored in it -> 1.0, not 0.5.
    assert compute_error_rate([with_geo, without_geo], service="geo") == 1.0
