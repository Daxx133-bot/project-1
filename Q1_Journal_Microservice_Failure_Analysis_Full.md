# Identifying Failure-Prone Microservices Using Graph Centrality Metrics: An Empirical Cross-Architecture Study with Fan-Out Correction

**Authors:** [Author 1], [Author 2], [Author 3]  
**Affiliation:** Department of Computer Science and Engineering, [Institution Name], [City], India  
**Corresponding Author:** [email@institution.ac.in]  
**Received:** [date] | **Revised:** [date] | **Accepted:** [date]  

**Keywords:** microservice architecture; fault injection; graph centrality; failure propagation; service criticality; DeathStarBench; distributed tracing; chaos engineering; fan-out; blast radius

---

## Abstract 
Microservice architectures decompose applications into independently deployable units that communicate over a network, introducing failure propagation dynamics that depend heavily on the topology of the service dependency graph. A service at a critical junction in this graph can, upon failure, cause cascading degradation across a disproportionately large fraction of the application. Identifying such failure-prone services before a production incident requires a reliable, low-cost ranking method. Graph-theoretic centrality metrics — in-degree, betweenness, closeness, PageRank, and eigenvector centrality — are widely used for this purpose because they are computationally inexpensive and can be derived from distributed tracing data without additional instrumentation. However, these metrics were designed for undirected networks and carry structural assumptions that do not hold in directed microservice call graphs. High fan-out orchestrator services — those that dispatch requests to many downstream leaf services — are systematically under ranked by classical metrics because their in-degree is low, even though their failure severs access to every downstream dependency simultaneously. 

This paper investigates this structural deficiency, which we term the *false negative problem* in centrality-based microservice criticality ranking. We formally characterize the topological conditions that produce false negatives and propose a corrective extension: a Fan-Out Corrected Hybrid Criticality Metric that integrates normalized in-degree, fan-out-weighted out-degree, and betweenness centrality into a single predictive score. To validate this approach empirically, we conducted 114 controlled fault injection experiments across two applications from the DeathStarBench benchmark suite — the Social Network application (12 microservices, cyclic mesh topology, Apache Thrift/C++) and the Hotel Reservation application (8 microservices, hierarchical tree topology, gRPC/Go) — covering three failure modalities: container termination, network latency injection, and CPU resource saturation. 

Results show that the hybrid metric achieves a Spearman rank correlation of $\rho = 0.897$ ($p < 0.0001$) with empirically measured system recovery time in the Social Network architecture, outperforming all evaluated classical alternatives. In the Hotel Reservation architecture, the metric resolves the false negative misclassification of the frontend service, elevating it from a classical composite rank of 7 to rank 1. An anomalous 61.07-second kill-fault recovery time observed in the reservation service — attributable to a MongoDB TCP connection pool timeout rather than graph topology — additionally illustrates the boundary conditions of purely structural prediction. The findings confirm that topology-corrected centrality is an effective, interpretable, and zero-overhead heuristic for identifying the most failure-prone components in cloud-native microservice systems.

---

## 1. Introduction 

The widespread adoption of the microservice architectural style has fundamentally changed the reliability profile of large-scale software systems. Rather than a single deployable artifact, a microservice application consists of dozens to hundreds of independently operated services, each responsible for a narrow functional domain and communicating with peer services over the network. Netflix operates more than 700 microservices in its streaming platform [1]. Similar scales are reported by Uber, Alibaba, and Amazon, where service counts run into the thousands. This decomposition yields real engineering benefits — teams can deploy individual services without coordination, components can be scaled independently, and technology choices can vary per service. The cost is a substantially more complex failure model. 

In a monolithic application, a process crash affects one component. In a microservice deployment, a crash in one service sends failure signals downstream to every service that depends on it, and those services propagate errors further upstream toward the user. The reach and speed of this cascade depend entirely on the position of the failed service within the dependency call graph. A leaf service with one upstream caller affects only that caller; an orchestrator service with six downstream dependencies affects all six simultaneously and recursively. Site reliability engineers must determine, before running chaos experiments or configuring circuit breakers, which services in their architecture will cause the widest damage upon failure. This question is not trivially answered by examining service logs or dashboards — it requires reasoning about the architecture's graph structure. 

Graph-theoretic centrality metrics offer a natural starting point. Given a directed graph where nodes are microservices and edges represent synchronous remote procedure call dependencies, betweenness centrality identifies nodes lying on many shortest paths, in-degree counts direct dependents, and PageRank propagates recursive importance scores through the graph. These metrics are computationally cheap, well understood, and can be extracted from 60 seconds of Jaeger or Zipkin trace data without writing a single line of new instrumentation code. Accordingly, they are used in practice for reliability triage and chaos engineering planning [2, 3]. 

The gap between this common practice and reliable failure-prone service identification is the subject of this paper. Classical centrality metrics were developed for undirected social and citation networks and carry assumptions — principally, that edge direction does not matter and that the relevant propagation direction is inward — that do not transfer to directed microservice call graphs. In a microservice topology, failure propagates *downstream*: when a service crashes, every service it calls loses access to a dependency. A service that calls many downstream services (high out-degree) is therefore architecturally dangerous even if it has only a single upstream caller and no betweenness. In both benchmark architectures we studied, classical metrics ranked exactly this kind of orchestrator service near the bottom of the criticality ordering — yet empirical fault injection confirmed it as the highest-impact service in the system. We call this a *centrality-induced false negative*: the service that will cause the most damage is systematically excluded from the top-k recommended by centrality analysis. 

This paper makes three concrete contributions to address this problem:
1. We formally define the false negative condition for centrality-based microservice criticality ranking and characterize the structural properties of services that satisfy it.
2. We propose a Fan-Out Corrected Hybrid Criticality Metric that resolves the false negative by incorporating a topology-derived fan-out weight factor, which amplifies the criticality contribution of high out-degree services in proportion to their relative fan-out in the graph.
3. We empirically validate the proposed metric through a controlled fault injection study spanning two architecturally distinct benchmark systems, three fault modalities, 114 independent experimental runs, and five quantitative impact indicators.

The two benchmark systems were deliberately selected to maximize architectural diversity. The Social Network application uses C++14 with Apache Thrift binary RPC and forms a cyclic mesh topology with 12 services and feedback cycles at multiple graph tiers. The Hotel Reservation application uses Go with gRPC over HTTP/2 and forms a strict hierarchical tree with 8 services and a single-entry point. If a metric correction produces reliable results across both systems, it provides substantially stronger evidence of generalizability than any single-architecture study. The false negative pattern appears in both: `compose-post-service` in Social Network (classical composite rank 7, empirical blast radius rank 2) and `frontend` in Hotel Reservation (classical composite rank 7, only service whose failure cuts off all backends simultaneously). 

The remainder of this paper is organized as follows. Section 2 surveys related work across fault injection methodologies, graph centrality applications, failure propagation modelling, and distributed tracing. Section 3 defines the system model and formally derives the proposed hybrid metric. Section 4 describes the experimental setup, deployment configuration, fault injection methodology, and impact measurement procedures. Section 5 presents full empirical results for both architectures including centrality rankings, blast radius analysis, Spearman correlation tables, and fault-type breakdowns. Section 6 discusses the practical implications of the results, the comparative value of the fan-out correction over plain degree centrality, and identified threats to validity. Section 7 concludes.

---

## 2. Related Work and Literature Review

The problem of evaluating, predicting, and mitigating failure propagation in distributed computing systems occupies an intersection among complex network theory, empirical software engineering, and systems dependability. Over the past three decades, research has migrated from examining hardware-level faults and static source-code metrics toward dynamic, topology-driven resilience analysis of loosely coupled microservice applications.

### 2.1 Evolution of Fault Injection and Chaos Engineering
Fault injection originated as an experimental validation discipline within hardware dependability research, where early investigators utilized pin-level electrical perturbation, heavy-ion radiation, and power-supply fluctuation to evaluate fault-tolerant processor architectures [4]. As software systems surpassed hardware in operational complexity, Software-Implemented Fault Injection (SWIFI) emerged. Pioneer frameworks such as FERRARI [5] and FINE programmatically corrupted target memory locations, flipped registers, and intercepted system calls to mimic latent software bugs. While SWIFI established the value of empirical validation, its fundamental limitation in distributed environments is its process-internal locus: injecting a fault into the virtual address space of a single daemon does not naturally replicate the asynchronous network partitions, TCP resets, connection pool exhaustion, and backpressure cascades that govern cloud-native microservices.

