# Environment Status for Re-run (Step 7)

**Date:** 2026-09-23. No fault injection was run.

---

## 1. Locust — FIXED

| | |
|---|---|
| Before | Not installed. Nothing could be re-run. |
| Action | `pip install locust --break-system-packages` |
| Now | **locust 2.46.3** on Python 3.13.2 |

Both workload scripts import cleanly against it:

```
infra/_locustfile_baseline.py -> imports OK
infra/_locustfile_hotel.py    -> imports OK
```

The API they use (`HttpUser`, `@task`, `between`, `catch_response=True`) is stable across
Locust 2.x, so no version-compatibility work is needed.

---

## 2. Docker — NOW RUNNING

Docker Desktop is a **per-user install** at
`C:\Users\daksh\AppData\Local\Programs\DockerDesktop\` — not the machine-wide location,
and `com.docker.service` is not registered as a Windows service, which is why the audit
found the daemon unreachable.

Started successfully. **Server 29.8.0**, Compose v5.5.1.

### Finding: a hard memory ceiling that is lower than the host's

The Docker backend VM is limited to **7.597 GiB**, not the host's 15.7 GB. Every
container reports this as its limit. This materially sharpens the contention hypothesis
in `_audit/TELEMETRY_DIAGNOSIS.md` §2(b): the budget for a full DeathStarBench stack plus
Jaeger, MongoDB, Redis and Memcached is 7.6 GiB, not 15.7 GB.

### Finding: both stacks were running concurrently

On daemon start, **40 containers** came up — the Social Network stack had a `restart:
always` policy and resumed automatically. It held port **16686**, which caused the first
Hotel Reservation bring-up to fail:

```
Error response from daemon: ... Bind for 0.0.0.0:16686 failed: port is already allocated
```

This is direct evidence that past experiment batches may have run with **both benchmark
stacks live at once**, inside a 7.6 GiB ceiling. That is a plausible contributor to the
4816 ms baseline p95 excursions in `sn_legacy` (vs 299 ms max in the controlled batch).

**Action taken:** `docker compose stop` on the Social Network stack (stop, not `down` —
no containers or volumes were removed). Hotel Reservation was then brought up alone.

**Recommendation:** run exactly one benchmark stack at a time, and disable the
`restart: always` policy or explicitly stop the idle stack before each batch.

---

## 3. Hotel Reservation stack — UP

Brought up with the project's override, which is the configuration the experiments
assume:

```
docker compose -f ../DeathStarBench/hotelReservation/docker-compose.yml \
               -f infra/hotel-compose.override.yml \
               --project-directory ../DeathStarBench/hotelReservation up -d
```

The override matters: it pins `jaegertracing/all-in-one:1.62.0`, sets
`JAEGER_SAMPLE_RATIO=1.0` (100 % sampling), and maps Jaeger's UI to host port **16687**
so it does not collide with Social Network's 16686. Bringing HR up *without* it leaves
Jaeger unpublished and unqueryable — worth knowing, because a run started the wrong way
would produce exactly the zero-telemetry signature already seen.

24 containers running. `frontend` on `:5000`, Jaeger on `:16687`.

**`user` service confirmed present in the compose file** with its own `mongodb-user`
backing store, and it starts healthy (`hotelreservation-user-1  Up`).

Incidental note: this DSB revision (`6ecb097`) also ships `review` and `attractions`
services, which `sdg/hotel_expected_services.py` does not list. The manifest's "8
services" is itself a subset choice and should be stated as such.

---

## 4. The `user` service — cause CONFIRMED LIVE, fix VERIFIED, not yet applied

The audit inferred from logs that malformed requests were the cause. That is now
**confirmed by controlled experiment against the running stack.**

### The requests the current workload sends

```
GET /user?username=Cornell_1
    -> HTTP 400  "Please specify username and password"

POST /reservation  (JSON body, as _locustfile_hotel.py sends it)
    -> HTTP 400
```

### The same requests, corrected

```
GET /user?username=Cornell_1&password=1111111111
    -> HTTP 200

