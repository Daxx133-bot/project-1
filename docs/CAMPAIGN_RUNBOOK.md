# Campaign runbook

For the 180-run confirmatory campaign (Preregistration v3 §8–§9). Expect **8–11 hours**.

---

## Before you launch

**1. Stop the laptop sleeping.** No code fix can survive an OS-level suspend — Docker
containers freeze, Jaeger's in-memory spans are lost, and the run in flight is garbage.
On Windows 11, in an **admin** PowerShell:

```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 10
```

Closing the lid still sleeps the machine by default. Either leave it open, or set
**Settings → System → Power & battery → Lid, power and sleep button controls → When I
close the lid (plugged in) → Do nothing**.

Keep it **on AC power**. On battery, Windows applies a separate, more aggressive profile.

**2. Confirm the memory ceiling.** One stack at a time is a hard constraint
(`_audit/MEMORY_CEILING.md`). Check Docker Desktop reports **≥ 7.6 GiB** to the Linux VM.
The runner brings one stack up, runs everything for that application, then tears it down —
never both.

**3. Free disk.** Raw spans are persisted per run (v3 §9.6) to `data/spans/` as gzipped
JSON. Budget **~1–2 GB** for 180 runs. Check before starting, not at run 140.

**4. Confirm the working tree is clean and note the commit.** The preregistration's
"commit at lock" field should be filled in before any run starts.

```bash
git status --short && git rev-parse HEAD
```

**5. Build the manifest** (once):

```bash
python tools/run_campaign.py --build-manifest
python tools/run_campaign.py --dry-run     # sanity check: 180 runs, no gateways
```

---

## Launching

```bash
python tools/run_campaign.py
```

That is the whole command. It is also the **resume** command — there is no separate
resume mode.

---

## Checking progress without touching the process

Either of these is safe at any time; neither interrupts the run.

```bash
tail -n 20 data/campaign/progress.log      # one line per completed run
python tools/run_campaign.py --status      # counts, and any failed combinations
```

A progress line looks like:

```
[2026-09-25T11:04:02+00:00] DONE     socialnetwork|media-service|kill|1   A/D/U=2/0/5  err=0.154  dp95=8866.8  T_rec=48.35s | done=17 censored=1 failed=0 pending=162
```

`--status` reads the manifest, so it is accurate even if the process has died.

---

## Stopping safely

**Ctrl-C in the runner's terminal.** The in-flight run is returned to `pending`, the
current stack is brought down, and the manifest is left consistent. Exit code 130.

If the process is killed harder than that (window closed, power loss), the in-flight run
is left marked `running`. That is handled: **the next launch resets any `running` entry to
`pending`** and redoes it, because a run interrupted mid-flight has untrustworthy data.

**Do not delete the manifest** to "start clean" — that discards the record of what ran.

---

## Verifying that resume actually works — do this before the real launch

Two checks, ~2 minutes total.

**A. Bookkeeping, no Docker required.** The resume logic has direct tests:

```bash
python -m pytest tests/test_campaign_runner.py -v
```

These cover: completed runs are never repeated, a censored run is terminal, a `running`
entry left by a dead process is reset and redone, an exception marks `failed` and the
campaign continues, and Ctrl-C leaves the manifest resumable.

**B. A live rehearsal, with Docker.** Run two combinations for real, stop, and resume:

```bash
python tools/run_campaign.py --max-runs 2
python tools/run_campaign.py --status          # expect 2 terminal, 178 pending
python tools/run_campaign.py --max-runs 1      # must run run #3, not repeat #1 or #2
tail -n 5 data/campaign/progress.log
```

Confirm the third progress line names a **different** combination from the first two.
Those 3 runs are real campaign data and are kept — the rehearsal costs nothing.

---

## When something goes wrong

**A single run fails.** Nothing to do. It is logged with a full traceback under
`data/campaign/failures/`, marked `failed`, the stack is restored, and the campaign moves
on. Re-run failures at the end, which preserves balance:

```bash
python tools/run_campaign.py --retry-failed
```

**A run is `censored`.** That is **a legitimate observation, not a failure** — the service
did not recover within 180 s. It is never re-run to obtain a number (v3 §6.3). Leave it.

**The campaign stops with exit code 2.** The stack could not be recovered after escalating
through `compose up` → `compose restart` → `compose down && up`. The process stops
deliberately: continuing would produce a hundred plausible-looking but meaningless rows.
Fix the machine (usually Docker Desktop needs restarting), then re-run the same command to
resume.

**It refuses to start, citing a lock.** Another runner is live, or a previous one died
without cleaning up. Confirm nothing is running, then delete
`data/campaign/.campaign.lock`. This lock exists because a double-launch silently
corrupted 3 pilot runs (`_quarantine/QUARANTINE_LOG.md` item 9) — check properly before
overriding it.

---

## When it finishes

```bash
python tools/run_campaign.py --status
```

Expect `done + censored = 180` and `failed = 0`. If any combination is still `failed`
after `--retry-failed`, **do not analyse an unbalanced set** — report the imbalance and
decide explicitly (v3 §8: balance is mandatory).

Results land in `data/campaign/runs/`, raw spans in `data/spans/`. Commit both before
running any analysis, so the dataset is frozen at a known commit.