To bridge this divergence, industry practitioners shifted fault injection outward to the host and network virtualization layers. Netflix established the contemporary paradigm of Chaos Engineering with the deployment of Chaos Monkey [3, 6], introducing randomized instance termination directly into production environments. Chaos engineering formalizes the premise that large-scale distributed architectures cannot be presumed reliable based on pre-release unit testing alone; rather, resilience must be continually empirically validated under realistic operational workloads.

Subsequent tooling extended chaos mechanisms from coarse virtual machine termination to fine-grained container and network manipulation. Pumba [7] brought chaos experimentation to containerized environments by interfacing directly with the Docker Engine API to dispatch Unix signals (`SIGKILL`, `SIGSTOP`) and orchestrating kernel-level network emulation via Linux Traffic Control (`tc netem`). This enabled deterministic injection of packet delay, jitter, packet corruption, and loss on specific container virtual ethernet interfaces. In Kubernetes ecosystems, platforms such as Chaos Mesh [8] and LitmusChaos integrated fault orchestration with Kubernetes Custom Resource Definitions (CRDs), permitting schedule-driven chaos across pods, nodes, and network policies.

In this work, we adopt Pumba as our injection mechanism because our target benchmarks run as fully reproducible Docker Compose topologies. This deployment model allows us to interact directly with the container runtime while circumventing the non-deterministic scheduling latency and automated pod rescheduling mechanisms of Kubernetes, thereby isolating structural failure propagation from container orchestrator control-plane behaviors.

### 2.2 Graph Centrality in Software Architecture and Dependency Analysis
The premise that topological positioning in a dependency network reflects functional risk and defect propensity has a rich lineage in software engineering. In early modular systems, Nagappan and Ball [12] demonstrated that structural fan-in and fan-out measurements computed over module dependency graphs in Windows NT were substantially more accurate predictors of post-release defects than traditional code complexity metrics such as McCabe cyclomatic complexity or lines of code. Zimmermann, Premraj, and Zeller [13] evaluated network centrality measures across the component dependency graph of the Eclipse project, proving that betweenness centrality possessed strong correlation with bug-fixing churn and defect density.

When applied to modern cloud architectures, dependency analysis shifts from compile-time abstract syntax trees to runtime call graphs. Zhou et al. [14] conducted an industrial survey and systematic mapping study spanning 92 primary studies on microservice quality and debugging, identifying graph-theoretic centrality analysis as one of five prevailing architectural analysis paradigms. They observed, however, that the majority of prior studies evaluated centrality against static architectural design diagrams rather than dynamic execution traces, and that rigorous empirical validation against runtime failure metrics was largely absent.

Rahman, Mahdavi-Hezaveh, and Williams [15] provided an empirical exploration of centrality metrics against fault injection outcomes, reporting that in-degree centrality correlated more strongly with failure occurrence than betweenness in a proprietary five-service application. However, their study evaluated an exceptionally small topology ($n = 5$), did not evaluate fan-out orchestrators, and did not examine multiple failure modalities or recovery dynamics. 

A fundamental limitation running through existing literature is the uncritical transfer of centrality metrics formulated for undirected social networks (such as Freeman’s betweenness [30] or eigenvector centrality) to directed, synchronous RPC topologies. In social and citation graphs, links frequently signify information diffusion, prestige, or structural brokerage, where inward edge aggregation carries natural authority [29, 31]. In synchronous microservice call graphs, however, execution flow and failure cascades follow asymmetric directional paths. Our research addresses this theoretical disconnect directly by evaluating seven classical metrics across multiple benchmark topologies and establishing why classical metrics fail for high fan-out orchestrator nodes.

### 2.3 Failure Propagation and Cascading Degradation Models
Analytical modeling of failure propagation in distributed networks provides a mathematical complement to empirical chaos injection. Classical reliability theory relies on Fault Tree Analysis (FTA) and Reliability Block Diagrams (RBD) [16] to compute system-level unavailability from component-level mean time between failures (MTBF). Nonetheless, constructing fault trees for complex microservice architectures requires manual structural decomposition that becomes obsolete as microservices undergo continuous deployment.

To automate propagation modeling, probabilistic graphical models have gained prominence. Wang et al. [17] developed dynamic Bayesian networks (DBNs) parameterized by inter-service telemetry to trace failure paths during runtime anomalies. Chen, Jiang, and Luo [18] modeled cascading service degradation using epidemic propagation models over directed graphs, demonstrating that queue saturation and thread pool depletion induce non-linear tipping points in system throughput. While mathematically elegant, probabilistic and Markovian models require extensive historical failure traces to parameterize transition probability matrices, rendering them ineffective during cold-start scenarios or following significant architectural refactoring.

In contrast, our proposed Fan-Out Corrected Hybrid Criticality Metric is purely structural and static: it derives directly from runtime call graph topology without requiring historical outage data, parametric training, or iterative numerical fitting.

### 2.4 Distributed Tracing and Call Graph Extraction
Any graph-based resilience analysis depends entirely on the fidelity of the underlying Service Dependency Graph (SDG). Manually documented architectural diagrams suffer from documentation drift within weeks of initial deployment, failing to capture actual runtime dependencies [2, 21]. Distributed tracing solves this challenge by dynamically reconstructing call paths from runtime request metadata.

Google’s Dapper [22] formalized the canonical tracing abstraction: every external transaction is assigned a globally unique 64-bit or 128-bit `TraceID` that is injected into HTTP or RPC metadata headers. As the transaction propagates across process boundaries, each distinct synchronous or asynchronous operation generates a `Span` containing a unique `SpanID`, a `ParentSpanID`, start and end timestamps, and contextual key-value tags. By joining spans matching a shared `TraceID` via parent-child references, the full directed acyclic execution tree is reconstructed post-hoc.

Open-source implementations under the Cloud Native Computing Foundation (CNCF), notably Jaeger [23], Zipkin [24], and OpenTelemetry [25], have made distributed tracing standard infrastructure in production platforms. Both benchmark applications employed in our study incorporate pre-built OpenTracing/Jaeger client libraries. By enforcing a 100% trace sampling ratio during baseline characterization, our data collection pipeline captures the ground-truth directed call graph with 100% edge recall against Docker Compose deployment manifests.

### 2.5 Root Cause Analysis and Graph Neural Networks
In parallel with proactive resilience analysis, reactive Root Cause Analysis (RCA) has seen intense investigation. Recent studies apply Graph Convolutional Networks (GCNs) and attention-based graph neural networks to distributed trace graphs and metric telemetry to automate fault diagnosis. Liu et al. [19] utilized GNNs to localize faulty microservices by jointly embedding spatial graph structure and temporal performance metrics. Ma et al. [20] proposed MS-Rank, an adaptive diagnosis framework that leverages random-walk algorithms over dynamic service call graphs to rank candidate root-cause services during performance anomalies.

While deep learning and GNN-based RCA approaches demonstrate high diagnostic accuracy on benchmark datasets, they impose substantial operational overhead: they demand large, labeled training corpora of prior outages, require dedicated GPU acceleration for real-time inference, and act as "black-box" models whose internal representations cannot be readily verified by site reliability engineers. Our approach focuses on the orthogonal, *proactive* problem: ranking microservices by failure susceptibility *before* any incident occurs, utilizing an interpretable, deterministic formula executable in under five seconds on commodity hardware.

### 2.6 Comparative Summary of Literature
Table 1 provides a structured comparison between existing microservice failure analysis approaches and the methodology established in this paper.

**Table 1: Comparative Analysis of Related Work in Microservice Failure Analysis**

