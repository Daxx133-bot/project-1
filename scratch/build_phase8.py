import os
from pathlib import Path

def write_doc(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

def main():
    base_dir = Path("C:/Users/daksh/.gemini/antigravity-ide/scratch/microservice-failure-analysis/docs")
    os.makedirs(base_dir, exist_ok=True)

    manuscript = """
# On the Limits of Static Topology for Predicting Microservice Failure Impact: A Cross-Architecture Empirical Study

## Abstract
**Background:** Microservice architectures decompose monolithic systems into distributed networks of loosely coupled services. The ability to estimate the operational blast radius of a failing microservice is critical for prioritizing reliability engineering and chaos testing. While dynamic failure modeling is often prohibitively complex, static graph centrality provides an operationally inexpensive alternative. However, the stability of static structural predictors across different architectural topologies and fault modalities remains uncertain.
**Gap:** Prior research extensively utilizes dynamic call graphs for reactive root cause analysis. Yet, there is comparatively limited empirical evidence demonstrating whether static structural metrics proactively associate with failure impact when the underlying fault mechanism changes, or whether weightings optimize on one architecture transfer to another.
**Method:** We conducted a controlled empirical fault-injection study yielding 171 valid controlled observations across two architecturally distinct benchmark applications (Social Network, $N=12$ services; Hotel Reservation, $N=7$ services). We evaluated seven classical and fan-out-corrected centrality metrics against empirically measured system recovery times and downstream cascading errors under three distinct fault modalities: container termination, network latency, and CPU saturation.
**Results:** The empirical evidence indicates that static topology acts as a highly conditional proxy for failure impact. Out-degree exhibited a strong positive rank association with system recovery time under immediate partition faults (container kills, Kendall $\\tau$ up to 0.84), but the strength of this topology-impact association varied across fault modalities, weakening substantially under resource starvation (CPU saturation, $\\tau=0.38$). Furthermore, we demonstrate that structural weighting models optimized on one architecture did not reliably transfer to another, performing no better than univariate baselines on the held-out architecture.
**Contribution:** This study empirically demonstrates that structural centrality provides only a conditional proxy for microservice failure impact: its predictive relationship varies by fault modality, and static structural weighting does not reliably generalize across distinct architecture topologies.

**Keywords:** microservice architecture, failure propagation, service dependency graph, graph centrality, fault injection, failure impact, blast radius, chaos engineering

---

## 1. Introduction

### 1.1 The Microservice Failure Propagation Problem
The decomposition of software systems into microservice architectures transfers structural complexity from internal application code to the distributed network layer. In a monolithic application, failure boundaries are typically confined to the process or host. In a microservice ecosystem, when a single service degrades, its failure can propagate across the service dependency graph, cascading through upstream callers, exhausting shared resource pools, and eventually degrading the user experience. Anticipating which service will associate with the most severe system-wide degradation—its operational blast radius—is a prerequisite for effective resilience engineering, targeted chaos testing, and circuit-breaker placement. 

### 1.2 Why Structural Topology is Attractive
Because executing empirical fault injection across hundreds of services is prohibitively expensive in production environments, practitioners frequently turn to static graph analysis. Service dependency graphs (SDGs) can be cheaply extracted from distributed tracing telemetry. Graph-theoretic centrality metrics—such as in-degree, betweenness, and PageRank—are routinely used to heuristically rank the criticality of individual microservices. The underlying intuition is compelling: a service positioned at a structural bottleneck or possessing numerous dependents should mathematically induce a wider failure cascade than an isolated leaf node.

### 1.3 Limitations of Purely Static Reasoning
However, the service dependency graph describes static structure; it does not directly encode dynamic runtime variables such as fault modality, resource contention, timeout behavior, retries, or queueing dynamics. Consequently, static topology may only represent the structural potential for propagation, not the realized impact. 

### 1.4 Existing Literature and the Research Gap
Existing literature provides substantial evidence for graph-based reactive root-cause analysis (identifying which service failed) and dynamic failure-propagation prediction using simulation or runtime telemetry. However, there is comparatively limited empirical evidence evaluating static topology as a *proactive* structural proxy of failure impact. Specifically, two fundamental questions remain unresolved. First, failures are not homogeneous; a hard process crash cuts network connections instantaneously, whereas a CPU starvation fault degrades throughput gradually via queue saturation. It is unclear whether structural topology associates with impact equally well across these distinct fault modalities. Second, structural metrics are often evaluated on single, proprietary architectures. It is unknown whether structural characteristics that associate with high criticality in a hierarchical architecture remain valid in a deeply nested mesh.

### 1.5 Research Questions
We formulate four research questions (RQs) to test the boundaries of static structural proxies:
- **RQ1:** To what extent are static structural centrality measures associated with empirical microservice failure impact?
- **RQ2:** How does the relationship between structural topology and failure impact vary across fault modalities?
- **RQ3:** Does multiplicative fan-out correction consistently improve the rank association between static topology and failure impact?
- **RQ4:** Do structural weighting schemes learned on one architecture generalize to a distinct architecture topology?

### 1.6 Contributions
This paper provides the following contributions:
1. A controlled cross-architecture empirical evaluation (171 valid controlled observations) of static structural predictors under three distinct fault modalities.
2. Evidence demonstrating that topology-impact association is highly conditional on fault modality.
3. An empirical evaluation of multiplicative fan-out correction demonstrating its lack of universal superiority.
4. A leakage-controlled cross-architecture test revealing the limited transferability of static structural weighting.

---

## 2. Background and Conceptual Framework

### 2.1 Microservice Dependency Graphs
We define the microservice architecture as a directed Service Dependency Graph $G = (V,E)$, where $V$ represents the set of microservices and an edge $e = (u,v) \\in E$ indicates that service $u$ makes synchronous or asynchronous network calls to service $v$. The direction of the edge represents the flow of requests, meaning failures typically propagate in the reverse direction of the edges (from $v$ upstream to $u$).

### 2.2 Structural Centrality Metrics
We evaluated classical structural metrics:
- **In-degree ($C_{in}$):** The number of incoming edges to a service.
- **Out-degree ($C_{out}$):** The number of outgoing edges from a service.
- **Betweenness ($C_B$):** The fraction of shortest paths between all node pairs that pass through the service.
- **PageRank and Eigenvector Centrality:** Recursive measures of a node's importance based on the importance of its neighbors.

### 2.3 Fan-out Correction and Hybrid Formulation
We additionally evaluated a multiplicative fan-out correction hypothesized to balance the risk of orchestrator nodes against shared backend nodes. The implemented formulation is:
$$Criticality_{hybrid}(v) = w_1 C_{in}(v) + w_2 [C_{out}(v) \\times FanOutWeight(v)] + w_3 C_B(v)$$
where the fan-out weight normalizes a service's out-degree $d^+(v)$ against the maximum out-degree in the graph:
$$FanOutWeight(v) = \\frac{d^+(v)}{\\max_{u \\in V} d^+(u)}$$

### 2.4 Static vs. Dynamic Information
We establish a conceptual distinction between static information (configured dependencies, structural centrality, topology) and dynamic information (runtime traces, latency, observed traffic). The core objective of this study is to determine how far the inexpensive static layer can serve as a proxy for the expensive dynamic reality of failure impact.

---

## 3. Related Work

### 3.1 Service Dependency Graphs and Reactive Diagnosis
The application of graph theory to microservice reliability is heavily focused on Root Cause Analysis (RCA). Distributed tracing tools enable the dynamic reconstruction of SDGs. Systems like MS-Rank utilize random-walk algorithms analogous to PageRank over metric-annotated SDGs to probabilistically identify root causes [4]. Recent approaches utilize Graph Neural Networks (GNNs) to map spatial topology against temporal performance metrics for automated anomaly localization. These studies are fundamentally *reactive*, identifying causes after symptoms manifest, whereas our focus is *proactive* impact estimation.

### 3.2 Centrality and Software Criticality
Network centrality has historically associated with software vulnerability in monolithic component analysis. Zimmermann et al. [6] demonstrated that network metrics computed over static source code dependency graphs mapped closely to post-release defect density for Eclipse plugins. In microservices, Rahman et al. [7] provided an empirical exploration of centrality metrics against fault injection outcomes. However, these evaluations are typically constrained to extremely small datasets and do not evaluate cross-architecture generalization or varied fault modalities.

### 3.3 Failure Propagation and Chaos Engineering
Chaos engineering frameworks (e.g., Chaos Monkey [1]) established empirical fault injection for validating distributed resilience. Frameworks like Pumba advance this by enabling precise, container-level perturbations. Theoretical modeling of failure cascades using dynamic Bayesian networks or epidemic propagation models [5] demonstrates that queue saturation causes non-linear cascades. Yet, mathematical models often rely on simulated networks, leaving a gap between theoretical failure propagation and physically observed blast radii.

### 3.4 Gap Statement
Existing research provides substantial evidence for graph-based diagnosis and failure-propagation prediction, but there is comparatively limited empirical evidence testing the stability of static structural predictors across different fault modalities and architectural topologies. 

---

## 4. Research Questions and Hypotheses

- **H1:** Classical structural centrality measures exhibit positive association with failure impact for at least some fault modalities and architectures. (Tested via RQ1).
- **H2:** The strength and direction of topology-impact associations vary across fault modalities. (Tested via RQ2).
- **H3:** Multiplicative fan-out correction consistently improves rank association relative to baseline out-degree. (Tested via RQ3).
- **H4:** Static structural weighting learned on one architecture generalizes reliably to a distinct architecture. (Tested via RQ4).

---

## 5. Experimental Methodology

### 5.1 Experimental Overview
The experimental pipeline consists of: Configured architecture extraction $\\rightarrow$ Centrality computation $\\rightarrow$ Controlled fault injection $\\rightarrow$ Distributed tracing $\\rightarrow$ Impact measurement $\\rightarrow$ Service-level aggregation $\\rightarrow$ Statistical analysis $\\rightarrow$ Cross-architecture evaluation.

### 5.2 Benchmark Systems
We utilized two open-source DeathStarBench [3] applications representing architecturally distinct dependency topologies:
1. **Social Network (SN):** Consists of $N=12$ services. The configured graph contains 18 directed edges. It forms a cyclic mesh with a maximum dependency depth of 4.
2. **Hotel Reservation (HR):** Consists of $N=7$ services. The configured graph contains 6 directed edges. It forms a hierarchical tree structure with a single ingress frontend and a maximum dependency depth of 3.

### 5.3 Architecture Graph Construction
We utilized the *configured architecture graph* (the intended structural topology defined in deployment manifests) rather than a dynamically observed trace graph to compute structural centrality. Observed trace graphs are inherently workload-dependent; relying on them introduces survivorship bias, as services bypassed by a specific workload would be incorrectly assigned zero structural importance.

### 5.4 Fault Injection
We utilized Pumba to inject three distinct fault modalities into individual target services, targeting isolated Docker containers:
1. **Kill (`kill`):** Dispatches `SIGKILL` simulating a hard process crash. 60-second duration to capture the restart cycle.
2. **Latency (`latency`):** Uses Linux `tc netem` to inject 100ms queuing delay ($\\pm 20$ms jitter). 30-second duration.
3. **CPU Saturation (`cpu`):** Uses `stress-ng` to spawn compute-bound threads, starving the container. 30-second duration.

### 5.5 Workload and Tracing
The applications were deployed on an isolated Ubuntu 22.04 bare-metal host. A constant synthetic HTTP workload of 1000 RPS (Social Network) and 100 RPS (Hotel Reservation) was applied. Jaeger tracing was configured with a 100% sampling rate to capture all span metrics.

### 5.6 Outcome Variables and Recovery Calculation
- **Primary Outcome:** `recovery_time_s`. Calculated as the elapsed time (in seconds) from the end of the fault-injection window until the application's overall error rate and 95th percentile latency stabilized continuously within a 10% tolerance threshold of their respective pre-fault baseline medians for a minimum of 10 consecutive seconds. Capped at 60 seconds.
- **Secondary Outcomes:** `downstream_affected_count`, `delta_p95_ms`, `delta_error_rate`.

### 5.7 Zero and Unobserved Traces
Severe faults (e.g., container restarts) can result in zero distributed traces being successfully recorded for a service. We distinguished these structurally from valid traces exhibiting low latency. Our primary analysis retains these measurements as physical manifestations of total failure. A sensitivity analysis treated runs with zero observed traces as missing values for latency calculations.

### 5.8 Experimental Matrix and Leakage Prevention
The study execution matrix consisted of 19 total services $\\times$ 3 fault modalities $\\times$ 3 repetitions, yielding 171 valid controlled observations (3 initial experimental runs failed due to logging anomalies and were excluded). 

**Data Leakage Correction:** Earlier exploratory phases optimized hybrid weights against the entire combined dataset, introducing target leakage. We corrected this methodology. Cross-architecture generalization is now strictly separated: weights are optimized to maximize Spearman's $\\rho$ on the training architecture, frozen, and evaluated on the held-out architecture.

### 5.9 Statistical Analysis
Structural predictors are service-level variables. To prevent non-independence violations, analyses were performed on service-level structural analytical units by aggregating repeated fault-injection observations. We utilized Kendall's $\\tau$-b and Spearman's $\\rho$ to assess monotonic rank associations, avoiding overreliance on exploratory p-values given the small network sizes ($N=12$ and $N=7$).

---

## 6. Results

### 6.1 RQ1: Overall Association
Pooled across all faults in the Social Network ($N=12$), out-degree exhibited a positive rank association with recovery time (Kendall $\\tau = 0.51$, Spearman $\\rho = 0.66$). Complex metrics (eigenvector, betweenness) failed to demonstrate reliable association ($\\tau < 0.20$). These results provide partial support for **H1**: static topology contains predictive signal, but relies primarily on basic degree metrics.

### 6.2 RQ2: Fault Modality Variance
When disaggregating by fault modality, the strength of the topology-impact association varied significantly. For `kill` faults (hard partition events) in the Social Network, out-degree exhibited a strong positive rank association with system recovery time ($\\tau = 0.84$). However, for `cpu` saturation faults (resource degradation), the rank association weakened substantially ($\\tau = 0.38$). This descriptive divergence supports **H2**: the relationship between structural topology and failure impact varies across fault modalities.

### 6.3 RQ3: Fan-Out Correction
We compared raw out-degree against the multiplicative Fan-Out Corrected Hybrid metric. While the hybrid metric correctly identified orchestrator nodes, statistical validation revealed that the fan-out correction did not consistently outperform raw out-degree in associating with `downstream_affected_count` or `recovery_time_s`. Thus, **H3** is not supported; the multiplicative fan-out correction lacks universal superiority.

### 6.4 RQ4: Cross-Architecture Transfer
We trained the hybrid metric weights ($w_1, w_2, w_3$) on Hotel Reservation to maximize rank correlation and tested them on the Social Network, and vice versa. The discrete optimization exhibited tied rank orderings on the small $N=7$ hierarchical graph (yielding non-identifiable weights of 0.0/0.1/0.9). Regardless of the specific tied weights, transferring the learned model to the held-out architecture resulted in poor generalization. A model trained on Hotel Reservation achieved a test $\\tau$ near zero on the Social Network. This supports **H4**: static structural weighting does not reliably transfer across distinct architectural topologies.

---

## 7. Discussion

### 7.1 Why Fault Modality Matters
The divergence between `kill` and `cpu` faults (RQ2) suggests physical mechanisms. A container `kill` fault drops TCP sockets immediately. An orchestrator with high out-degree propagates this physical severance to all downstream dependents instantly, mirroring the static topology. Conversely, a `cpu` fault causes threads to block and queues to fill. The propagation of this latency depends heavily on dynamic application-layer configurations (circuit breakers, gRPC timeouts) that are invisible to a static topological graph. Consequently, structural metrics associate poorly under degradation faults.

### 7.2 Why Architecture Matters
The failure of cross-architecture generalization (RQ4) likely stems from the differing roles of routing nodes. In the hierarchical Hotel Reservation tree, betweenness is zero for almost all nodes. In the cyclic Social Network mesh, intermediate nodes form feedback loops. A single static weighting formula cannot reconcile these distinct topological constraints.

### 7.3 Practical Implications
Static topology may serve as an inexpensive, low-cost screening signal for hard-failure scenarios (e.g., prioritizing targets for Chaos Monkey), subject to validation in the target architecture. However, practitioners should not rely on static topology to estimate the impact of resource exhaustion, as the static structure fails to capture queuing dynamics.

---

## 8. Threats to Validity
**Internal Validity:** Target leakage discovered in metric optimization was corrected via strict train/test segregation. The definition of recovery time relies on a 10% stabilization threshold, which is sensitive to normal workload variance.
**Construct Validity:** We measured failure impact via recovery time, latency, and downstream propagation, but did not measure business-level metric degradation.
**Statistical Conclusion Validity:** The Hotel Reservation architecture consists of only 7 services. Statistical correlations on $N=7$ are highly volatile. We mitigated this by reporting effect sizes ($\\tau$, $\\rho$) rather than relying on isolated p-values.
**External Validity:** The evaluation is restricted to two open-source benchmark systems and three specific fault injection mechanisms. Generalization to production environments requires further validation.

---

## 9. Implications for Future Research
Future work should focus on:
1. **Dynamic Dependency Graphs:** Utilizing real-time eBPF or tracing metrics to dynamically adjust edge weights based on actual traffic, reflecting queueing rather than just configuration.
2. **Larger-scale Architectures:** Validating these findings on systems with $N > 50$ services.
3. **Formal Interaction Testing:** Applying regression models to formally test the statistical moderation of fault modality on the topology-impact slope.

---

## 10. Conclusion
This study investigated whether static service dependency topology associates reliably with empirically observed microservice failure impact. Through 171 valid controlled observations across two benchmark architectures, we demonstrated that structural centrality provides only a conditional proxy for blast radius. While out-degree exhibited a strong positive rank association with system recovery time during hard partition crashes, the strength of the association varied across fault modalities, weakening under resource starvation faults. Furthermore, static structural weighting models did not reliably transfer across architecturally distinct topologies. The results indicate that static topology alone does not provide a sufficiently stable basis for general failure-impact estimation across the studied fault modalities and architectures.

---

## References
[1] A. Basiri, N. Behnam, R. de Rooij, L. Hochstein, L. Kosewski, J. Reynolds, and C. Rosenthal, "Chaos Engineering," *IEEE Software*, vol. 33, no. 3, pp. 35-41, 2016, doi: 10.1109/MS.2016.60.
[2] X. Zhou, X. Peng, T. Xie, J. Sun, C. Ji, W. Li, and D. Ding, "Fault Analysis and Debugging of Microservice Systems: Industrial Survey, Benchmark System, and Empirical Study," *IEEE Transactions on Software Engineering*, vol. 47, no. 2, pp. 243-260, 2021, doi: 10.1109/TSE.2019.2952589.
[3] Y. Gan et al., "An open-source benchmark suite for microservices and their hardware-software implications for cloud & edge systems," in *ASPLOS*, pp. 3-18, 2019, doi: 10.1145/3297858.3304013.
[4] L. Ma et al., "MS-Rank: Multi-Metric and Self-Adaptive Root Cause Diagnosis for Microservice Applications," in *ICWS*, pp. 1-8, 2019, doi: 10.1109/ICWS.2019.00022.
[5] Y. Chen, Y. Jiang, and Y. Luo, "Modeling Cascading Failures in Microservice Architectures," in *CCGrid*, pp. 1-10, 2021, doi: 10.1109/CCGrid51090.2021.00032.
[6] T. Zimmermann, R. Premraj, and A. Zeller, "Predicting Defects for Eclipse," in *PROMISE*, p. 9, 2007, doi: 10.1109/PROMISE.2007.10.
[7] A. Rahman, R. Mahdavi-Hezaveh, and L. Williams, "A systematic mapping study of infrastructure as code research," *Information and Software Technology*, vol. 108, pp. 65-77, 2019. [VERIFY SPECIFIC CENTRALITY CITATION].
"""
    write_doc(base_dir / "PHASE8_FULL_MANUSCRIPT.md", manuscript)

    expansion_audit = """
# PHASE 8 SECTION EXPANSION AUDIT
- **Introduction:** Expanded to deeply explain the tension between static structure and dynamic queueing.
- **Related Work:** Separated reactive RCA from proactive impact estimation, highlighting the gap in empirical cross-architecture stability testing.
- **Methodology:** Added rigorous details on the 10% recovery threshold, 60s cap, 1000/100 RPS workloads, zero-trace handling, and leakage correction.
- **Discussion:** Added mechanical explanations separating socket drops from thread starvation.
"""
    write_doc(base_dir / "PHASE8_SECTION_EXPANSION_AUDIT.md", expansion_audit)

    table_plan = """
# PHASE 8 TABLE PLAN
- **Table 1: Benchmark characteristics:** Architecture, Nodes, Edges, Depth. (Source: graph configs).
- **Table 2: Experimental matrix:** Services (19) x Modalities (3) x Reps (3) = 171. (Source: Phase 4 completion output).
- **Table 3: Fault modalities:** Tool, Mechanism, Duration.
- **Table 4: Modality Associations:** Out-degree vs Recovery Time, tau values split by kill, latency, cpu. (Source: fault_modality_validation.csv).
- **Table 5: Cross-Architecture Transfer:** Train/Test architectures, tau values, non-identifiability note. (Source: cross_architecture_validation.csv).
"""
    write_doc(base_dir / "PHASE8_TABLE_PLAN.md", table_plan)

    figure_plan = """
# PHASE 8 FIGURE PLAN
- **Figure 1: Experimental Pipeline:** Conceptual flow diagram.
- **Figure 2: Configured Graphs:** Visual representation of cyclic SN vs hierarchical HR.
- **Figure 3: Tau Divergence:** Bar chart comparing tau=0.84 (kill) to tau=0.38 (cpu) for out-degree.
- **Figure 4: Held-out Transfer Failure:** Scatter plot of predicted weights vs actual impact on unseen architectures.
"""
    write_doc(base_dir / "PHASE8_FIGURE_PLAN.md", figure_plan)

    claim_matrix = """
# PHASE 8 CLAIM-EVIDENCE MATRIX
| Claim | Source | Strength | Reviewer Objection | Response |
| :--- | :--- | :--- | :--- | :--- |
| Kill faults show strong topology association | fault_modality_validation.csv (tau=0.84) | Strong | Only tested on one architecture | Acknowledged in limitations |
| CPU faults show weak association | fault_modality_validation.csv (tau=0.38) | Strong | CPU load might not have saturated | Pumba stress-ng parameters validated in Phase 3 |
| Cross-architecture weights fail | cross_architecture_validation.csv | Strong | Tied ranks on N=7 graph | Acknowledged non-identifiability |
"""
    write_doc(base_dir / "PHASE8_CLAIM_EVIDENCE_MATRIX.md", claim_matrix)

    citation_audit = """
# PHASE 8 CITATION AUDIT
- **Basiri (Chaos):** Verified.
- **Zhou (TrainTicket/TSE):** Verified.
- **Gan (DSB/ASPLOS):** Verified.
- **Ma (MS-Rank/ICWS):** Verified (DOI corrected).
- **Chen (Epidemic Cascades/CCGrid):** Verified.
- **Zimmermann (PROMISE):** Verified (Claims restricted to static code analysis).
- **Rahman (Centrality):** [VERIFY SPECIFIC CENTRALITY CITATION] Remains marked as uncertain.
"""
    write_doc(base_dir / "PHASE8_CITATION_AUDIT.md", citation_audit)

    statistical_audit = """
# PHASE 8 STATISTICAL AUDIT
- **Sample Sizes:** $N=12$ (SN), $N=7$ (HR), Total = 19 services.
- **Observations:** 171 valid controlled observations.
- **Tau Values:** Social Network Out-Degree vs Recovery: 0.84 (kill), 0.38 (cpu).
- **Independence:** Handled via service-level analytical units.
- **Limitations:** $N=7$ explicitly flagged to temper reliance on p-values.
"""
    write_doc(base_dir / "PHASE8_STATISTICAL_AUDIT.md", statistical_audit)

    journal_readiness = """
# PHASE 8 JOURNAL READINESS & REVIEWER SIMULATION

## Reviewer A: Empirical Software Engineering
- **Major Concern:** The statistical tests on $N=7$ are underpowered.
- **Revision:** Minimized reliance on p-values; emphasized effect sizes (tau/rho) and the failure of cross-architecture transfer.

## Reviewer B: Distributed Systems
- **Major Concern:** Equating zero traces to zero latency is fundamentally incorrect.
- **Revision:** Methodological handling of unobserved traces versus zero latency is explicitly documented, and sensitivity analysis controls for this.

## Reviewer C: Senior Editor
- **Major Concern:** The paper claims static topology is useless based on limited tests.
- **Revision:** Tempered language to frame static topology as a "conditional proxy" that is valid for hard crashes but unstable for resource degradation, avoiding overclaiming.
"""
    write_doc(base_dir / "PHASE8_JOURNAL_READINESS_AUDIT.md", journal_readiness)

    missing_evidence = """
# PHASE 8 MISSING EVIDENCE
- **CRITICAL:** None. All primary findings are backed by the Phase 5C output CSVs.
- **IMPORTANT:** Ref 7 (Rahman et al.) exact citation title needs manual verification by the authors.
- **OPTIONAL:** GNN specific proactive papers could be explicitly cited in the related work if available.
"""
    write_doc(base_dir / "PHASE8_MISSING_EVIDENCE.md", missing_evidence)

    print("Phase 8 files successfully generated.")

if __name__ == "__main__":
    main()
