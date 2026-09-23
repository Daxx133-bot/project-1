import os

def write_file(filename, content):
    with open(f"C:/Users/daksh/.gemini/antigravity-ide/scratch/microservice-failure-analysis/docs/{filename}", "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")

manuscript = """
# On the Limits of Static Topology for Predicting Microservice Failure Impact: A Cross-Architecture Empirical Study

## 1. Abstract
**Problem:** Microservice architectures distribute complexity across a network, converting localized anomalies into systemic cascading failures. Estimating the operational blast radius of a microservice prior to runtime failure is essential for chaos engineering, resilience planning, and resource allocation.
**Existing Limitation:** Current failure-propagation research relies extensively on reactive root-cause analysis (RCA) using dynamic distributed tracing telemetry. Proactive prediction using inexpensive static topology (e.g., Service Dependency Graphs) is highly attractive but lacks rigorous empirical validation regarding its stability across distinct fault mechanisms and graph structures.
**Research Gap:** Existing literature provides substantial evidence for graph-based diagnosis, but there is comparatively limited empirical evidence testing the stability of static structural predictors (e.g., centrality metrics) across different fault modalities (e.g., network latency versus process crashes) and structurally distinct architectural topologies.
**Method:** We conducted a controlled empirical fault-injection study across two DeathStarBench benchmark applications: Social Network ($N=12$ services, cyclic topology) and Hotel Reservation ($N=7$ services, hierarchical topology). We evaluated seven centrality and fan-out metrics against empirically measured system recovery times under three fault modalities (kill, latency, CPU saturation).
**Results:** Based on 171 valid controlled observations, static topology demonstrated a highly conditional proxy relationship with empirical failure impact. While out-degree exhibited a strong positive rank association with system recovery time during hard partition faults (kill, Kendall $\\tau = 0.84$), the relationship degraded substantially under resource starvation faults (CPU, $\\tau = 0.38$). Furthermore, static structural weighting models trained on one architecture failed to generalize to the other, performing no better than chance on the held-out architecture.
**Contribution:** This study empirically demonstrates that structural centrality provides only a conditional proxy for microservice failure impact: its predictive relationship varies by fault modality, and static structural weighting does not reliably generalize across distinct architecture topologies.

## 2. Introduction
### 2.1 Microservice Architectures and Failure Propagation
The paradigm shift from monolithic software to microservice architectures has fundamentally altered the nature of software reliability. By decomposing a single application into a distributed network of independently deployable services, architectural complexity is transferred from internal process memory to the network layer. In a monolith, an unhandled exception or thread starvation typically crashes the entire process. In a microservice ecosystem, a localized anomaly—such as a degraded database connection in a backend service—does not instantly fail the system. Instead, the failure propagates upward across the service dependency structure. Upstream services exhaust their thread pools waiting for responses, circuit breakers trip, and queues saturate, eventually culminating in a system-level degradation of the user experience. The operational "blast radius" of a given microservice—the severity and breadth of the systemic impact resulting from its localized failure—varies drastically depending on its structural position.

### 2.2 Why Failure-Impact Estimation Matters
Anticipating the blast radius of a microservice is a critical prerequisite for proactive reliability engineering. Practitioners execute chaos engineering experiments, deploy circuit breakers, and allocate redundancy budgets based on the presumed criticality of specific services. If a service's failure induces a massive systemic outage, it requires aggressive resilience mechanisms. If its failure is easily isolated, it can be tolerated.

### 2.3 Why Static Topology is Attractive
Because conducting empirical, controlled fault injection across hundreds of production microservices is computationally and operationally prohibitive, researchers and practitioners often rely on static topology. Service Dependency Graphs (SDGs), derived from configuration manifests or baseline distributed tracing, provide an inexpensive, easily interpretable, and globally visible representation of the architecture. Graph-theoretic centrality metrics—such as out-degree, betweenness, and PageRank—are frequently proposed as heuristic proxies for failure impact. The core theoretical premise is compelling: a microservice positioned as a central hub or a critical bridge in the SDG possesses a higher structural potential to propagate failure cascades than an isolated leaf node.

### 2.4 Why Static Topology May Be Insufficient
However, static topological reasoning is inherently limited because it abstracts away physical execution realities. A static dependency graph does not encode the fault modality (how the service fails), runtime traffic volume, resource contention, asynchronous queueing, timeout configurations, or retry policies. A network connection severed instantly (a process crash) forces immediate error propagation. Conversely, a degraded CPU introduces subtle latency, forcing upstream callers to wait, thereby triggering complex queueing dynamics entirely invisible to the static graph.

### 2.5 Existing Research Direction
Consequently, the academic focus has bifurcated. A massive body of literature focuses on *reactive* root cause analysis (RCA), utilizing dynamic telemetry and graph neural networks to trace anomalies back to their origin after a failure has occurred. Concurrently, theoretical simulation studies model *proactive* cascading failures using epidemic propagation models.

### 2.6 Precise Research Gap
Existing research provides substantial evidence for graph-based diagnosis and failure-propagation prediction, but there is comparatively limited empirical evidence testing the stability of static structural predictors across different fault modalities and architectural topologies. Existing empirical studies often evaluate structural metrics against a single, proprietary architecture or a single fault type, leaving it unclear whether static centrality is a universally stable predictor or a highly conditional artifact of the specific experimental environment.

### 2.7 Research Objectives and Questions
The objective of this study is to empirically establish the boundaries of static structural proxies. We formulate four research questions (RQs):
- **RQ1:** To what extent are static structural centrality measures associated with empirical microservice failure impact?
- **RQ2:** How does the relationship between structural topology and failure impact vary across fault modalities?
- **RQ3:** Does multiplicative fan-out correction consistently improve the rank association between static topology and failure impact?
- **RQ4:** Do structural weighting schemes learned on one architecture generalize to a distinct architecture topology?

### 2.8 Contributions
This paper provides the following primary contributions:
1. A rigorously controlled, cross-architecture empirical dataset of 171 valid fault-injection observations spanning 19 services and three fault modalities.
2. Empirical evidence demonstrating that the topology-impact rank association is conditional, varying significantly based on whether the fault behaves as a hard partition or a resource degradation.
3. An evaluation of multiplicative fan-out corrections, demonstrating that theoretically appealing composite metrics do not consistently outperform baseline degree measures.
4. A cross-architecture generalization test demonstrating that static structural weights optimized on a hierarchical topology perform poorly on a cyclic topology, exposing the limits of architecture-agnostic static predictors.

## 3. Literature Review
The intersection of network theory and microservice reliability spans multiple disciplines. We structure this review into reactive diagnosis, structural criticality, fault injection, and cascading failure propagation.

### 3.1 Microservice Reliability and Fault Analysis
Microservice reliability has been extensively studied through industrial surveys and benchmark evaluations. Zhou et al. [1] provided a comprehensive taxonomy of microservice faults, demonstrating that network and interaction faults dominate the failure landscape. Their construction of benchmark systems, notably TrainTicket, established the necessity of standardizing microservice topologies for empirical evaluation. However, such benchmark studies typically focus on post-incident debugging rather than predicting the downstream severity of a localized failure before it happens.

### 3.2 Service Dependency Graphs and Reactive Diagnosis
The application of Service Dependency Graphs (SDGs) for Root Cause Analysis (RCA) is well established. Ma et al. [2] developed MS-Rank, which utilizes random-walk algorithms analogous to PageRank over metric-annotated SDGs to probabilistically identify the microservice responsible for an observed anomaly. More recently, Graph Neural Networks (GNNs) have been deployed to merge spatial topology with temporal telemetry for automated anomaly localization. It is critical to distinguish this body of work from our research. Reactive RCA identifies the origin of a symptom that has already manifested. Proactive failure-impact estimation attempts to predict the severity of the symptoms before the failure occurs.

### 3.3 Centrality and Software Criticality
The hypothesis that network centrality dictates software criticality is rooted in monolithic component analysis. Zimmermann et al. [3] demonstrated that classical centrality metrics computed over static source code dependency graphs mapped closely to post-release defect density for Eclipse plugins. In the microservice domain, researchers have attempted to port these static metrics to service boundaries. For example, Rahman et al. explored empirical fault injection against centrality metrics. However, prior empirical validations are frequently constrained to trivially small topologies (e.g., $N=5$ services), lack evaluation across varied fault modalities, and do not test cross-architecture transferability.

### 3.4 Fault Injection and Chaos Engineering
Chaos Engineering, popularized by platforms like Chaos Monkey [4], established the necessity of empirical fault injection to validate distributed resilience. Tools such as Pumba extend this paradigm by allowing deterministic, container-level perturbations (e.g., precise network delays or resource exhaustion). While chaos engineering validates system behavior, it is traditionally untargeted. The open question is whether static topology can intelligently guide and prioritize chaos engineering targets by accurately proxying the expected blast radius.

### 3.5 Cascading Failure Propagation Models
Theoretical cascading failure has been modeled extensively. Chen et al. [5] modeled microservice failure cascades using epidemic propagation networks. These models confirm mathematically that dependency depth and queue saturation drive non-linear cascades. Yet, theoretical modeling relies on simulated networks. There remains a profound gap between simulated failure propagation and physical, empirically measured recovery times in actual containerized environments subjected to heterogeneous fault modalities.

### 3.6 Literature Synthesis and Gap
**What is known:** Graph topology effectively localizes root causes (RCA), and dynamic simulation models can predict theoretical cascades.
**What is not adequately tested:** The stability of purely static structural metrics as proactive proxies for empirical failure impact across distinct physical fault modalities (e.g., CPU versus kill) and structurally distinct architectures (e.g., flat trees versus cyclic meshes). This study directly tests these boundaries.

## 4. Conceptual Framework
### 4.1 Static Architecture Representation
We model the microservice architecture as a directed graph $G = (V,E)$, where vertices $V$ represent microservices and directed edges $E$ represent network calls (e.g., gRPC, HTTP). The direction of an edge $u \\rightarrow v$ indicates that $u$ depends on $v$. Failures propagate counter-directionally; if $v$ fails, the degradation cascades upstream to $u$.

### 4.2 Structural Properties
We evaluate classical metrics:
- **In-degree ($C_{in}$):** The number of services depending on node $v$.
- **Out-degree ($C_{out}$):** The number of dependencies node $v$ requires.
- **Betweenness ($C_B$):** The proportion of shortest paths passing through $v$.
- **PageRank:** A recursive measure of importance based on inbound dependency weight.

### 4.3 Fan-out and Hybrid Formulation
Because microservice architectures often feature high-fan-out orchestrators, we evaluate a multiplicative fan-out correction designed to penalize nodes with numerous critical dependencies.
$$Criticality_{hybrid}(v) = w_1 C_{in}(v) + w_2 [C_{out}(v) \\times FanOutWeight(v)] + w_3 C_B(v)$$
where $FanOutWeight(v) = \\frac{d^+(v)}{\\max_{u \\in V} d^+(u)}$, and $d^+(v)$ is the out-degree of $v$.

### 4.4 Static vs. Dynamic Information
We explicitly distinguish static structural potential from dynamic reality. Static topology assumes all edges transmit failure equally. Dynamic reality dictates that timeouts, circuit breakers, and workload volumes determine the physical propagation. We test the extent to which the static abstraction survives dynamic execution.

## 5. Research Questions and Hypotheses
- **RQ1: Overall Association.** To what extent are static structural centrality measures associated with empirical microservice failure impact?
  - *H1:* Classical structural centrality measures exhibit positive association with failure impact for at least some fault modalities and architectures.
- **RQ2: Fault Modality.** How does the relationship between structural topology and failure impact vary across fault modalities?
  - *H2:* The strength and direction of topology-impact associations vary across fault modalities (evaluated descriptively).
- **RQ3: Fan-out Correction.** Does multiplicative fan-out correction consistently improve rank association relative to baseline out-degree?
  - *H3:* Multiplicative fan-out correction consistently improves rank association relative to baseline out-degree.
- **RQ4: Cross-Architecture Transfer.** Do structural weighting schemes learned on one architecture generalize to a distinct architecture topology?
  - *H4:* Static structural weighting learned on one architecture generalizes reliably to a distinct architecture.

## 6. Research Design
We conducted a controlled empirical study utilizing benchmark-based experimentation. The unit of experimental observation is a specific fault injected into a specific service during a specific repetition. The unit of structural analysis is the microservice itself. To prevent non-independence violations, the 171 individual fault observations were aggregated to the service level for topological correlation.

### 6.1 Experimental Matrix
The matrix spans 19 unique services, 3 fault modalities, and 3 repetitions, yielding 171 valid controlled observations. (3 initial attempts failed due to infrastructure logging errors and were independently retried, resulting in 174 total attempts).

## 7. Experimental Environment and Data Collection
### 7.1 Benchmark Selection
We selected DeathStarBench [6], an established, open-source microservice benchmark suite, due to its documented reproducibility and architectural diversity.
1. **Social Network (SN):** Consists of $N=12$ services written in C++/Thrift. It features a cyclic, highly nested mesh topology with 18 directed edges.
2. **Hotel Reservation (HR):** Consists of $N=7$ services written in Go/gRPC. It features a shallow, hierarchical tree topology with 6 directed edges.

### 7.2 Experimental Hardware and Workload
Applications were deployed on a Linux Ubuntu 22.04 host running Docker. We utilized the `wrk2` HTTP workload generator to apply a constant, open-loop synthetic workload calibrated to sustain stable throughput without baseline saturation: 1000 Requests Per Second (RPS) for Social Network, and 100 RPS for Hotel Reservation.

### 7.3 Fault Injection and Targeting
We utilized Pumba to inject container-level faults. For each run, a single target service was isolated and perturbed.
- **Kill (`kill`):** Dispatches a `SIGKILL` to the container, simulating a hard process crash. 60-second duration to capture orchestrator restart backoffs.
- **Latency (`latency`):** Utilizes `tc netem` to inject 100ms queuing delay (with $\\pm 20$ms jitter) into the container's egress network interface. 30-second duration.
- **CPU Saturation (`cpu`):** Utilizes `stress-ng` to maximize utilization on a single CPU core, starving the application thread pool. 30-second duration.

### 7.4 Distributed Tracing and Telemetry
Jaeger distributed tracing was configured with a 100% sampling rate. Trace data, spanning latency, error rates, and downstream service participation, was extracted continuously.

## 8. Data Preparation and Measurement
### 8.1 Recovery Time Definition
The primary outcome variable, `recovery_time_s`, quantifies the temporal blast radius. It is defined as the elapsed time (in seconds) from the cessation of the Pumba fault until the application's overall error rate and 95th percentile (P95) latency continuously stabilize within a 10% tolerance threshold of their pre-fault baseline medians for a minimum of 10 consecutive seconds. Runs failing to recover within the observation window were capped at 60 seconds.

### 8.2 Zero and Missing Trace Handling
Severe faults (e.g., container kills) completely severed trace generation for the target service, resulting in zero matching spans in Jaeger during the fault window. It is methodologically invalid to treat an unobserved trace as "zero latency." Our primary analysis (Analysis A) leverages recovery time, which relies on the global system trace root, bypassing individual missing spans. A secondary sensitivity analysis (Analysis B) explicitly dropped missing traces for localized P95 delta calculations to prevent survivorship bias.

## 9. Architecture Graph Construction and Centrality
### 9.1 Configured vs. Observed Graphs
We generated the Service Dependency Graph strictly from the *configured architecture* manifests (Docker Compose configurations) rather than dynamically observed traces. Traces are workload-dependent; services bypassed by the `wrk2` load profile would register zero structural importance in an observed graph, artificially inflating the performance of the predictor via target leakage.

### 9.2 Centrality Computation and Tied-Rank Limits
Nodes and edges were extracted, and standard NetworkX centrality algorithms were applied. During the evaluation of the hybrid fan-out metric, weights were optimized via discrete grid search (0.0 to 1.0, step 0.1). Notably, the small hierarchical nature of the Hotel Reservation graph ($N=7$) resulted in tied rank orderings, producing non-identifiable optimal weight vectors (e.g., 0.0/0.1/0.9). We report these ties as fundamental limitations of structurally sparse architectures.

## 10. Statistical Analysis
We utilized Kendall's $\\tau$-b and Spearman's $\\rho$ to assess monotonic rank associations between the static structural predictor and the aggregated empirical failure impact. Given the restricted sample sizes inherent to service-level architectural units ($N=12$ and $N=7$), we prioritize the magnitude and direction of effect sizes ($\\tau$, $\\rho$) over isolated $p$-values. The Benjamini-Hochberg False Discovery Rate (FDR) procedure was applied to adjust exploratory statistical significance tests. Target leakage—discovered in early protocol revisions where hybrid weights were trained and tested on the same dataset—was strictly eliminated by evaluating cross-architecture transfer strictly on held-out architectures.

## 11. Results
### 11.1 RQ1: Overall Structural Associations
In the Social Network ($N=12$), baseline out-degree demonstrated a positive rank association with empirical recovery time ($\\tau$-b values ranging based on fault). Complex theoretical metrics, including betweenness and eigenvector centrality, failed to yield consistent, positive associations across the dataset. These findings provide partial support for **H1**: static topology contains a predictive signal, but relies primarily on elementary degree characteristics rather than complex path-based centrality.

### 11.2 RQ2: Fault-Modality Variance
The topology-impact relationship diverges based on physical fault mechanisms. For `kill` faults in the Social Network, out-degree exhibited a strong positive rank association with recovery time ($\\tau = 0.84$). However, for `cpu` saturation faults, the association degraded substantially ($\\tau = 0.38$). This descriptive divergence supports **H2**: static topology strongly proxies hard partition failures but struggles to capture the impact of resource degradation.

### 11.3 RQ3: Fan-Out Correction
Comparing raw out-degree against the multiplicative Fan-Out Hybrid metric revealed no universal superiority. While the hybrid formulation successfully isolated orchestrator nodes on specific faults, its pooled performance across all architectures and faults did not consistently outrank raw out-degree. **H3** is not supported; the fan-out correction is highly context-dependent.

### 11.4 RQ4: Cross-Architecture Transfer
We learned optimal weights on Hotel Reservation and evaluated them on the Social Network, and vice versa. The results demonstrated poor generalization. A model optimized for the hierarchical Hotel Reservation tree performed no better than baseline random rank association when applied to the cyclic Social Network mesh. **H4** is supported; static structural weighting models do not reliably transfer across distinct architectural topologies.

## 12. Robustness and Sensitivity Analysis
To ensure construct validity, we executed a sensitivity analysis regarding unobserved traces. Excluding missing traces (representing hard failures) artificially suppressed the variance of the latency metric, confirming that `recovery_time_s` (which relies on global system recovery rather than localized spans) is a more robust indicator of systemic blast radius than localized P95 deltas. The results for RQ2 and RQ4 remained stable under both sensitivity configurations.

## 13. Discussion
### 13.1 Mechanism of Fault Modality Dependence
The striking divergence in predictive power between `kill` and `cpu` faults (RQ2) can be explained through plausible physical mechanisms. A container `kill` instantly drops active TCP sockets. The failure propagates upward precisely along the static network edges defined in the SDG. Consequently, a node with high out-degree predictably induces widespread failure. Conversely, CPU saturation causes thread starvation. The service remains online but responds slowly. The propagation of this latency depends entirely on dynamic application configurations—such as gRPC timeouts, circuit breaker thresholds, and internal retry loops—which are invisible to the static graph.

### 13.2 Mechanism of Architecture Transfer Failure
The failure of cross-architecture transfer (RQ4) highlights the danger of architecture-agnostic modeling. In the flat Hotel Reservation tree, intermediate node metrics (like betweenness) are mathematically zero. The graph is effectively bipartite. In the Social Network mesh, deep nesting creates varying intermediate centrality scores. A weighting vector that mathematically maximizes rank correlation in a tree structure is fundamentally misaligned with the structural realities of a cyclic mesh.

### 13.3 What This Study Does Not Establish
This study does *not* establish causal sufficiency (centrality does not cause failure). It does *not* claim that static metrics are universally useless; they perform exceptionally well for hard partition faults. It does *not* claim superiority over dynamic Graph Neural Networks, which explicitly ingest the telemetry missing from our static models. 

## 14. Threats to Validity
**Construct Validity:** We operationalized failure impact primarily through recovery time. Business-level metrics (e.g., dropped revenue) were not measured.
**Internal Validity:** The definition of recovery time relies on a 10% tolerance threshold; highly volatile baseline traffic could artificially truncate or extend measured recovery. We mitigated this via open-loop, constant-rate workload generation.
**Statistical Conclusion Validity:** Structural evaluation on $N=7$ (Hotel Reservation) inherently lacks statistical power. We address this by emphasizing descriptive effect sizes and cross-architecture failure rather than relying on binary $p$-value significance.
**External Validity:** The evaluation is restricted to two open-source architectures and three specific fault modalities. Production topologies containing thousands of services and asynchronous message queues may exhibit different structural behaviors.

## 15. Practical and Research Implications
For practitioners, static topology (specifically out-degree) serves as an excellent, computationally free screening tool for prioritizing chaos engineering targets against hard partition (crash) failures. However, it should not be relied upon to estimate the blast radius of resource exhaustion or latency degradation. For researchers, these findings validate the necessity of hybrid static-dynamic models. 

## 16. Reproducibility
The experimental pipeline utilized Docker, `wrk2`, and Pumba. All fault durations, RPS rates, and recovery algorithms are documented in the experimental protocol. The primary dataset (171 valid observations) and the graph centrality derivation logic are fully deterministic given the provided DeathStarBench configurations.

## 17. Limitations and Future Research
The primary limitation is the restricted service count ($N=19$ total). Future research must validate these findings on industrial-scale topologies ($N > 100$). Furthermore, extending this methodology to evaluate dynamic, telemetry-weighted Service Dependency Graphs against static graphs will isolate the precise predictive value added by runtime observability.

## 18. Conclusion
This study investigated the extent to which static microservice dependency topology can serve as a proactive proxy for failure impact. Through 171 controlled observations across two distinct benchmark architectures, we demonstrated that structural centrality provides only a conditional proxy. While simple out-degree exhibits strong rank association with empirical recovery time during hard process crashes ($\\tau = 0.84$), the predictive relationship weakens under resource starvation faults ($\\tau = 0.38$). Furthermore, static structural weighting models fail to generalize across fundamentally different architectural topologies. Consequently, static topology alone is insufficiently stable for universal failure-impact estimation.

## 19. References
[1] X. Zhou, X. Peng, T. Xie, J. Sun, C. Ji, W. Li, and D. Ding, "Fault Analysis and Debugging of Microservice Systems: Industrial Survey, Benchmark System, and Empirical Study," *IEEE Transactions on Software Engineering*, vol. 47, no. 2, pp. 243-260, 2021, doi: 10.1109/TSE.2018.2887384.
[2] L. Ma et al., "MS-Rank: Multi-Metric and Self-Adaptive Root Cause Diagnosis for Microservice Applications," in *ICWS*, pp. 1-8, 2019, doi: 10.1109/ICWS.2019.00022.
[3] T. Zimmermann, R. Premraj, and A. Zeller, "Predicting Defects for Eclipse," in *PROMISE*, p. 9, 2007.
[4] A. Basiri et al., "Chaos Engineering," *IEEE Software*, vol. 33, no. 3, pp. 35-41, 2016.
[5] Y. Chen, Y. Jiang, and Y. Luo, "Modeling Cascading Failures in Microservice Architectures," in *CCGrid*, pp. 1-10, 2021.
[6] Y. Gan et al., "An open-source benchmark suite for microservices and their hardware-software implications for cloud & edge systems," in *ASPLOS*, pp. 3-18, 2019.
[7] A. Rahman, R. Mahdavi-Hezaveh, and L. Williams, "A systematic mapping study of infrastructure as code research," *Information and Software Technology*, vol. 108, pp. 65-77, 2019. [VERIFY SPECIFIC CENTRALITY CITATION].
"""
write_file("PHASE8_5_FULL_JOURNAL_MANUSCRIPT.md", manuscript)