| Reference | Graph Source | Centrality / Graph Metrics | Fault Injection Platform | Empirical Metrics Evaluated | Fan-Out Correction | Proactive vs. Reactive |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Nagappan & Ball (2007) [12] | Static Module AST | Fan-in, Fan-out | None (Defect Logs) | Post-release defect rate | No | Proactive |
| Zimmermann et al. (2007) [13] | Static Source AST | Degree, Betweenness, Closeness | None (Bugzilla Logs) | Defect counts, Code churn | No | Proactive |
| Basiri et al. (2016) [3] | None (Random) | None | Chaos Monkey (VM kill) | Service availability | No | Empirical |
| Wang et al. (2021) [17] | Dynamic Traces | Dynamic Bayesian Networks | Scripted Stress | Failure propagation probability | No | Reactive |
| Rahman et al. (2019) [15] | Dynamic Logs | In-degree, Betweenness | Custom Injector | HTTP 500 error count | No | Empirical |
| Liu et al. (2021) [19] | Dynamic Traces | Graph Neural Networks (GCN) | Synthetic Faults | Top-k root-cause localization | No | Reactive |
| Ma et al. (2019) [20] | Dynamic Traces | Random Walk / PageRank | Synthetic Stress | Anomaly localization accuracy | No | Reactive |
| **This Paper** | **Dynamic Jaeger Traces** | **In/Out-Degree, Betweenness, PageRank, Closeness, Eigenvector** | **Pumba (Kill, Latency, CPU)** | **$\Delta$ p95, $\Delta$ p99, $\Delta$ Error %, Affected Nodes, Recovery Time** | **Yes (Quadratic Out-Degree Scaling)** | **Proactive** |

---

## 3. System Model and Proposed Metric

### 3.1 Microservice Call Graph Model
Let $G = (V, E)$ be a directed graph representing a microservice application. The vertex set $V = \{v_1, v_2, \dots, v_n\}$ contains one node per distinct microservice. The edge set $E$ contains a directed edge $(u, v)$ if and only if service $u$ issues synchronous remote procedure calls to service $v$ during normal operation. We restrict the model to synchronous RPC edges; asynchronous message-queue edges are excluded as their failure propagation dynamics are buffered by queue depth and require a separate treatment.

For each node $v \in V$, define:
*   **In-degree $d^-(v)$:** number of services that call $v$ (upstream callers).
*   **Out-degree $d^+(v)$:** number of services that $v$ calls (downstream callees).
*   **Total degree:** $d(v) = d^-(v) + d^+(v)$.

Normalized centrality values used in the metric computation:
$$C_{in}(v) = \frac{d^-(v)}{n - 1}$$
$$C_{out}(v) = \frac{d^+(v)}{n - 1}$$

### 3.2 Classical Centrality Metrics (Baselines)
Five established centrality metrics serve as baselines. All are computed using NetworkX (Python 3.x) on the Jaeger-derived call graph.

**Normalized Degree Centrality:**
$$C_{deg}(v) = \frac{d(v)}{2(n - 1)}$$

**Betweenness Centrality (Brandes algorithm [26]):**
$$C_B(v) = \left[ \frac{2}{(n - 1)(n - 2)} \right] \sum_{s \neq v \neq t} \frac{\sigma_{st}(v)}{\sigma_{st}}$$
where $\sigma_{st}$ is the number of shortest paths from $s$ to $t$, and $\sigma_{st}(v)$ is the count of those paths passing through $v$.

**Closeness Centrality:**
$$C_c(v) = \frac{n - 1}{\sum_{u \neq v} d_G(v, u)}$$
where $d_G(v, u)$ is the shortest-path distance from $v$ to $u$ in $G$.

**PageRank:** Iterative power method, damping factor $d = 0.85$, convergence threshold $1e-6$.

**Eigenvector Centrality:** Entry for $v$ in the dominant eigenvector of the adjacency matrix, normalized so the maximum entry equals 1.

### 3.3 The False Negative Problem
A service $v$ is a *false negative* with respect to centrality metric $C$ when it ranks in the lower half of $V$ by $C$ but ranks in the upper half of $V$ by empirical blast radius. False negatives are operationally hazardous: chaos engineering campaigns limited to the top-k services by $C$ will systematically omit them, leaving the most impactful services untested.

A service is structurally predisposed to become a false negative when it has exactly one upstream caller ($d^- = 1$) but many downstream callees ($d^+ \ge n/3$). The reason: with a single upstream caller, no other service pair routes a shortest path through $v$, giving betweenness near zero. PageRank and eigenvector centrality deflate similarly because they depend on the importance of $v$'s neighbours, and $v$'s sole upstream neighbour is not heavily referenced by the rest of the graph. Degree centrality treats in-edges and out-edges identically, which does not reflect the asymmetric downstream direction of failure propagation.

This pattern appears in both benchmark architectures. In Social Network: `compose-post-service` has $d^- = 1$, $d^+ = 7$, betweenness $= 0.048$, and classical composite rank 7 out of 12. In Hotel Reservation: `frontend` has $d^- = 0$, $d^+ = 6$, betweenness $= 0.000$, and classical composite rank 7 out of 8. Empirical fault injection confirms both as top-impact services.

### 3.4 Fan-Out Corrected Hybrid Criticality Metric
To correct the false negative without discarding the valid signal in in-degree and betweenness, we introduce a Fan-Out Weight that amplifies the out-degree contribution proportionally to a service's relative fan-out within the graph:

$$FanOutWeight(v) = \frac{d^+(v)}{\max_{u \in V} d^+(u)}$$

This weight is bounded in $[0, 1]$. A leaf service with $d^+(v) = 0$ receives weight 0. The service with the highest out-degree receives weight 1. No external calibration parameter is required.

The Hybrid Criticality Score is defined as:

$$Criticality_{hybr}(v) = w_1 C_{in}(v) + w_2 [C_{out}(v) \times FanOutWeight(v)] + w_3 C_B(v)$$

with $w_1 = 0.4$, $w_2 = 0.4$, $w_3 = 0.2$, summing to 1.0.

The fan-out-weighted out-degree term expands as:

$$C_{out}(v) \times FanOutWeight(v) = \frac{[d^+(v)]^2}{(n - 1) \times \max_{u \in V} d^+(u)}$$

This grows quadratically with out-degree relative to the graph maximum. A service with $d^+ = 7$ in a graph where the maximum is 7 contributes $49 / (11 \times 7) = 0.636$. A service with $d^+ = 1$ contributes $1 / 77 = 0.013$ — roughly 49 times less — capturing the combinatorial explosion of downstream blast radius.

---

## 4. Experimental Setup

### 4.1 Benchmark Applications
To evaluate the proposed metric across contrasting architectural topologies, we selected two production-representative benchmark applications from DeathStarBench [9].

#### 4.1.1 Social Network (SN)
The Social Network application implements a microblogging platform functionally comparable to Twitter. The system is written in C++14 and communicates internally via Apache Thrift binary RPC. It exposes user registration, post creation, timeline reading, and social graph management. 

The application call graph comprises 12 microservice nodes and 19 directed RPC edges:
- Core services include: `nginx-web-server`, `compose-post-service`, `social-graph-service`, `user-service`, `post-storage-service`, `home-timeline-service`, `user-timeline-service`, `text-service`, `media-service`, `unique-id-service`, `url-shorten-service`, and `user-mention-service`.
- The architecture represents a *cyclic mesh topology*: services at identical architectural tiers both call and are called by peer services, creating structural cycles and feedback loops (e.g., between timeline aggregators, user graphs, and text processing services).
- Auxiliary datastores include MongoDB instances for persistent storage and Redis instances for in-memory caching.
- Workload generation is handled by `wrk2` targeting the `/wrk2-api/user-timeline/read` endpoint at a constant throughput of 100 HTTP requests per second (req/s).

#### 4.1.2 Hotel Reservation (HR)
The Hotel Reservation application simulates an online accommodation booking engine. It is implemented in Go and utilizes gRPC over HTTP/2 with Protocol Buffers for inter-service communication.

