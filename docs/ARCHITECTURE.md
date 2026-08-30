# Architecture

## Experiment Pipeline

```mermaid
flowchart TD
    A["Phase 1: Deploy Stack"] --> B["Phase 1: Health Check"]
    B --> C["Phase 1: Init Social Graph"]
    C --> D["Phase 1: Baseline Load"]
    D --> E["Phase 2: Collect Traces"]
    E --> F["Phase 2: Build SDG"]
    F --> G["Phase 3: Compute Centrality"]
    G --> H["Phase 4: Fault Injection Loop"]
    H --> I["Phase 5: Integration Tests"]
    I --> J["Phase 6: Correlation Analysis"]
    J --> K["Phase 6: Generate Plots"]
    K --> L["Phase 6: Identify Outliers"]
    L --> M["Phase 6: Update RESULTS.md"]

    style A fill:#4a9eff,color:#fff
    style F fill:#ff9f43,color:#fff
    style G fill:#ff6b6b,color:#fff
    style H fill:#ee5a24,color:#fff
    style J fill:#26de81,color:#fff
```

## Data Flow

```mermaid
flowchart LR
    subgraph "Data Sources"
        JAEGER["Jaeger Traces"]
        DOCKER["Docker Containers"]
    end

    subgraph "Phase 2: SDG Construction"
        TC["trace_collector.py"] --> RAW["raw_traces.json"]
        RAW --> GB["graph_builder.py"]
        GB --> SDG["sdg.json / sdg.graphml"]
    end

    subgraph "Phase 3: Centrality"
        SDG --> CC["compute_centrality.py"]
        CC --> CT["centrality_table.csv"]
    end

    subgraph "Phase 4: Fault Injection"
        FR["fault_runner.py"] --> MC["metrics_collector.py"]
        MC --> RL["results_logger.py"]
        RL --> EL["experiment_log.csv"]
    end

    subgraph "Phase 6: Analysis"
        CT --> CA["correlation_analysis.py"]
        EL --> CA
        CA --> CR["correlation_results.csv"]
        CR --> GP["generate_plots.py"]
        GP --> PLOTS["Heatmap, Scatter, Bar Charts"]
        CR --> IO["identify_outliers.py"]
        IO --> OA["outlier_analysis.csv"]
    end

    JAEGER --> TC
    JAEGER --> MC
    DOCKER --> FR
```

## DeathStarBench Social Network Architecture

The following diagram shows the microservice dependency structure of the
DeathStarBench Social Network application. This is the Service Dependency
Graph (SDG) that we construct from Jaeger traces.

```mermaid
graph TD
    NGINX["nginx-web-server<br/>(API Gateway)"]
    COMPOSE["compose-post-service<br/>(Post Orchestrator)"]
    TEXT["text-service"]
    MENTION["user-mention-service"]
    URL["url-shorten-service"]
    MEDIA["media-service"]
    UID["unique-id-service"]
    USER["user-service"]
    SOCIAL["social-graph-service"]
    POST["post-storage-service"]
    UTIMELINE["user-timeline-service"]
    HTIMELINE["home-timeline-service"]

    NGINX --> COMPOSE
    NGINX --> UTIMELINE
    NGINX --> HTIMELINE
    NGINX --> USER
    NGINX --> SOCIAL

    COMPOSE --> TEXT
    COMPOSE --> UID
    COMPOSE --> MEDIA
    COMPOSE --> USER
    COMPOSE --> POST
    COMPOSE --> UTIMELINE
    COMPOSE --> HTIMELINE

    TEXT --> MENTION
    TEXT --> URL

    HTIMELINE --> SOCIAL
    HTIMELINE --> POST

    style NGINX fill:#e74c3c,color:#fff
    style COMPOSE fill:#e67e22,color:#fff
    style HTIMELINE fill:#3498db,color:#fff
    style SOCIAL fill:#2ecc71,color:#fff
```

## Fault Injection Process

For each service, we run the following cycle:

```mermaid
sequenceDiagram
    participant LG as Load Generator
    participant SVC as Target Service
    participant PUMBA as Pumba
    participant JAEGER as Jaeger
    participant TESTS as pytest

    Note over LG: Warm-up (30s)
    LG->>SVC: Baseline traffic
    JAEGER->>JAEGER: Collect baseline traces

    Note over PUMBA: Inject fault
    PUMBA->>SVC: kill / netem delay / CPU stress
    LG->>SVC: Continue traffic (60s)
    JAEGER->>JAEGER: Collect fault-window traces

    Note over PUMBA: Remove fault
    PUMBA->>SVC: Restore
    SVC->>SVC: Recovery

    TESTS->>SVC: Integration tests
    Note over TESTS: Verify functional correctness
```