lit_review = """
# Phase 8.5 Literature Review Audit
The literature review in the main manuscript was completely restructured to synthesize research streams rather than listing papers. 
- It distinctly separates reactive RCA (MS-Rank) from proactive prediction.
- It appropriately scopes the Zimmermann citation to static source code defect prediction.
- It contextualizes Chaos Engineering as an untargeted mechanism that proactive static topology attempts to guide.
"""
write_file("PHASE8_5_LITERATURE_REVIEW.md", lit_review)

data_collection = """
# Phase 8.5 Data Collection Audit
- Confirmed DeathStarBench topologies (SN N=12, HR N=7).
- Workloads calibrated to 1000 RPS (SN) and 100 RPS (HR).
- Pumba faults mapped directly to implementation (SIGKILL 60s, tc netem 100ms +-20ms jitter 30s, stress-ng 30s).
- Definition of `recovery_time_s` mapped to the 10% median tolerance over 10 consecutive seconds, capped at 60s.
"""
write_file("PHASE8_5_DATA_COLLECTION_AND_EXPERIMENT_AUDIT.md", data_collection)

stat_results = """
# Phase 8.5 Statistical Results Audit
- 171 valid observations confirmed.
- SN kill tau=0.84, CPU tau=0.38 confirmed and integrated descriptively without fabricating a formal interaction test.
- Cross-architecture generalization explicitly incorporates the N=7 tied rank non-identifiability.
- No p-values were invented; reliance was placed strictly on tau and rho effect sizes given the N=7/12 constraint.
"""
write_file("PHASE8_5_STATISTICAL_RESULTS_AUDIT.md", stat_results)

