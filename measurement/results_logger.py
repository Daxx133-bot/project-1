#!/usr/bin/env python3
"""
results_logger.py — Structured Logging for Experiment Results
==============================================================
Provides append-only logging of fault injection experiment results.
Never overwrites previous data — each run appends to the CSV and also
writes a standalone JSON file per run.

Output files:
  - measurement/results/experiment_log.csv   (cumulative, all runs)
  - measurement/results/run_<timestamp>_<service>_<fault>.json (per run)
"""

import csv
import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class ExperimentResult:
    """
    Data captured from a single fault injection experiment run.

    All timing values are in milliseconds unless noted otherwise.
    Error rates are fractions in [0.0, 1.0].
    """
    # ── Identification ─────────────────────────────────────────────
    timestamp: str                   # ISO 8601 timestamp
    service: str                     # Target service that was faulted
    fault_type: str                  # "kill", "latency", or "cpu"
    repetition: int                  # Repetition number (1, 2, 3)

    # ── Baseline metrics (pre-fault steady state) ──────────────────
    baseline_p95_ms: float = 0.0     # p95 latency during baseline
    baseline_p99_ms: float = 0.0     # p99 latency during baseline
    baseline_error_rate: float = 0.0 # Error rate during baseline

    # ── Fault-window metrics ───────────────────────────────────────
    fault_p95_ms: float = 0.0        # p95 latency during fault
    fault_p99_ms: float = 0.0        # p99 latency during fault
    fault_error_rate: float = 0.0    # Error rate during fault

    # ── Blast radius ───────────────────────────────────────────────
    downstream_affected_count: int = 0
    downstream_affected_services: str = ""  # comma-separated list

    # ── Recovery ───────────────────────────────────────────────────
    recovery_time_s: float = 0.0     # Seconds from fault removal to healthy

    # ── Validation ─────────────────────────────────────────────────
    health_check_pass: bool = False
    integration_tests_pass: bool = False

    # ── Derived metrics (computed after construction) ──────────────
    latency_p95_delta_ms: float = 0.0
    latency_p99_delta_ms: float = 0.0
    error_rate_delta: float = 0.0

    def compute_deltas(self) -> None:
        """Compute delta metrics (fault - baseline)."""
        self.latency_p95_delta_ms = self.fault_p95_ms - self.baseline_p95_ms
        self.latency_p99_delta_ms = self.fault_p99_ms - self.baseline_p99_ms
        self.error_rate_delta = self.fault_error_rate - self.baseline_error_rate


# ── CSV column order ───────────────────────────────────────────────────────
CSV_COLUMNS = [
    "timestamp", "service", "fault_type", "repetition",
    "baseline_p95_ms", "fault_p95_ms", "latency_p95_delta_ms",
    "baseline_p99_ms", "fault_p99_ms", "latency_p99_delta_ms",
    "baseline_error_rate", "fault_error_rate", "error_rate_delta",
    "downstream_affected_count", "downstream_affected_services",
    "recovery_time_s",
    "health_check_pass", "integration_tests_pass",
]


class ResultsLogger:
    """
    Handles writing experiment results to CSV (append) and per-run JSON files.
    Thread-safe for sequential writes (not concurrent).
    """

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.csv_path = self.output_dir / "experiment_log.csv"

        # Create CSV with headers if it doesn't exist
        if not self.csv_path.exists():
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()
            print(f"[INFO] Created experiment log: {self.csv_path}")

    def log_result(self, result: ExperimentResult) -> None:
        """
        Log a single experiment result.

        Appends to the cumulative CSV and writes a standalone JSON file.
        """
        # Compute derived metrics
        result.compute_deltas()

        # Append to CSV
        self._append_csv(result)

        # Write per-run JSON
        self._write_json(result)

        print(f"  [LOG] Recorded: {result.service} / {result.fault_type} / "
              f"rep {result.repetition}")

    def _append_csv(self, result: ExperimentResult) -> None:
        """Append one row to the cumulative CSV file."""
        row = asdict(result)

        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            # Only write the columns defined in CSV_COLUMNS
            filtered_row = {k: row.get(k, "") for k in CSV_COLUMNS}
            writer.writerow(filtered_row)

    def _write_json(self, result: ExperimentResult) -> None:
        """Write a standalone JSON file for this run."""
        # File name: run_<timestamp>_<service>_<fault>.json
        # Replace colons in timestamp for Windows filename compatibility
        safe_ts = result.timestamp.replace(":", "-").replace("+", "p")
        filename = f"run_{safe_ts}_{result.service}_{result.fault_type}.json"
        json_path = self.output_dir / filename

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(result), f, indent=2)

    def get_all_results(self) -> list[dict]:
        """Read back all results from the CSV (for analysis)."""
        results = []
        if self.csv_path.exists():
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    results.append(row)
        return results
