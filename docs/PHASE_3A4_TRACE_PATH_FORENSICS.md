# PHASE 3A.4: Trace Path Forensics

## 1. Trace Path Forensics
An analysis of the Jaeger traces confirms that the Hotel Reservation telemetry pipeline is operational, but the traffic it is measuring is completely invalid.

- **Observed Trace**: 99.4% of traces recorded in Jaeger during the experiment consist of a single isolated span: `HTTP GET /` with a duration of ~0.2ms to 0.5ms.
- **Trace Topology**: These `GET /` traces have **zero downstream hops**. They do not contact `search`, `geo`, `profile`, or `reservation`. 
- **Valid Traces**: The only valid, fully distributed traces (e.g., `frontend` -> `search.Search/Nearby` -> `geo.Geo/Nearby`) recorded in Jaeger perfectly correspond to the single API requests sent by `health_check_hotel.py` immediately prior to the workload phase.

## 2. Compare Success vs Failure Traces
Because 100% of the `wrk2` traffic is recorded as `HTTP GET /` (which has no downstream calls), **none of the faults appear in the traces**. 
- A `kill` or `latency` fault on `reservation` cannot impact a request that only asks the frontend for the static `index.html` file.
- As a result, both baseline P95 and fault P95 are virtually identical (~0.5ms) across all experiments, and the blast radius is always 0.

## 3. Verify Workload Behavior
The `wrk2` Lua workload generator (`mixed-workload_type_1.lua`) contains a severe string-concatenation bug that breaks the HTTP Request-Line.

**The Bug:**
```lua
local method = "GET"
local path = url .. "/hotels?inDate=" .. in_date_str ...
return wrk.format(method, path, headers, nil)
```
Because `url` is defined as `http://localhost:5000`, the `path` variable evaluates to the absolute URL: `http://localhost:5000/hotels?...`
When `wrk.format` compiles the request, it creates:
`GET http://localhost:5000/hotels?... HTTP/1.1`

**Answer to Objective:** No. The current workload does **not** exercise the distributed reservation path. It is sending a malformed Request-Line.

## 4. Verify Frontend Routing
When the Go HTTP server (`frontend.go`) receives the request `GET http://localhost:5000/hotels...`, the `ServeMux` router attempts to match the path. Since the path is not exactly `/hotels` (it includes the absolute URI prefix), it falls back to the default handler:
```go
mux.Handle("/", http.FileServer(http.FS(staticContent)))
```
Consequently, the frontend immediately returns HTTP 200 with static content (in 0.5ms), completely bypassing the microservice backend.

## 5. Verify Jaeger Configuration
The Jaeger configuration is perfectly sound. Port `16687` correctly collects traces, and when a valid request is actually routed to the backend (e.g., via the Python health check using the `requests` library), Jaeger captures the full trace topology perfectly.

## 6. Verify Error Propagation
The zero error rate in the metrics is a consequence of two issues:
1. `wrk2` traffic never reaches a fault, so it never triggers an error (always receives HTTP 200 for the static file).
2. When the health check triggers an error (e.g., during a kill fault), the Go `frontend` returns HTTP 500 but **does not tag the root span with `error=true`**. Jaeger relies on this tag to calculate error rates.

## 7. Verify Latency Fault
The latency fault was correctly injected into `hotelreservation-reservation-1` via Pumba. However, because the `wrk2` workload was exclusively hitting the static `/` route, the fault was entirely bypassed, leading to an unchanged P95 latency.

## 8. Verify CPU Fault
The CPU stress was correctly applied via Pumba, but identical to the latency fault, it was applied to a service that received precisely zero experiment traffic.

## 9. Root-Cause Classification
1. **Workload/pathology**: The Lua script generates an absolute URI instead of a relative path.
2. **Application routing**: Go's `ServeMux` treats the absolute URI as unmatched and serves the root static handler `/`.

## 10. Minimal Fix
- **File:** `scratch/DeathStarBench/hotelReservation/wrk2/scripts/hotel-reservation/mixed-workload_type_1.lua`
- **Exact Problem:** The `path` variable concatenates the `url` prefix, breaking the `wrk2` Request-Line.
- **Proposed Change:** Remove `url .. ` from the path definitions in `search_hotel`, `recommend`, `reserve`, and `user_login`.
  - Example: `local path = "/hotels?inDate=" .. in_date_str ...`
- **Why it solves the issue:** `wrk.format` will now receive a valid relative path (`/hotels?...`), generating a standard HTTP request (`GET /hotels?... HTTP/1.1`), which Go's `ServeMux` will correctly route to the microservice backend handlers.

*(Note: There is a secondary issue in the Lua script where `reserve()` references undefined `lat` and `lon` variables, resulting in `lat=nil` which causes a panic in the reservation service. A minimal fix should define these variables locally in `reserve()` as they are in other functions).*

## 11. GO/NO-GO For a Single Validation Run

**DIAGNOSIS:**
The `wrk2` Lua script sends absolute URLs (`http://localhost...`) instead of relative paths, causing the Go frontend to fallback to the root static file server (`GET /`). 100% of the load generator traffic bypasses the microservices entirely, resulting in flat 0.5ms latencies and zero fault impact.

**EVIDENCE:**
1. 99.4% of Jaeger traces are `HTTP GET /` with 0.2ms durations.
2. Zero downstream service spans exist in the `wrk2` traces.
3. Lua script assigns `path = url .. "/hotels..."` which breaks `wrk.format`.
4. Go's `ServeMux` routes unmatched absolute URIs to the default `http.FileServer` handler.

**MINIMAL FIX:**
Remove `url .. ` from all `path` assignments in `mixed-workload_type_1.lua`, and define `lat` and `lon` in the `reserve()` function to prevent downstream panics.

**VALIDATION:**
Run a single pilot run (`reservation` + `latency`) after applying the Lua fix to verify that traces now contain downstream hops and that the fault significantly increases P95 latency.

**RECOMMENDATION:**
- FIX_AND_VALIDATE