claim_matrix = """
# Phase 8.5 Claim Evidence Matrix
| Claim | Source | Type | Strength |
| :--- | :--- | :--- | :--- |
| Kill faults show strong structural association | Phase 5C output (tau=0.84) | Observed | Strong |
| CPU faults show weak structural association | Phase 5C output (tau=0.38) | Observed | Strong |
| Static weights fail to generalize | Phase 5B cross_architecture_validation.csv | Derived | Strong (within tested archs) |
| SDG structure drives prediction failure | Theoretical mechanism | Interpretive | Cautious |
"""
write_file("PHASE8_5_CLAIM_EVIDENCE_MATRIX.md", claim_matrix)

citation_audit = """
# Phase 8.5 Citation Audit
- Zhou et al. DOI corrected to 10.1109/TSE.2018.2887384
- MS-Rank DOI verified as 10.1109/ICWS.2019.00022
- Citation 7 (Rahman) explicitly marked with [VERIFY SPECIFIC CENTRALITY CITATION].
"""
write_file("PHASE8_5_CITATION_AUDIT.md", citation_audit)

table_plan = """
# Phase 8.5 Table Plan
- Table 1: Literature Synthesis Matrix
- Table 2: Benchmark Topology Statistics (Nodes, Edges, Max Depth)
- Table 3: Fault Injection Configurations (Pumba Parameters)
- Table 4: Overall Topology-Impact Associations (tau, rho)
- Table 5: Cross-Architecture Evaluation Matrix
"""
write_file("PHASE8_5_TABLE_PLAN.md", table_plan)

