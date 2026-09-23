# Phase 8.5 Data Collection Audit
- Confirmed DeathStarBench topologies (SN N=12, HR N=7).
- Workloads calibrated to 1000 RPS (SN) and 100 RPS (HR).
- Pumba faults mapped directly to implementation (SIGKILL 60s, tc netem 100ms +-20ms jitter 30s, stress-ng 30s).
- Definition of `recovery_time_s` mapped to the 10% median tolerance over 10 consecutive seconds, capped at 60s.
