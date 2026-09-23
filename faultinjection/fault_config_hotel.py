"""
fault_config_hotel.py — Hotel Reservation Experiment Configuration
===================================================================
Hotel-specific configuration constants and default ExperimentConfig
for the Hotel Reservation benchmark.

The Hotel stack runs on different ports than Social Network:
  - HTTP frontend: port 5000 (SN uses 8080)
  - Jaeger UI:     port 16687 (SN uses 16686)

This avoids port conflicts when running both benchmarks sequentially
(or simultaneously on machines with enough RAM).
"""

from faultinjection.fault_config import ExperimentConfig, FaultType

# ── Hotel application services (excluded from fault injection) ─────────────
# These are storage, infrastructure, and caching services that must remain
# running for the application to function at all during experiments.
HOTEL_EXCLUDED_SERVICES = {
    # Jaeger tracing infrastructure
    "jaeger",
    # Memcached caches
    "memcached-profile",
    "memcached-rate",
    "memcached-reserve",
    # MongoDB backends
    "mongodb-geo",
    "mongodb-profile",
    "mongodb-rate",
    "mongodb-reservation",
    "mongodb-user",
    "mongodb-recommendation",
    # Service discovery (if present)
    "consul",
    "tls",
}

# ── Default Hotel Experiment Configuration ─────────────────────────────────
HOTEL_EXPERIMENT_CONFIG = ExperimentConfig(
    services=[],                    # auto-loaded from Hotel SDG at runtime
    fault_types=[
        FaultType.KILL,             # Container kill (SIGKILL)
        FaultType.LATENCY,          # Network latency (100ms via Pumba netem)
        FaultType.CPU,              # CPU stress (Pumba stress, 2 workers)
    ],
    repetitions=2,                  # 2 reps per (service, fault) = 48 total runs
    warmup_seconds=30,              # 30s baseline before fault injection
    fault_duration=60,              # 60s fault window (matches Social Network)
    cooldown_seconds=30,            # 30s recovery window
    load_rate=50,                   # 50 concurrent Locust users
    load_mode="locust",
    nginx_url="http://localhost:5000",    # Hotel frontend (NOT nginx, but Go gateway)
    jaeger_url="http://localhost:16687",  # Hotel-specific Jaeger instance
    dsb_dir="",                     # Resolved at runtime by fault_runner.py
    output_dir="",                  # Resolved at runtime to measurement/results/hotel/
)

# ── Hotel Jaeger default URL ───────────────────────────────────────────────
HOTEL_JAEGER_URL = "http://localhost:16687"
HOTEL_BASE_URL = "http://localhost:5000"

# ── Expected total runs ────────────────────────────────────────────────────
# 8 services × 3 fault types × 2 repetitions = 48 runs
# Estimated time: ~4 hours (30s warmup + 60s fault + 30s cooldown + ~30s overhead per run)
HOTEL_EXPECTED_TOTAL_RUNS = 8 * 3 * 2  # = 48
HOTEL_ESTIMATED_HOURS = (HOTEL_EXPECTED_TOTAL_RUNS * (30 + 60 + 30 + 30)) / 3600  # ≈ 4h
