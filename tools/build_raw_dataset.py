"""
build_raw_dataset.py — consolidate the real fault-injection batches into data/raw/.

Copies (never moves) the four genuine experiment logs into data/raw/ as separate,
clearly-named files. Every original column is retained verbatim; one column is added:

    batch  — the batch identifier, matching the filename stem

No merging, no deduplication, no filtering, no type coercion. Which batches to combine
is an analysis-time decision, not a storage-time one.

The contaminated log (48 fabricated rows) is NOT among the inputs; it lives in
_quarantine/measurement/results/experiment_log.csv. The genuine rows that were mixed into
it are recovered here from the per-run JSON files instead, so sn_legacy.csv contains only
real runs.

Usage:
    python tools/build_raw_dataset.py [--verify-only]
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

# Canonical column order used by fault_runner.py's results logger.
CANONICAL = [
    "timestamp", "service", "fault_type", "repetition",
    "baseline_p95_ms", "fault_p95_ms", "latency_p95_delta_ms",
    "baseline_p99_ms", "fault_p99_ms", "latency_p99_delta_ms",
    "baseline_error_rate", "fault_error_rate", "error_rate_delta",
    "downstream_affected_count", "downstream_affected_services",
    "recovery_time_s", "health_check_pass", "integration_tests_pass",
]


def from_csv(src: Path, batch: str) -> pd.DataFrame:
    df = pd.read_csv(src)
    df.insert(0, "batch", batch)
    return df


def from_json_dir(src_dir: Path, batch: str) -> pd.DataFrame:
    """Rebuild a batch from its per-run JSON records.

    Used for sn_legacy, whose CSV log was contaminated with fabricated rows. The JSON
    run records were written one-per-run by fault_runner.py and were never touched by
    populate_results.py, so they are a clean source for the genuine runs.
    """
    rows = []
    for path in sorted(src_dir.glob("run_*.json")):
        with open(path, "r", encoding="utf-8") as fh:
            rec = json.load(fh)
        rec["_source_file"] = path.name
        rows.append(rec)
    if not rows:
        raise SystemExit(f"[FAIL] no run_*.json found in {src_dir}")
    df = pd.DataFrame(rows)
    ordered = [c for c in CANONICAL if c in df.columns]
    rest = [c for c in df.columns if c not in ordered]
    df = df[ordered + rest]
    df.insert(0, "batch", batch)
    return df


BATCHES = [
    ("sn_controlled_sep18-20",
     lambda: from_csv(ROOT / "measurement/results_controlled/socialnetwork/experiment_log.csv",
                      "sn_controlled_sep18-20")),
    ("hr_controlled_sep18-20",
     lambda: from_csv(ROOT / "measurement/results_controlled/hotelreservation/experiment_log.csv",
                      "hr_controlled_sep18-20")),
    ("hr_sep13",
     lambda: from_csv(ROOT / "measurement/results/hotel/experiment_log.csv", "hr_sep13")),
    ("sn_legacy",
     lambda: from_json_dir(ROOT / "measurement/results", "sn_legacy")),
]


def digest(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()[:12]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-only", action="store_true",
                    help="Recompute and compare against what is already in data/raw/ "
                         "without writing.")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    problems = []

    for name, build in BATCHES:
        df = build()
        dest = RAW / f"{name}.csv"

        if args.verify_only:
            if not dest.exists():
                problems.append(f"{name}: {dest} missing")
                continue
            existing = pd.read_csv(dest)
            if len(existing) != len(df):
                problems.append(f"{name}: row count {len(existing)} on disk vs {len(df)} rebuilt")
            elif list(existing.columns) != list(df.columns):
                problems.append(f"{name}: column mismatch")
            else:
                print(f"[OK]   {name:<24} {len(df):>4} rows  verified")
            continue

        df.to_csv(dest, index=False)
        nz = {c: int((pd.to_numeric(df[c], errors="coerce").fillna(0) != 0).sum())
              for c in ("baseline_p95_ms", "fault_p95_ms", "fault_error_rate",
                        "downstream_affected_count", "recovery_time_s")
              if c in df.columns}
        print(f"[WROTE] {dest.relative_to(ROOT)}  rows={len(df)}  md5={digest(dest)}")
        print(f"        services={df['service'].nunique()}  "
              f"fault_types={sorted(df['fault_type'].unique())}")
        print(f"        non-zero: {nz}")

    if problems:
        for p in problems:
            print(f"[FAIL] {p}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