POST /reservation?inDate=..&outDate=..&hotelId=..&customerName=..
                 &username=..&password=..&number=1
    -> HTTP 200
```

### The decisive test — Jaeger service registry

```
before any traffic:            []
after 10 BUGGY   /user calls:  ['frontend', 'jaeger-all-in-one']
after 10 CORRECT /user calls:  ['frontend', 'jaeger-all-in-one', 'user']
```

The `user` service appears in Jaeger **if and only if** `password` is supplied. Trace
inspection confirms the edge exists: `frontend -> user (10 calls)`.

**Root cause, confirmed:** `services/frontend/server.go::userHandler` reads
`r.URL.Query()` and returns 400 before reaching `s.userClient.CheckUser(...)` when either
`username` or `password` is empty. No RPC is issued, so no span exists, so `user` cannot
enter the dependency graph. The same applies to `reservationHandler`, which additionally
reads **query parameters** (not a JSON body) and expects `number`, not `roomNumber`.

### Graph produced by a corrected 60-request mixed workload

```
frontend -> profile          (222 calls)
frontend -> recommendation   ( 42 calls)
frontend -> reservation      (207 calls)
frontend -> search           (180 calls)
frontend -> user             ( 63 calls)
search   -> geo              (180 calls)
search   -> rate             (180 calls)

nodes = 8   edges = 7   user present: True
```

Compared with the graph the paper used: **7 nodes / 6 edges → 8 nodes / 7 edges.**

Two notes for the record:

1. The manifest `sdg/hotel_expected_services.py` expects 8 edges, including
   `("reservation", "user")`. That edge **does not exist in this DSB revision** — the
   *frontend* calls `user` for auth; the `reservation` service does not. The manifest
   appears to be wrong, and the observed 7-edge graph is likely complete for this
   workload. This should be verified before the manifest is used as ground truth again.
2. The seeded credentials do not validate (`"Failed. Please check your username and
   password."`), so `mongodb-user` is probably unseeded. This does **not** block graph
   extraction — `CheckUser` is called either way, and `reservationHandler` proceeds to
   `MakeReservation` regardless of the auth result — but it should be fixed so the
   workload exercises realistic success paths.

### Status: NOT YET APPLIED

The workload fix is **verified but not committed**, per the instruction to stop after
step 7. It must be made in **`infra/generate_hotel_load.py`** (lines ~82–102 and
~186–193), not only in `infra/_locustfile_hotel.py` — the latter is auto-generated
("Auto-generated by generate_hotel_load.py. Do not edit manually.") and would silently
revert.

---

## 5. Readiness against the preregistration's preconditions

| # | Precondition (`PREREGISTRATION.md` §7) | Status |
|---|---|---|
| 1 | Locust installed, workload verified to generate traffic | **MET** — 2.46.3; 60 live requests produced 7 edges |
| 2 | `/user` and `/reservation` fixed; HR graph shows 8 nodes / 8 edges | **PARTIAL** — fix verified live (8 nodes / 7 edges); not yet applied to source. The 8th edge appears not to exist in this DSB revision |
| 3 | `trace_count` / `telemetry_ok` written per run | **MET** — added to `results_logger.py` |
| 4 | Social Network traces re-captured, `sdg/output/sdg.json` regenerated | **NOT MET** — SN stack currently stopped; source traces for the existing graph were overwritten and are gone |
| 5 | Pilot of 1 rep per (service × fault) with non-zero telemetry | **NOT MET** — no fault injection run this session, by instruction |

---

## 6. Current machine state

- **Docker daemon: running.**
- **Hotel Reservation: up** (24 containers, `frontend:5000`, Jaeger `:16687`).
- **Social Network: stopped** (not removed; `docker compose start` restores it).
- No fault was injected. No Pumba container was run. No experiment data was written.
- Roughly 60 HTTP requests were sent to the HR frontend for diagnosis. These produced
  traces in the HR Jaeger instance but **no file under `data/raw/` or `measurement/`**.
  If a clean trace baseline is wanted for graph extraction, restart the Jaeger container
  first to clear them.