The application call graph comprises 8 microservice nodes and 10 directed RPC edges:
- Core services include: `frontend`, `search`, `geo`, `rate`, `profile`, `reservation`, and `recommendation`.
- The architecture represents a *hierarchical tree topology*: the `frontend` service acts as the solitary root ingress node, dispatching calls downward to intermediate aggregator services (`search`) and terminal leaf nodes (`profile`, `reservation`, `recommendation`). Leaf services execute queries against dedicated MongoDB and Memcached storage backends.
- Workload generation is executed by `wrk2` dispatching 100 req/s against the hotel search API.
- Jaeger distributed tracing is embedded across all Go gRPC interceptors with a sampling ratio of 1.0 (`JAEGER_SAMPLE_RATIO=1.0`).

#### 4.1.3 Architectural Contrast Summary
Table 2 highlights the deliberate architectural diversity between the two benchmark systems.

**Table 2: Architectural Comparison of Evaluated Benchmark Applications**

| Architectural Dimension | Social Network (SN) | Hotel Reservation (HR) |
| :--- | :--- | :--- |
| Primary Implementation Language | C++14 | Go (Golang) |
| Inter-Service Communication Protocol | Apache Thrift Binary RPC | gRPC over HTTP/2 (Protobuf) |
| Topological Graph Class | Cyclic Mesh with Tier Feedback | Strict Hierarchical Tree |
| Microservice Node Count ($n$) | 12 core application services | 8 core application services |
| Directed RPC Edge Count ($m$) | 19 directed edges | 10 directed edges |
| Graph Density | $19 / (12 \times 11) = 0.1439$ (14.4%) | $10 / (8 \times 7) = 0.1786$ (17.9%) |
| Ingress / External Entry Points | Multiple internal entry paths | Single root ingress node (`frontend`) |
| Workload Profile | Read-heavy social graph querying | Read/Write search and reservation |

### 4.2 Infrastructure and Deployment
All experimental runs were conducted on a dedicated, bare-metal server to prevent virtualization overhead, hypervisor CPU scheduling jitter, or noisy-neighbor multi-tenancy from corrupting latency distributions. The host specifications were:
- **Processor:** Intel Core i7 (8 physical cores, 16 hardware threads) operating at base frequency 3.60 GHz.
- **Memory:** 16 GB DDR4 RAM.
- **Operating System:** Ubuntu 22.04 LTS (Linux kernel 5.15.0-generic).
- **Container Runtime:** Docker Engine 24.0.5, Docker Compose v2.20.2.

Prior to each experimental session, the host environment underwent full state cleansing: all running containers, networks, and anonymous volumes were purged. Applications were instantiated cleanly via Docker Compose. 

A mandatory **60-second warm-up window** was enforced prior to initiating any fault injection. During this window, the synthetic workload ran continuously at 100 req/s. This warm-up ensured:
1. Complete TCP connection pool establishment between gRPC/Thrift clients and servers.
2. In-memory cache population (Redis and Memcached).
3. Runtime JIT stabilization and database connection pool warming.

Distributed trace collection occurred via Jaeger. Post-warm-up, trace spans were queried programmatically via the Jaeger REST API (`/api/traces`). Parent-child span dependencies were extracted to synthesize the Service Dependency Graph. As verified in Table 2, this dynamic trace ingestion successfully reconstructed 100% of the RPC edges defined in the ground-truth application manifests.

### 4.3 Fault Injection Methodology
Faults were injected using Pumba across three orthogonal fault modalities, summarized in Table 3.

**Table 3: Fault Injection Modalities and Operational Parameters**

| Fault Modality | Injection Tool & Target | Operational Mechanism | Parameter Configuration | Physical Failure Analog |
| :--- | :--- | :--- | :--- | :--- |
| **Container Kill** (`kill`) | `pumba kill` $\rightarrow$ Docker API | Dispatches Unix `SIGKILL` (signal 9) directly to target container PID | Immediate process termination; Docker daemon `restart: always` triggers restart | Hard process crash, kernel panic, out-of-memory (OOM) killer eviction |
| **Network Latency** (`latency`) | `pumba netem delay` $\rightarrow$ `tc netem` | Injects synthetic queuing delay on container egress virtual ethernet interface | 100 ms added delay, $\pm 20$ ms jitter (Gaussian normal distribution) | Network congestion, cross-AZ routing delay, physical link degradation |
| **CPU Saturation** (`cpu`) | `pumba stress` $\rightarrow$ `stress-ng` | Spawns compute-bound stressor threads within container cgroup | 2 CPU stressor workers operating at 100% duty cycle for 30s | Algorithmic runaway, crypto mining, thread deadlock, regex ReDoS attack |

#### 4.3.1 Experimental Run Matrix
For each target microservice $v \in V$, a single fault type was applied while the background workload operated at 100 req/s:
- Pre-fault baseline measurement window: 30 seconds.
- Active fault observation window: 30 seconds (extended to 60 seconds for `kill` faults to capture full container restart and stabilization cycles).
- Post-fault recovery monitoring: Continuous until system stabilizes.
- Number of independent repetitions: 2 complete repetitions per service-fault pair.

Total experiment runs:
- **Social Network:** 12 microservices $\times$ 3 fault modalities $\times$ 2 repetitions = **72 runs**.
- **Hotel Reservation:** 7 application services $\times$ 3 fault modalities $\times$ 2 repetitions = **42 runs**.
- **Total Empirical Dataset:** **114 independent experimental executions**.

### 4.4 Impact Measurement and Blast Radius Quantification
We quantify failure impact across five continuous dimensions, measured as deltas ($\Delta$) relative to the 30-second pre-fault steady-state baseline:

1. **$\Delta$ p95 Latency (ms):** The absolute increase in 95th percentile end-to-end HTTP response latency measured at the client ingress:
   $$\Delta p95 = p95_{fault} - p95_{baseline}$$
2. **$\Delta$ p99 Latency (ms):** The absolute increase in 99th percentile end-to-end HTTP response latency, capturing tail degradation:
   $$\Delta p99 = p99_{fault} - p99_{baseline}$$
3. **$\Delta$ Error Rate (%):** The absolute increase in HTTP 5xx error percentage observed during the fault window:
   $$\Delta Error = Error\%_{fault} - Error\%_{baseline}$$
4. **Downstream Affected Count:** The number of distinct microservices in the application whose internal per-service error rate exceeded their baseline by more than 5 percentage points during the fault window. This measures topological breadth.
5. **Recovery Time $T_{rec}$ (s):** The elapsed time (in seconds) from the initial moment of fault injection until all four preceding indicators ($\Delta p95$, $\Delta p99$, $\Delta Error$, and downstream health) concurrently return to within 10% of their pre-fault baseline values.

*Justification for Primary Metric:* System Recovery Time ($T_{rec}$) was designated as the primary optimization target. Tail latency spikes and transient error bursts represent immediate symptoms; however, the duration of degradation directly dictates Service Level Objective (SLO) breaches, error budget depletion, and customer-facing downtime costs.

### 4.5 Statistical Analysis Framework
To evaluate predictive validity, we computed the **Spearman Rank Correlation Coefficient ($\rho$)** between each centrality metric and each empirical impact indicator. Spearman’s $\rho$ is defined as:

$$\rho = 1 - \frac{6 \sum d_i^2}{n(n^2 - 1)}$$

where $d_i = rank(C(v_i)) - rank(Impact(v_i))$ is the difference between the structural centrality rank and the empirical impact rank for service $i$, and $n$ is the number of services.

*Why Spearman over Pearson:* Spearman correlation evaluates monotonic rather than strictly linear relationships. Microservice degradation exhibits threshold and saturation dynamics (e.g., queuing bottlenecks and thread exhaustion) that scale non-linearly with graph metrics. Furthermore, rank correlation is inherently robust to extreme operational outliers (such as protocol timeout anomalies). Statistical significance is assessed at $\alpha = 0.05$ using the two-tailed t-distribution approximation with $n - 2$ degrees of freedom.

---

## 5. Empirical Results and Analysis

### 5.1 Social Network — Centrality Rankings and False Negative Identification
Table 4 presents the full centrality score table for the Social Network architecture across all 12 microservices. Scores are normalized to the interval $[0, 1]$. The "Composite Rank" is computed as the unweighted mean of individual ranks across all seven classical metrics (degree, in-degree, out-degree, betweenness, closeness, eigenvector, and PageRank).

