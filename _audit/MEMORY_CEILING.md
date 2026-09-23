# Step 2 — Docker VM memory ceiling

**Date:** 2026-09-24

## Where the limit actually comes from

It is **not** a Docker Desktop setting. Docker Desktop here runs on the **WSL2 backend**,
and `~/AppData/Roaming/Docker/settings-store.json` contains no `memoryMiB`, `cpus` or
`vmType` key — those fields only exist for the Hyper-V backend.

There is **no `~/.wslconfig`**, so WSL2 applies its default: **50 % of host RAM**.
Host = 15.7 GB → VM = **8 157 077 504 bytes = 7.598 GiB**, which matches the per-container
limit every container reports.

To raise it you would create `~/.wslconfig`:

```ini
[wsl2]
memory=12GB
```

then `wsl --shutdown` and restart Docker Desktop.

## Measured: is it needed?

**No — not if one stack runs at a time.**

| Configuration | Containers | Memory | Headroom of 7.60 GiB |
|---|---:|---:|---:|
| Both stacks (as found, idle) | 40 | 2.36 GiB | 5.24 GiB |
| **SN alone** (post 4-min load) | 27 | **1.66 GiB** | **5.94 GiB** |

A single benchmark stack uses **~22 % of the ceiling**. The ceiling was never the binding
constraint on its own.

## Recommendation: leave it unchanged

Raising WSL2 to 12 GB on a 15.7 GB host leaves ~3.7 GB for Windows, the IDE and the
browser — a real risk of host swapping, which would itself perturb latency measurements
and contaminate the very numbers we are trying to collect. Given ~6 GiB of measured
headroom with one stack, that trade is not worth taking.

**If** a future run shows container OOM kills or `MemUsage` approaching the limit, revisit
it then, with the evidence.

## The actual problem was concurrency, not capacity

On daemon start, **both** stacks came up automatically (40 containers) because the DSB
compose files set `restart: always`. Hotel Reservation's Jaeger then failed to bind:

```
Error response from daemon: ... Bind for 0.0.0.0:16686 failed: port is already allocated
```

Two stacks under one ceiling, competing for CPU and for port 16686, is the condition that
plausibly contributed to the `sn_legacy` baseline p95 excursions (up to 4816 ms, versus a
299 ms maximum in the controlled batch).

## Enforced for the rest of this session

One stack at a time, verified before each phase:

| Phase | Stack up | Other stack | Containers |
|---|---|---|---|
| SN graph reconstruction | socialNetwork | stopped | 27 |
| HR graph reconstruction | hotelReservation | stopped | 24 |
| HR pilot | hotelReservation | stopped | 24 |
| SN pilot | socialNetwork | stopped | 27 |

**Operational rule for the campaign:** explicitly `docker compose stop` the idle stack
before each phase, and assert `docker ps -q | wc -l` matches the expected count. Do not
rely on the stacks staying down across a Docker Desktop restart — `restart: always` will
bring them back.

## Related finding: never `docker restart` Jaeger mid-experiment

During step 4 a `docker restart hotelreservation-jaeger-1` (intended to clear old spans)
produced a **silent total telemetry loss**: 4 842 requests completed with 0 failures, yet
Jaeger held **zero spans**. Two causes, both worth knowing:

1. The restart gave Jaeger a new container IP; the Go services had cached the old one and
   kept sending UDP spans into the void. UDP never reports an error.
2. The restart also dropped every published port binding, so the collector was
   unreachable from the host.

This reproduces the **exact zero-telemetry signature** of the `hr_sep13` batch, and is a
**third** mechanism that could have produced it, alongside the `start_load()` no-op and
the discarded `trace_count`. To clear spans safely, recreate the whole stack with
`docker compose up -d --force-recreate` so the application services re-resolve Jaeger.

This is precisely the failure the new `telemetry_ok` / `trace_count` fields are designed
to catch — and in the pilot they did.
