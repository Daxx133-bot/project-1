# Setup Guide

Step-by-step instructions to reproduce the full experiment pipeline on a fresh machine.

## Prerequisites

### Hardware
- **Minimum**: 8 GB RAM, 4 CPU cores, 20 GB free disk space
- **Recommended**: 16 GB RAM, 8 CPU cores, 40 GB free disk
- The DeathStarBench Social Network runs ~28 Docker containers simultaneously

### Software
| Tool | Version | Purpose |
|------|---------|---------|
| Docker Desktop | ≥ 4.0 (WSL2 backend) | Container runtime |
| Docker Compose | ≥ 2.0 (included in Docker Desktop) | Service orchestration |
| Python | ≥ 3.11 | All scripts |
| Git | Any recent | Clone DeathStarBench |
| pip | Any recent | Install Python packages |

### Docker Desktop Configuration (Windows)
1. **Enable WSL2 backend** — required for Pumba fault injection and `tc netem`.
2. **Allocate resources** in Docker Desktop → Settings → Resources:
   - Memory: ≥ 8 GB (ideally 12 GB)
   - CPUs: ≥ 4
   - Disk: ≥ 30 GB
3. Ensure ports `8080`, `8081`, and `16686` are not in use by other services.

---

## Quick Start

```bash
# 1. Clone this project (or unzip)
cd C:\Users\daksh\.gemini\antigravity-ide\scratch
git clone <this-repo-url> microservice-failure-analysis
cd microservice-failure-analysis

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Deploy DeathStarBench (clones repo + starts Docker stack)
python infra/setup_env.py

# 4. Initialize social graph data (~1K users, ~2 min)
python infra/init_social_graph.py

# 5. Verify everything is healthy
python infra/health_check.py

# 6. Generate baseline load and confirm traces in Jaeger
python infra/generate_baseline_load.py --mode auto --duration 60 --rate 50
```

After step 6, open the **Jaeger UI** at [http://localhost:16686](http://localhost:16686)
and verify you can see traces from services like `nginx-web-server`, `compose-post-service`, etc.

---

## Detailed Phase-by-Phase Instructions

### Phase 1 — Environment & Deployment

#### Step 1.1: Clone DeathStarBench
```bash
python infra/setup_env.py
```
This script:
- Clones `https://github.com/delimitrou/DeathStarBench.git` with submodules (for wrk2)
- Copies `infra/docker-compose.override.yml` into the `socialNetwork/` directory
- Runs `docker-compose up -d`
- Waits for all containers to start (up to 120s)

**First run** will download ~5 GB of Docker images. Subsequent runs are instant.

If you already have DSB cloned elsewhere:
```bash
python infra/setup_env.py --dsb-dir "C:\path\to\DeathStarBench" --skip-clone
```

#### Step 1.2: Initialize Social Graph
```bash
python infra/init_social_graph.py --graph socfb-Reed98
```
Available datasets:
| Dataset | Users | Use case |
|---------|-------|----------|
| `socfb-Reed98` | ~962 | Quick testing (default) |
| `ego-twitter` | ~81K | Medium-scale experiments |
| `soc-twitter-follows-mun` | ~400K | Full-scale (needs lots of RAM) |

#### Step 1.3: Health Check
```bash
python infra/health_check.py
```
Checks: Docker containers, Nginx, Jaeger, and core user flows (register → login → post → timeline).

#### Step 1.4: Baseline Load
```bash
# Auto mode: tries wrk2, falls back to Locust
python infra/generate_baseline_load.py --mode auto --duration 60 --rate 50

# Explicitly use Locust (if wrk2 build fails on your machine)
python infra/generate_baseline_load.py --mode locust --duration 60 --rate 30
```

### Phase 2 — SDG Construction
```bash
python sdg/trace_collector.py --lookback 2h --limit 2000
python sdg/graph_builder.py
```
Outputs: `sdg/output/sdg.graphml`, `sdg/output/sdg.json`

### Phase 3 — Centrality Computation
```bash
python centrality/compute_centrality.py
```
Outputs: `centrality/output/centrality_table.csv`, `centrality/output/centrality_table.json`

### Phase 4 — Fault Injection
```bash
# Full experiment (all services, all fault types, 3 reps each)
python faultinjection/fault_runner.py

# Quick test run (2 services, kill only, 1 rep)
python faultinjection/fault_runner.py \
    --services compose-post-service,nginx-thrift \
    --faults kill \
    --reps 1
```

### Phase 5 — Integration Tests
```bash
pytest tests/ -v --tb=short
```

### Phase 6 — Analysis
```bash
python analysis/correlation_analysis.py
python analysis/generate_plots.py
python analysis/identify_outliers.py
```

### Full Pipeline (all phases)
```bash
python scripts/run_full_experiment.py
```

---

## Troubleshooting

### Docker containers keep restarting
- Check logs: `docker-compose logs <service-name>` (run in the socialNetwork dir)
- Common cause: insufficient memory. Increase Docker Desktop memory allocation.
- Jaeger issue: If tracing services crash, check if Jaeger version is pinned to 1.62.0 in the override.

### No traces in Jaeger
- Verify Jaeger container is running: `docker ps | grep jaeger`
- Check if services can reach Jaeger: `docker-compose logs compose-post-service | grep jaeger`
- Generate some traffic first — traces only appear after requests are made.

### wrk2 Docker build fails
- Use Locust instead: `python infra/generate_baseline_load.py --mode locust`
- If on ARM64 (Apple Silicon Mac), wrk2 may need source modifications. Locust is the safer choice.

### "Port already in use" errors
- Check what's using the port: `netstat -ano | findstr :8080`
- Kill the conflicting process or change the port in the override file.

### Pumba fault injection doesn't work
- Pumba needs access to `/var/run/docker.sock` — this works in WSL2 but not all Windows Docker setups
- Verify: `docker run --rm -v /var/run/docker.sock:/var/run/docker.sock ghcr.io/alexei-led/pumba --help`

---

## Project Structure

```
microservice-failure-analysis/
├── infra/                  # Docker setup, health checks, load generation
│   ├── docker-compose.override.yml
│   ├── setup_env.py
│   ├── health_check.py
│   ├── init_social_graph.py
│   ├── generate_baseline_load.py
│   └── Dockerfile.wrk2
├── sdg/                    # Service Dependency Graph construction
│   ├── trace_collector.py
│   └── graph_builder.py
├── centrality/             # Centrality metric computation
│   └── compute_centrality.py
├── faultinjection/         # Fault injection orchestration
│   ├── fault_config.py
│   └── fault_runner.py
├── measurement/            # Blast radius measurement
│   ├── metrics_collector.py
│   └── results_logger.py
├── analysis/               # Statistical analysis & visualization
│   ├── correlation_analysis.py
│   ├── generate_plots.py
│   └── identify_outliers.py
├── tests/                  # pytest integration tests
│   ├── conftest.py
│   ├── test_user_flows.py
│   └── test_service_health.py
├── scripts/                # Orchestration
│   ├── run_full_experiment.py
│   └── run_full_experiment.sh
├── docs/                   # Documentation
│   ├── SETUP.md (this file)
│   ├── ARCHITECTURE.md
│   └── RESULTS.md
├── requirements.txt
└── pyproject.toml
```