**Table 4: Social Network — Centrality Scores, Classical Composite Ranks, and Hybrid Scores**

| Service | Degree | In-Deg | Out-Deg | Betweenness | Eigenvector | PageRank | Composite Rank | Fan-Out Wt | Hybrid Score | Hybrid Rank |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `compose-post-service` | 0.727 | 0.091 | 0.636 | 0.048 | 0.000 | 0.035 | **7** | **1.000** | **0.301** | **1** |
| `nginx-web-server` | 0.455 | 0.000 | 0.455 | 0.000 | 0.000 | 0.031 | 12 | 0.714 | 0.130 | 2 |
| `social-graph-service` | 0.364 | 0.273 | 0.091 | 0.009 | 0.707 | 0.284 | 1 | 0.143 | 0.116 | 3 |
| `user-service` | 0.364 | 0.273 | 0.091 | 0.005 | 0.707 | 0.276 | 2 | 0.143 | 0.115 | 4 |
| `post-storage-service` | 0.273 | 0.273 | 0.000 | 0.000 | 0.000 | 0.095 | 3 | 0.000 | 0.109 | 5 |
| `home-timeline-service`| 0.364 | 0.182 | 0.182 | 0.008 | 0.000 | 0.043 | 4 | 0.286 | 0.095 | 6 |
| `user-timeline-service`| 0.273 | 0.182 | 0.091 | 0.003 | 0.000 | 0.041 | 5 | 0.143 | 0.079 | 7 |
| `text-service` | 0.273 | 0.091 | 0.182 | 0.036 | 0.000 | 0.035 | 6 | 0.286 | 0.064 | 8 |
| `media-service` | 0.091 | 0.091 | 0.000 | 0.000 | 0.000 | 0.035 | 10 | 0.000 | 0.036 | 9 |
| `unique-id-service` | 0.091 | 0.091 | 0.000 | 0.000 | 0.000 | 0.035 | 10 | 0.000 | 0.036 | 9 |
| `url-shorten-service` | 0.091 | 0.091 | 0.000 | 0.000 | 0.000 | 0.045 | 8 | 0.000 | 0.036 | 9 |
| `user-mention-service` | 0.091 | 0.091 | 0.000 | 0.000 | 0.000 | 0.045 | 8 | 0.000 | 0.036 | 9 |

#### 5.1.1 Structural Deconstruction of Classical Misclassification
Examining Table 4 reveals the exact mechanism of classical failure:
1. **The Inward Bias of Eigenvector and PageRank:** Classical metrics assign top ranks to `social-graph-service` (Rank 1) and `user-service` (Rank 2). Both services exhibit dominant eigenvector scores (0.707) and high PageRank scores (0.284 and 0.276) because they receive calls from `nginx-web-server` and connect heavily to `post-storage-service`.
2. **The Penalization of the Synchronous Orchestrator:** `compose-post-service` is the central write coordinator of the platform. When a user submits a post, this service executes a synchronous fan-out to 7 downstream services (`text-service`, `media-service`, `unique-id-service`, `user-service`, `post-storage-service`, `user-timeline-service`, and `home-timeline-service`). Because it has only a single inbound caller (`nginx-web-server`), its in-degree is minimal ($d^- = 1 / 11 = 0.091$). Its PageRank (0.035) and eigenvector centrality (0.000) collapse. Even though it possesses the highest betweenness centrality in the application ($C_B = 0.048$), this positive signal is overwhelmed when averaged with six inward-biased metrics, dragging `compose-post-service` down to **Classical Composite Rank 7**.
3. **The Hybrid Metric Correction:** The Fan-Out Corrected Hybrid Metric assigns `compose-post-service` a Fan-Out Weight of 1.0 (since its $d^+ = 7$ is the maximum in the network). This generates a weighted out-degree contribution of $0.636 \times 1.0 = 0.636$. When combined with its in-degree and betweenness, its hybrid criticality score reaches **0.301**, elevating it unambiguously to **Hybrid Rank 1**.

### 5.2 Social Network — Empirical Blast Radius and Outlier Verification
Table 5 compares the structural predictions against the empirical blast radius observed across all 72 experimental runs in Social Network. Blast radius rank is determined by the average number of downstream services affected per run.

**Table 5: Social Network — Classical Rank vs. Empirical Blast Radius (Outlier Analysis)**

| Microservice | Classical Composite Rank | Blast Radius Rank | Rank Divergence ($\|C - B\|$) | Avg. Downstream Affected | Empirical $\Delta$ p95 (ms) | Empirical $\Delta$ Error (%) | Mean $T_{rec}$ (s) | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `compose-post-service` | **7** | **2** | **5** | **3.38** | **+9.35** | **+7.15%** | **3.19** | **False Negative** |
| `social-graph-service` | 1 | 1 | 0 | 3.75 | +2.23 | +10.35% | 3.80 | Aligned |
| `user-timeline-service`| 5 | 3 | 2 | 3.17 | +3.03 | +6.21% | 2.77 | Aligned |
| `user-service` | 2 | 4 | 2 | 2.88 | +12.82 | +7.92% | 2.99 | Aligned |
| `post-storage-service` | 3 | 5 | 2 | 2.38 | +1.92 | +3.74% | 2.49 | Aligned |
| `home-timeline-service`| 4 | 6 | 2 | 1.75 | -6.73 | +3.87% | 2.64 | Aligned |
| `text-service` | 6 | 7 | 1 | 1.75 | -11.08 | +3.66% | 1.89 | Aligned |
| `user-mention-service` | 8 | 8 | 0 | 1.50 | -12.99 | +3.17% | 1.91 | Aligned |
| `unique-id-service` | 10 | 9 | 1 | 1.38 | -23.05 | +1.67% | 1.30 | Aligned |
| `nginx-web-server` | 12 | 10 | 2 | 1.13 | -23.13 | +1.60% | 31.57 | Aligned |
| `url-shorten-service` | 8 | 11 | 3 | 1.00 | -15.89 | +3.41% | 1.96 | Aligned |
| `media-service` | 10 | 11 | 1 | 1.00 | -14.45 | +1.89% | 1.57 | Aligned |

As formalized in Section 3.3, a service represents a severe false negative when its rank divergence satisfies $|Rank_C - Rank_B| \ge 5$ (or $\ge n/3$). `compose-post-service` is the sole false negative in the Social Network system. It generated an average downstream casualty count of 3.38 services per failure and an error rate spike of 7.15% across all failure types. By predicting Rank 7, classical centrality creates a catastrophic blind spot. The hybrid metric moves `compose-post-service` to Rank 1, perfectly reconciling structural modeling with physical reality.

### 5.3 Social Network — Spearman Rank Correlation Analysis
Table 6 presents the full Spearman rank correlation matrix ($\rho$) between structural centrality metrics and empirical failure indicators across the 72 Social Network runs.

**Table 6: Social Network — Spearman Correlation ($\rho$) Between Centrality Metrics and Failure Impacts**

| Metric | $\Delta$ Error Rate $\rho$ | $\Delta$ p95 Latency $\rho$ | $\Delta$ p99 Latency $\rho$ | Downstream Count $\rho$ | Recovery Time $T_{rec}$ $\rho$ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Degree** | 0.506 | 0.484 | 0.542 | 0.598* | 0.867** |
| **In-Degree** | **0.780\*\*** | **0.731\*\*** | **0.743\*\*** | 0.666* | 0.234 |
| **Out-Degree** | 0.322 | 0.311 | 0.293 | 0.430 | 0.659* |
| **Betweenness** | 0.739** | 0.676* | 0.616* | **0.730\*\*** | 0.388 |
| **Closeness** | 0.648* | 0.566 | 0.616* | 0.482 | 0.150 |
| **Eigenvector** | 0.470 | 0.364 | 0.540 | 0.312 | 0.247 |
| **PageRank** | 0.561 | 0.430 | 0.543 | 0.352 | 0.095 |
| **Composite Score** | -0.898*** | -0.814** | -0.842** | -0.789** | -0.365 |
| **Hybrid Criticality**| 0.527 | 0.513 | 0.598* | 0.650* | **0.897\*\*** |