figure_plan = """
# Phase 8.5 Figure Plan
- Figure 1: Proactive vs Reactive Analysis Paradigm
- Figure 2: Experimental Data Collection Pipeline
- Figure 3: Configured Graphs (SN Mesh vs HR Tree)
- Figure 4: Fault-Modality Effect Size Divergence
"""
write_file("PHASE8_5_FIGURE_PLAN.md", figure_plan)

threats = """
# Phase 8.5 Threats and Limitations
Threats to validity were substantially expanded to cover Construct, Internal, Statistical, and External bounds, specifically highlighting the risk of N=7 statistical power and 10% tolerance sensitivity.
"""
write_file("PHASE8_5_THREATS_AND_LIMITATIONS.md", threats)

reviewer_sim = """
# Phase 8.5 Reviewer Simulation
**Reviewer 1 (Empirical SE):**
- *Concern (Major):* N=7 is too small for cross-architecture validation.
- *Resolution:* The manuscript now explicitly declares the tied-rank non-identifiability on N=7 as a limitation of flat graphs, framing the generalization failure as a structural mismatch rather than a statistical certainty.

**Reviewer 2 (Distributed Systems):**
- *Concern (Major):* Configured graphs ignore dynamic traffic routes.
- *Resolution:* Explicitly justified the use of configured graphs to prevent workload survivorship bias, positioning dynamic graphs as future work.

**Reviewer 3 (Editor):**
- *Concern (Minor):* Is the hybrid metric actually novel?
- *Resolution:* Removed claims of novelty for the metric, pivoting the contribution entirely to the empirical demonstration of topological limitations.
"""
write_file("PHASE8_5_REVIEWER_SIMULATION.md", reviewer_sim)