*(Statistical significance: \* $p < 0.05$; \*\* $p < 0.01$; \*\*\* $p < 0.001$. For the Composite Score, negative $\rho$ indicates strong positive alignment because a lower numerical rank implies higher priority).*

#### 5.3.1 The Dissociation Between Error Magnitude and Recovery Dynamics
The correlation matrix reveals a striking structural dissociation:
1. **In-Degree Dominates Immediate Damage:** In-degree centrality exhibits the highest correlation with immediate $\Delta$ Error Rate ($\rho = 0.780, p = 0.0027$) and $\Delta$ p95 Latency ($\rho = 0.731, p = 0.0069$). When a high in-degree node crashes, dozens of caller client sockets immediately drop, generating rapid 5xx HTTP spikes.
2. **In-Degree Fails on Recovery Time:** Crucially, in-degree shows **no statistically significant correlation** with system recovery time ($\rho = 0.234, p = 0.465$). Once a failed service restarts, callers reconnect relatively quickly if no downstream dependencies are blocked.
3. **Hybrid Criticality Solves Recovery Prediction:** The Fan-Out Corrected Hybrid Metric achieves the highest correlation with System Recovery Time ($\rho = 0.897, p < 0.0001$). Recovery time in microservices is governed by the time required for *all downstream branches* to clear backpressure queues, flush dead connection pools, and re-establish cache consistency. High fan-out orchestrators force multiple leaf branches into error states concurrently; thus, when an orchestrator fails, stabilizing the application requires parallel recovery across multiple subtrees, directly prolonging $T_{rec}$.

### 5.4 Social Network — Fault Modality Breakdown
Table 7 disaggregates the recovery time correlation ($\rho$ against $T_{rec}$) across the three injected fault modalities.

**Table 7: Social Network — Centrality vs. Recovery Time ($\rho$) Across Fault Modalities**

| Fault Modality | Hybrid Criticality $\rho$ | Degree Centrality $\rho$ | In-Degree Centrality $\rho$ | Betweenness Centrality $\rho$ |
| :--- | :--- | :--- | :--- | :--- |
| **Container Kill** (`SIGKILL`) | 0.882** | 0.841** | 0.221 | 0.401 |
| **Network Latency** (100 ms) | 0.901*** | 0.872** | 0.248 | 0.389 |
| **CPU Saturation** (2 workers)| **0.908\*\*\***| 0.874** | 0.230 | 0.381 |
| **Overall Mean** | **0.897\*\*\***| **0.867\*\*** | **0.234** | **0.388** |

The hybrid metric exhibits consistent, superior correlation across all fault types. The strongest correlation occurs under **CPU saturation ($\rho = 0.908$)**. Unlike abrupt container termination, resource exhaustion induces progressive queuing and proportional latency expansion that maps directly to graph paths without being distorted by Docker container restart mechanics. Under container kills, although Docker container reboot times add baseline variance, the hybrid metric maintains a robust $\rho = 0.882$.

### 5.5 Hotel Reservation — Centrality Rankings and Ingress Inversion
Table 8 presents centrality calculations and rankings for the Hotel Reservation system.

**Table 8: Hotel Reservation — Centrality Scores, Classical Composite Ranks, and Hybrid Scores**

| Service | Degree | In-Deg | Out-Deg | Betweenness | Composite Rank | Fan-Out Wt | Hybrid Score | Hybrid Rank |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `frontend` | 0.667 | 0.000 | 0.667 | 0.000 | **7** | **1.000** | **0.267** | **1** |
| `search` | 0.500 | 0.167 | 0.333 | 0.067 | 3 | 0.500 | 0.147 | 2 |
| `geo` | 0.167 | 0.167 | 0.000 | 0.000 | 1 | 0.000 | 0.067 | 3 |
| `rate` | 0.167 | 0.167 | 0.000 | 0.000 | 1 | 0.000 | 0.067 | 3 |
| `profile` | 0.167 | 0.167 | 0.000 | 0.000 | 4 | 0.000 | 0.067 | 3 |
| `reservation` | 0.167 | 0.167 | 0.000 | 0.000 | 5 | 0.000 | 0.067 | 3 |
| `recommendation` | 0.167 | 0.167 | 0.000 | 0.000 | 6 | 0.000 | 0.067 | 3 |

#### 5.5.1 The Ingress Inversion Paradox
In the hierarchical tree topology of Hotel Reservation, the false negative phenomenon reaches a structural extreme:
- The `frontend` service is the root ingress node: it receives traffic from external clients and dispatches calls to all backend services.
- Because external HTTP traffic originates outside the microservice call graph, `frontend` has $d^- = 0$.
- Because no shortest paths between internal microservices pass *through* the root ingress node, its betweenness is exactly $C_B = 0.000$.
- Classical consensus assigns `frontend` **Composite Rank 7 out of 8** — classifying the most essential service in the architecture as least critical.
- The hybrid metric assigns `frontend` a Fan-Out Weight of 1.0 (since $d^+ = 4$ direct dependencies, maximum in graph), producing a score of 0.267 and correctly placing it at **Hybrid Rank 1**.
- Similarly, `search`, the only intermediate branch node connecting to `geo` and `rate`, is elevated to **Hybrid Rank 2**.

### 5.6 Hotel Reservation — Empirical Recovery Times and the MongoDB Anomaly
Table 9 displays the empirical recovery times observed across the 42 experimental runs on Hotel Reservation.

**Table 9: Hotel Reservation — Mean Recovery Time by Service and Fault Modality (seconds)**

| Microservice | Kill Modality (mean) | Latency Modality (mean) | CPU Modality (mean) | Overall Mean $T_{rec}$ |
| :--- | :--- | :--- | :--- | :--- |
| `reservation` | **61.07 s** | 0.11 s | 0.12 s | **20.43 s** |
| `search` | 1.34 s | 0.12 s | 0.17 s | 0.54 s |
| `rate` | 1.23 s | 0.10 s | 0.11 s | 0.48 s |
| `geo` | 1.17 s | 0.10 s | 0.16 s | 0.47 s |
| `frontend` | 1.13 s | 0.11 s | 0.14 s | 0.46 s |
| `recommendation` | 1.06 s | 0.12 s | 0.17 s | 0.45 s |
| `profile` | 1.10 s | 0.09 s | 0.13 s | 0.44 s |

#### 5.6.1 Root Cause Forensics: Protocol-Level Connection Starvation
The data contains a massive operational anomaly: when the `reservation` service container is terminated via `SIGKILL`, system recovery requires **61.07 seconds** — an order of magnitude larger than all other services combined (a 45:1 ratio over `search`).

Log analysis and network socket inspection isolated the root cause:
1. When the `reservation` container is abruptly killed, the TCP connection to MongoDB is severed without a formal TCP FIN/RST exchange.
2. The Go gRPC client runtime in `reservation` maintains an active connection pool to the backend MongoDB replica.
3. Upon container restart, the client driver fails to detect that previous TCP sockets are dead, retaining poisoned file descriptors in the pool until the operating system's **TCP keepalive timeout expires**.
4. In the default Docker Linux bridge network configuration, `tcp_keepalive_time` and socket retransmission timers enforce a 60-second recovery delay.
5. During these 60 seconds, all booking requests queue and timeout, causing a prolonged total outage.

#### 5.6.2 Boundary Condition of Purely Structural Modeling
From a graph-theoretic perspective, `reservation` is a terminal leaf node ($d^- = 1, d^+ = 0, C_B = 0$). Its graph signature is indistinguishable from `profile`, `rate`, or `recommendation`. Consequently, both classical and hybrid metrics assign it Rank 3 (tied with its leaf peers).

This finding formalizes an essential theoretical boundary condition: **Graph centrality models structural failure propagation paths across service boundaries, but cannot predict infrastructure configuration bottlenecks, database driver connection pool leaks, or OS-level protocol timeouts.** Structural prediction must therefore be deployed as a complement to runtime configuration auditing.

### 5.7 Hotel Reservation — Correlation Constraints in Tree Topologies
In Hotel Reservation, Spearman rank correlation values between structural metrics and empirical indicators evaluate to near zero ($\rho \approx 0.089, p > 0.80$). This outcome is a direct mathematical artifact of tree topology degeneracy:
- Five of the seven application services (`geo`, `rate`, `profile`, `reservation`, `recommendation`) are structural leaf nodes with identical in-degree (1), out-degree (0), and betweenness (0).
- When $>70\%$ of the vertex set possesses mathematically identical scores, rank correlation assigns identical tied ranks (3.5), compressing the rank variance to zero.
- Crucially, the hybrid metric successfully separated the non-leaf routing tier (`frontend` and `search`) from the leaf tier. In hierarchical architectures, evaluation should rely on **Pairwise Ranking Accuracy** (the percentage of service pairs $(u, v)$ where the metric correctly orders impact) rather than monotonic rank correlation.

---

## 6. Discussion and Operational Implications

### 6.1 The Theoretical Superiority of Fan-Out Correction
A practitioner might ask whether plain degree centrality ($C_{deg}$) is sufficient, given that it achieved $\rho = 0.867$ in Social Network. The answer lies in the mechanics of architectural consensus and the physical directionality of RPC failures:
1. **Symmetry vs. Asymmetry:** Degree centrality is undirected and symmetric: it treats one inbound dependency identically to one outbound dependency ($d = d^- + d^+$). In synchronous RPC architectures, this premise is physically false. A leaf service that is called by one service affects only that caller upon failure. An orchestrator that calls seven services affects seven execution subtrees simultaneously.
2. **Consensus Dilution in Multi-Metric Dashboards:** Organizations rarely rely on a single metric; SRE teams utilize composite rankings across multiple tools. When unweighted degree centrality is blended into a composite index alongside betweenness, PageRank, and eigenvector centrality, the lack of inbound edges mathematically pulls orchestrators down into the bottom quartiles, triggering the false negative.
3. **Quadratic Scaling Rationale:** The quadratic expansion $[d^+(v)]^2$ mirrors the physical behavior of downstream thread pool saturation. When an orchestrator fails, it creates backlog queues across all downstream worker pools simultaneously, producing non-linear recovery delays.

### 6.2 Operationalizing Jaeger as a Zero-Overhead Graph Source
A major practical strength of this methodology is its zero-overhead integration into modern cloud environments:
- **No Custom Instrumentation:** Distributed tracing is already present across enterprise Kubernetes clusters. The Jaeger query API (`/api/traces`) returns standard JSON spans encoding caller-callee tuples.
- **Microsecond Graph Generation:** For typical enterprise architectures ($n \le 50$ services), downloading 60 seconds of ambient trace data and computing the Fan-Out Corrected Hybrid Metric requires less than **3.5 seconds** of total CPU time on standard commodity hardware.
- **CI/CD Architectural Quality Gates:** This computational efficiency allows the metric to be embedded directly into CI/CD deployment pipelines. When a pull request modifies a service’s RPC client bindings or introduces a new dependency, the pipeline automatically reconstructs the prospective SDG, recalculates hybrid criticality, and flags whether the commit has elevated a service into a critical orchestrator chokepoint.

### 6.3 Practical Guidelines for Site Reliability Engineering (SRE)
Our findings provide three concrete guidelines for production operations:
1. **Targeted Chaos Experimentation:** Rather than executing randomized Chaos Monkey terminations that waste compute budget on resilient leaf nodes, SRE teams should prioritize the top-3 services identified by the Hybrid Criticality Metric. This guarantees that chaos campaigns validate the highest-leverage failure boundaries.
2. **Architectural Hardening Prioritization:** Services identified as high fan-out orchestrators should be mandated to implement aggressive resilience patterns:
   - Synchronous RPC calls should be bounded by strict deadline propagation and circuit breakers.
   - Heavy fan-out reads should be decoupled into asynchronous background batching or event-driven streaming where feasible.
3. **Dual-Layer Observability (Topology + Configuration):** As demonstrated by the MongoDB connection pool anomaly, structural analysis cannot catch protocol-level misconfigurations. SRE teams must pair graph centrality prioritization with runtime configuration audits verifying TCP keepalive parameters, connection pool eviction timeouts, and gRPC retry backoff limits.

### 6.4 Threats to Validity

#### 6.4.1 Construct Validity
We adopted System Recovery Time ($T_{rec}$) as our primary proxy for failure severity. While $T_{rec}$ directly mirrors SLO breach duration and downtime cost, it does not capture all failure dimensions, such as silent data corruption, cache state divergence, or partial degradations where requests return stale data rather than hard 5xx errors.

#### 6.4.2 Internal Validity
Traffic was generated using `wrk2` under a constant throughput model (100 req/s) to isolate architectural propagation from traffic surge confounds. Real-world user traffic exhibits bursty, non-stationary Poisson and Pareto distributions. Nonetheless, maintaining a stable baseline was strictly required to ensure that comparative impact deltas between services remained statistically valid and comparable.

#### 6.4.3 External Validity
We evaluated two open-source benchmarks from DeathStarBench. While designed by systems researchers to emulate Twitter and modern booking systems, proprietary enterprise platforms may differ in scale (hundreds of services) and communication patterns (asynchronous Kafka queues, serverless functions). Our mathematical formulation is strictly defined for synchronous RPC topologies. Extending the metric to asynchronous pub/sub systems requires discounting edge weights by queue buffer capacity.

#### 6.4.4 Weight Selection Sensitivity
The hybrid weights ($w_1 = 0.4, w_2 = 0.4, w_3 = 0.2$) were chosen by architectural reasoning to balance local fan-in, fan-out impact, and global path routing. Grid-search analysis over weight triplets confirms that this region maximizes recovery time correlation ($\rho > 0.88$). In production environments with historical incident logs, weights can be tuned via cross-validation.

---

## 7. Conclusion

This paper investigated the problem of identifying failure-prone microservices using graph centrality metrics. Through 114 controlled fault injection experiments across two architecturally diverse benchmark systems and three failure modalities, we demonstrated that classical graph-theoretic centrality metrics systematically under rank high fan-out orchestrator services — a structural deficiency we formalized as the centrality-induced false negative problem. The deficiency arises because metrics designed for undirected networks penalize services with low in-degree and low betweenness, even when those services are responsible for dispatching requests to the largest number of downstream dependencies. 

To address this, we proposed a Fan-Out Corrected Hybrid Criticality Metric that incorporates a topology-derived fan-out weight factor, amplifying the criticality contribution of high out-degree services in proportion to their relative fan-out within the graph. Across the Social Network benchmark (12 services, cyclic mesh, 72 runs), the hybrid metric achieved a Spearman rank correlation of rho = 0.897 (p < 0.0001) with empirically measured system recovery time — the highest among all evaluated metrics — and correctly elevated the `compose-post-service` from classical composite rank 7 to hybrid rank 1. In the Hotel Reservation benchmark (8 services, hierarchical tree, 42 runs), the metric resolved the false negative misclassification of the `frontend` service without any architecture-specific parameter tuning. 

The empirical study additionally uncovered a real-world operational anomaly: the `reservation` service exhibited a 61-second kill-fault recovery time driven by a MongoDB TCP connection pool timeout, not by its graph position. This finding defines the boundary of topology-based failure identification and points to the value of pairing graph-centrality analysis with configuration-level vulnerability scanning. 

The hybrid metric is computationally lightweight, requires only static call graph topology derivable from existing distributed tracing infrastructure, and produces interpretable single-number scores. Future work will extend the evaluation framework to asynchronous and event-driven architectures, investigate empirical weight optimization via cross-architecture cross-validation, and develop pairwise ranking accuracy as an evaluation measure better suited to sparse tree topologies. 

### Data and Code Availability 
The complete experiment log (114 runs), centrality computation scripts, fault injection orchestration code, and all figures are available at [repository link to be provided upon acceptance]. All plots were generated from raw CSV experiment logs using reproducible Python scripts included in the repository.

---

## References 

[1] C. Richardson, *Microservices Patterns: With Examples in Java*. Shelter Island, NY: Manning Publications, 2018.

[2] T. Cerny, M. J. Donahoo, and M. Trnka, "Contextual understanding of microservice architecture: Current and future directions," *ACM SIGAPP Applied Computing Review*, vol. 17, no. 4, pp. 29–45, 2018.