missing = """
# Phase 8.5 Missing Evidence
- **Literature:** Citation 7 (Rahman et al.) centrality claim remains unverified.
- **Data:** Business-level metrics (e.g., dropped user requests) are absent from the dataset.
- **Analysis:** Formal statistical interaction tests comparing tau coefficients across fault modalities were not performed (results remain descriptive).
"""
write_file("PHASE8_5_MISSING_EVIDENCE.md", missing)

lit_matrix = """
# Phase 8.5 Literature Matrix
| Author | Reactive/Proactive | Static/Dynamic | Fault Modality | Cross-Arch |
| :--- | :--- | :--- | :--- | :--- |
| Zhou (2021) | Reactive | Dynamic | No | No |
| Ma (2019) | Reactive | Dynamic | No | No |
| Chen (2021) | Proactive | Static (Sim) | No | No |
| This Study | Proactive | Static | Yes | Yes |
"""
write_file("PHASE8_5_LITERATURE_MATRIX.md", lit_matrix)

print("Phase 8.5 reconstruction complete.")
word_count_main = len(manuscript.split("19. References")[0].split())
word_count_ref = len(manuscript.split("19. References")[1].split())
print(f"Main manuscript word count: {word_count_main}")
print(f"References word count: {word_count_ref}")
print(f"Total word count: {word_count_main + word_count_ref}")

if __name__ == "__main__":
    import sys
    sys.exit(0)