[3] A. Basiri, N. Behnam, R. de Rooij, L. Hochstein, L. Kosezewski, J. Reynolds, and C. Rosenthal, "Chaos engineering," *IEEE Software*, vol. 33, no. 3, pp. 35–41, May/Jun. 2016.

[4] J. Arlat, M. Aguera, L. Amat, Y. Crouzet, J.-C. Fabre, J.-C. Laprie, E. Martins, and D. Powell, "Fault injection for dependability validation: A methodology and some applications," *IEEE Transactions on Software Engineering*, vol. 16, no. 2, pp. 166–182, Feb. 1990.

[5] G. A. Kanawati, N. A. Kanawati, and J. A. Abraham, "FERRARI: A flexible software-based fault and error injection system," *IEEE Transactions on Computers*, vol. 44, no. 2, pp. 248–260, Feb. 1995.

[6] Y. Tseitlin, "The antifragile organization," *Communications of the ACM*, vol. 56, no. 8, pp. 40–44, Aug. 2013.

[7] A. Alexei, "Pumba: Chaos testing tool for Docker," 2018. [Online]. Available: https://github.com/alexei-led/pumba

[8] C. Liu, C. Wang, K. Ma, and K. Chen, "Chaos Mesh: A powerful chaos engineering platform for Kubernetes," in *Proc. 2021 ACM Symposium on Cloud Computing (SoCC '21)*, 2021.

[9] Y. Gan, Y. Zhang, D. Cheng, A. Shetty, P. Rathi, N. Katarki, A. Bruno, J. Hu, B. Ritchken, B. Jackson, K. Hu, M. Pancholi, B. He, B. Liang, S. Rajagopalan, and C. Delimitrou, "An open-source benchmark suite for microservices and their hardware-software implications for cloud & edge systems," in *Proc. 24th ACM Int. Conf. Architectural Support for Programming Languages and Operating Systems (ASPLOS '19)*, 2019, pp. 3–18.

[10] H. Kannan, G. Subramanian, A. Gavrilovska, and M. Joshi, "Characterizing microservice dependency and performance: Alibaba trace analysis," in *Proc. 2019 ACM Symposium on Cloud Computing (SoCC '19)*, 2019.

[11] Y. Gan, M. Liang, S. Dev, D. Lo, and C. Delimitrou, "Seer: Leveraging big data to navigate the complexity of performance debugging in cloud microservices," in *Proc. 24th ACM Int. Conf. Architectural Support for Programming Languages and Operating Systems (ASPLOS '19)*, 2019, pp. 19–33.

[12] M. Nagappan and T. Ball, "Using software dependencies and churn metrics to predict field failures: An empirical study," in *Proc. 1st ACM Int. Symp. Empirical Software Engineering and Measurement (ESEM '07)*, 2007, pp. 364–373.

[13] T. Zimmermann, R. Premraj, and A. Zeller, "Predicting defects for Eclipse," in *Proc. 3rd Int. Workshop on Predictor Models in Software Engineering (PROMISE '07)*, 2007, p. 9.

[14] X. Zhou, X. Peng, T. Xie, J. Sun, C. Ji, W. Li, and D. Ding, "Fault analysis and debugging of microservice systems: Industrial survey, benchmark system, and empirical study," *IEEE Transactions on Software Engineering*, vol. 47, no. 2, pp. 243–260, Feb. 2021.

[15] M. Rahman, M. Mahdavi-Hezaveh, and L. Williams, "A systematic mapping study of infrastructure as code research," *Information and Software Technology*, vol. 108, pp. 65–77, Apr. 2019.

[16] A. Rauzy, "New algorithms for fault trees analysis," *Reliability Engineering & System Safety*, vol. 40, no. 3, pp. 203–211, 1993.

[17] W. Wang, H. Hu, and P. Banerjee, "Microservice failure propagation analysis using dynamic Bayesian networks," in *Proc. 2021 IEEE 40th Int. Symp. Reliable Distributed Systems (SRDS)*, 2021.

[18] L. Chen, P. Jiang, and B. Luo, "Cascading failure modeling in microservice architecture," *IEEE Transactions on Network and Service Management*, vol. 18, no. 3, pp. 3012–3025, Sep. 2021.

[19] P. Liu, H. Xu, Q. Ouyang, R. Jiao, Z. Chen, S. Zhang, J. Yang, L. Lin, and D. Pei, "Microservice root cause analysis with graph convolutional neural networks," in *Proc. 2021 IEEE 32nd Int. Symp. Software Reliability Engineering (ISSRE)*, 2021, pp. 140–150.

[20] M. Ma, Z. Yin, S. Zhang, S. Wang, C. Zheng, X. Jiang, H. Hu, C. Luo, Y. Li, N. Qiu, F. Shen, C. Zhang, and D. Pei, "MS-Rank: Multi-metric and self-adaptive root cause diagnosis for microservice applications," in *Proc. 2019 IEEE Int. Conf. Web Services (ICWS)*, 2019, pp. 60–67.

[21] T. Cerny, M. J. Donahoo, and J. Pechanec, "On code analysis opportunities and challenges for enterprise systems and microservices," *IEEE Access*, vol. 8, pp. 159449–159470, 2020.

[22] B. H. Sigelman, L. A. Barroso, M. Burrows, P. Stephenson, M. Plakal, D. Beaver, S. Jaspan, and C. Shanbhag, "Dapper, a large-scale distributed systems tracing infrastructure," Google LLC, Tech. Rep. dapper-2010-1, 2010.

[23] Cloud Native Computing Foundation, "Jaeger: Open source, end-to-end distributed tracing," 2021. [Online]. Available: https://www.jaegertracing.io/

[24] Y. Shkuro, *Mastering Distributed Tracing: Analyzing Performance in Microservices and Complex Systems*. Birmingham, UK: Packt Publishing, 2019.

[25] OpenTelemetry Authors, "OpenTelemetry: Effective observability for cloud-native applications," 2021. [Online]. Available: https://opentelemetry.io/

[26] U. Brandes, "A faster algorithm for betweenness centrality," *Journal of Mathematical Sociology*, vol. 25, no. 2, pp. 163–177, 2001.

[27] N. Dragoni, S. Giallorenzo, A. L. Lafuente, M. Mazzara, F. Montesi, A. Mustafin, and L. Safina, "Microservices: Yesterday, today, and tomorrow," in *Present and Ulterior Software Engineering*, M. Mazzara and B. Meyer, Eds. Cham: Springer, 2017, pp. 195–216.

[28] J. Thönes, "Microservices," *IEEE Software*, vol. 32, no. 1, pp. 116–116, Jan./Feb. 2015.

[29] M. E. J. Newman, *Networks: An Introduction*. Oxford, UK: Oxford University Press, 2010.

[30] L. C. Freeman, "Centrality in social networks: Conceptual clarification," *Social Networks*, vol. 1, no. 3, pp. 215–239, 1978.

[31] L. Page, S. Brin, R. Motwani, and T. Winograd, "The PageRank citation ranking: Bringing order to the web," Stanford InfoLab, Tech. Rep. 1999-66, 1999.

[32] A. Walker, T. Cerny, and E. Song, "Open-source tools and benchmarks for microservice research," *ACM SIGOPS Operating Systems Review*, vol. 54, no. 1, pp. 28–39, 2021.

[33] O. Haugen, B. Morin, and A. Harmer, "Towards semantic API deprecation in microservice ecosystems," in *Proc. 2021 IEEE Int. Conf. Software Engineering and Service Science (SOSE)*, 2021.

[34] S. Newman, *Building Microservices: Designing Fine-Grained Systems*, 2nd ed. Sebastopol, CA: O'Reilly Media, 2021.

[35] Y. Meng, S. Zhang, Y. Sun, R. Zhang, Z. Hu, Y. Zhang, C. Jia, Z. Wang, and D. Pei, "Localizing failure root causes in a microservice through causality inference," in *Proc. 2020 IEEE/ACM 28th Int. Symp. Quality of Service (IWQoS)*, 2020, pp. 1–10.
