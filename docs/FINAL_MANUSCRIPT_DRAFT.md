# On the Limits of Static Topology for Predicting Microservice Failure Impact: A Cross-Architecture Empirical Study

## Abstract
**Background:** Microservice architectures decompose monolithic systems into distributed networks of loosely coupled services. Anticipating the operational blast radius of a failing microservice is critical for prioritizing reliability engineering and chaos testing, but dynamic failure modeling is often prohibitively complex. Static graph centrality provides an operationally cheap alternative, yet its structural association with failure impact across different architectural topologies and fault modalities remains uncertain.
**Gap:** While prior research extensively utilizes dynamic call graphs for reactive root cause analysis, there is comparatively limited empirical evidence demonstrating whether static structural metrics proactively associate with failure impact when the underlying fault mechanism or architectural topology changes.
**Method:** We conducted a controlled fault-injection study yielding 171 valid controlled observations across two structurally distinct benchmark applications (Social Network, $N=12$; Hotel Reservation, $N=7$). We evaluated seven classical and fan-out-corrected centrality metrics against empirically measured system recovery times and downstream cascading errors under three distinct fault modalities: container termination, network latency, and CPU saturation.
**Results:** The empirical evidence indicates that static topology acts as a highly conditional proxy for failure impact. Out-degree exhibited a strong positive rank association with system recovery time under immediate partition faults (container kills, Kendall $\tau$ up to 0.88), but the strength of this topology-impact association varied across fault modalities, weakening substantially under resource starvation (CPU saturation). Furthermore, we demonstrate that structural weighting models optimized on one architecture topology did not reliably transfer to another, performing no better than univariate baselines on the held-out architecture.
**Contribution:** This study empirically demonstrates that structural centrality provides only a conditional proxy for microservice failure impact: its predictive relationship varies by fault modality, and static structural weighting does not reliably generalize across distinct architecture topologies.

**Keywords:** microservice architecture, failure propagation, service dependency graph, graph centrality, fault injection, failure impact, blast radius, chaos engineering

---

## 1. Introduction

The decomposition of software systems into microservice architectures transfers complexity from internal application code to the network layer. When a single service degrades, its failure can propagate across the service dependency graph, cascading through upstream callers and exhausting shared resource pools. Anticipating which service will associate with the most severe system-wide degradation—its operational blast radius—is a prerequisite for effective resilience engineering, targeted chaos testing, and circuit-breaker placement.

Because executing empirical fault injection across hundreds of services is prohibitively expensive in production environments, practitioners frequently turn to static graph analysis. Service dependency graphs (SDGs) can be cheaply extracted from distributed tracing telemetry. Graph-theoretic centrality metrics—such as in-degree, betweenness, and PageRank—are routinely used to heuristically rank the criticality of individual microservices. The underlying intuition is compelling: a service positioned at a structural bottleneck or possessing numerous dependents should mathematically induce a wider failure cascade than an isolated leaf node.

While existing research heavily utilizes SDGs for reactive root cause analysis (identifying which service failed), the reviewed literature provides limited evidence evaluating static topology as a *proactive* structural proxy of failure impact. Specifically, two fundamental questions remain unresolved. First, failures are not homogeneous; a hard process crash cuts network connections instantaneously, whereas a CPU starvation fault degrades throughput gradually. It is unclear whether structural topology associates with impact equally well across these distinct fault modalities. Second, structural metrics are often evaluated on single, proprietary architectures. It is unknown whether structural characteristics that associate with high criticality in a hierarchical architecture remain valid in a deeply nested, cyclic mesh.

This study investigates the boundaries of static structural proxies. Rather than proposing a universally superior centrality metric, we aim to empirically determine the conditions under which static topology provides a reliable structural proxy for failure impact, and where it breaks down.

We conducted a controlled fault-injection experiment across two structurally distinct microservice applications from the DeathStarBench suite: the Social Network (12 core services, cyclic mesh) and Hotel Reservation (7 core services, hierarchical tree). Generating 171 valid controlled observations across three fault modalities (container termination, network latency, and CPU saturation), we evaluated seven structural metrics against empirical system recovery time and downstream error propagation. To prevent methodological target leakage, we strictly segregated optimization and evaluation architectures.

The core findings challenge the assumption that structural position is a universal proxy for criticality. We found that the association between structural centrality and failure impact is conditionally dependent on the fault modality. While out-degree serves as a strong structural proxy of blast radius during hard container crashes, its rank association deteriorates substantially under CPU starvation faults. Furthermore, our cross-architecture evaluation demonstrates that static structural weightings optimized for one architectural class did not reliably transfer to another, yielding held-out rank associations no better than basic degree metrics.

The remainder of this paper is structured as follows. Section 2 reviews related work. Section 3 formalizes the research questions. Section 4 details the experimental methodology. Section 5 presents the empirical results. Section 6 interprets these findings, discusses their practical implications, and outlines threats to validity. Section 7 concludes.

---

## 2. Background and Related Work

### 2.1 Service Dependency Graphs and Reactive Diagnosis
The application of graph theory to microservice reliability is deeply rooted in Root Cause Analysis (RCA). Distributed tracing tools enable the dynamic reconstruction of Service Dependency Graphs (SDGs). Researchers have leveraged these graphs extensively to trace anomalies backward from the user edge to the offending service. Systems like MS-Rank utilize random-walk algorithms analogous to PageRank over metric-annotated SDGs to probabilistically identify root causes [4]. Similarly, recent approaches utilize Graph Neural Networks (GNNs) to map spatial topology against temporal performance metrics for automated anomaly localization. 

While these studies establish that topological pathways govern the propagation of errors, they are fundamentally *reactive*. They trace a failure that has already occurred back to its source. Our work investigates the inverse, *proactive* problem: evaluating static topology as a structural proxy for the magnitude of a potential failure.

### 2.2 Centrality-Based Service Criticality
The hypothesis that network centrality associates with software vulnerability originated in monolithic component analysis. Zimmermann et al. [6] demonstrated that network metrics computed over static source code dependency graphs mapped closely to post-release defect density for Eclipse plugins. In the context of microservices, Rahman et al. [8] provided an empirical exploration of centrality metrics against fault injection outcomes, reporting that in-degree centrality correlated with HTTP 500 error occurrence in a proprietary five-service application. 

However, existing evaluations are typically constrained to extremely small graphs, rarely differentiate between failure mechanisms (e.g., resource exhaustion versus process crashes), and almost never evaluate whether findings generalize beyond a single, isolated application architecture.

### 2.3 Failure Propagation and Fault Injection
Chaos engineering frameworks, beginning with Chaos Monkey, established the necessity of empirical fault injection for validating distributed system resilience [1]. Frameworks like Pumba and Chaos Mesh have advanced this by enabling precise, container-level perturbations, including network latency and CPU throttling. Theoretical modeling of these phenomena—using dynamic Bayesian networks or epidemic propagation models [5]—has demonstrated that queue saturation and thread depletion cause non-linear failure cascades. Yet, these mathematical models often rely on simulated networks rather than empirical containerized execution, leaving a gap between theoretical failure propagation and physically observed blast radii.

### 2.4 Positioning of the Present Study
The existing literature provides substantial evidence for graph-based diagnosis, but comparatively limited empirical evidence testing the stability of static structural predictors. We address this gap by systematically evaluating structural metrics across different fault modalities (crash vs. resource exhaustion) and directly testing the cross-architecture generalization of structural criticality models.

---

## 3. Research Questions and Hypotheses

To structure our investigation into the limits of structural failure estimation, we formulate four Research Questions (RQs) and corresponding Hypotheses (Hs):

**RQ1: To what extent do static structural centrality measures associate with empirically observed microservice failure impact?**
- **H1:** Classical structural metrics provide a measurable but non-universal proxy for failure impact.

**RQ2: How does the association between structural topology and failure impact vary across fault modalities?**
- **H2:** The relationship between structural topology and failure impact varies by fault modality.

**RQ3: Does fan-out correction provide additional explanatory/predictive association beyond classical topology measures?**
- **H3:** Fan-out correction improves failure-impact prediction beyond classical structural measures. 

**RQ4: Do structural weightings learned on one architecture transfer to another architecture?**
- **H4:** Static structural weightings learned on one architecture generalize poorly to a structurally distinct architecture.

---

## 4. Experimental Method

### 4.1 Architecture Selection and Graph Definition
We selected two open-source microservice applications from the DeathStarBench suite to represent distinct structural topologies. 

1. **Social Network (SN):** 12 core microservices. The configured architecture graph consists of 12 nodes and 18 directed edges. It forms a cyclic mesh, featuring complex feedback loops between graph tiers (e.g., timeline aggregation and user relation services). Maximum dependency depth is 4.
2. **Hotel Reservation (HR):** 7 core microservices. The configured architecture graph consists of 7 nodes and 6 directed edges. It forms a strict hierarchical tree, with a single ingress frontend dispatching requests to downstream leaf nodes. Maximum dependency depth is 3.

[FIGURE 1 HERE]
*Caption:* Experimental Workflow. Flowchart showing deployment $\rightarrow$ workload $\rightarrow$ fault injection $\rightarrow$ telemetry gathering $\rightarrow$ static topology correlation.
*Purpose:* Visually explains the controlled study design.

[FIGURE 2 HERE]
*Caption:* Social Network Configured Graph.
*Purpose:* Directed graph visualization of the 12 nodes highlighting cyclic relationships.

[FIGURE 3 HERE]
*Caption:* Hotel Reservation Configured Graph.
*Purpose:* Directed tree graph of the 7 nodes highlighting the single frontend ingress.

We utilized the *configured architecture graph* (the intended structural topology defined in deployment manifests) rather than a dynamically observed trace graph to compute structural centrality. Observed trace graphs are inherently workload-dependent; relying on them risks survivorship bias, where services bypassed by a specific workload are incorrectly assigned zero structural importance.

### 4.2 Structural Metrics Evaluated
For each service $v$, we computed classical centrality metrics: in-degree ($C_{in}$), out-degree ($C_{out}$), total degree, betweenness ($C_B$), PageRank, and eigenvector centrality. 

We additionally evaluated a hybrid structural metric. The formulation is:
$$Criticality_{hybrid}(v) = w_1 C_{in}(v) + w_2 [C_{out}(v) \times FanOutWeight(v)] + w_3 C_B(v)$$
where the multiplicative fan-out correction normalizes a service's out-degree $d^+(v)$ against the maximum out-degree in the graph:
$$FanOutWeight(v) = \frac{d^+(v)}{\max_{u \in V} d^+(u)}$$

### 4.3 Workload and Fault Injection Configuration
The applications were deployed on an isolated Ubuntu 22.04 bare-metal host (8-core Intel i7, 16GB RAM) using Docker Compose. A constant synthetic HTTP workload of 1000 req/s (Social Network) and 100 req/s (Hotel Reservation) was applied using `wrk2`. Jaeger tracing was configured with a 100% sampling rate.

We utilized Pumba to inject three distinct fault modalities into individual target services:
1. **Kill (`kill`):** Dispatches `SIGKILL` to the target container, simulating a hard process crash and triggering Docker restart policies.
2. **Latency (`latency`):** Uses Linux `tc netem` to inject 100ms of queuing delay ($\pm 20$ms jitter) to all egress traffic from the target container.
3. **CPU Saturation (`cpu`):** Uses `stress-ng` to spawn compute-bound threads, starving the target application of CPU cycles.

Each fault injection window lasted 30 seconds (60 seconds for kill faults to allow restart cycles), bounded by 30-second pre-fault baseline and post-fault recovery observation windows.

### 4.4 Measurement and Outcomes
We define failure impact across one primary and three secondary dimensions, calculated from tracing telemetry.

- **Primary Outcome:** `recovery_time_s`. Calculated as the elapsed time (in seconds) from the end of the fault-injection window until the application's overall error rate and 95th percentile latency stabilized continuously within 10% of their respective pre-fault baseline medians for a minimum of 10 consecutive seconds. If stabilization was not reached within the 60-second recovery observation window, the value was capped at 60s.
- **Secondary Outcomes:** `downstream_affected_count` (number of services exhibiting a $>5\%$ error rate increase relative to baseline), `delta_p95_ms` (absolute increase in 95th percentile ingress latency), and `delta_error_rate` (absolute percentage point increase in overall HTTP 5xx error rate).

### 4.5 Experimental Matrix and Exclusions
The study execution matrix consisted of 19 total services $\times$ 3 fault modalities $\times$ 3 repetitions, yielding 171 valid controlled observations. Three initial experimental runs failed due to infrastructure logging anomalies and were excluded from the primary dataset prior to statistical analysis.

[TABLE 6 HERE]
*Table Name:* Experimental Matrix.

### 4.6 Statistical Design and Leakage Prevention
Structural predictors are service-level variables. Correlating them against 171 raw run-level observations violates independence assumptions. Therefore, all primary correlation analyses were performed on service-level analytical units (the mean outcome of the 3 repetitions for fault-specific analysis, or the mean across all faults for global analysis). 

We utilized Kendall's $\tau$-b and Spearman's $\rho$ to assess monotonic rank associations. Given the small network sizes ($N=12$ and $N=7$), we emphasize effect sizes and utilize permutation testing (10,000 resamples) where applicable.

**Data Leakage Correction:** Earlier exploratory phases of this research optimized the hybrid metric weights ($w_1, w_2, w_3$) against the entire combined dataset. This introduces target leakage. In this final validated methodology, cross-architecture generalization is strictly separated: weights are optimized to maximize Spearman's $\rho$ on the *training* architecture, frozen, and evaluated exactly once against the *held-out* test architecture.

### 4.7 Zero-Trace Handling
Severe faults (e.g., container restarts) can result in zero distributed traces being successfully recorded for a service during the measurement window. We distinguished these structurally from valid traces exhibiting low latency. Our primary analysis (Analysis A) retains these measurements as physical manifestations of total failure. A sensitivity analysis (Analysis B) treated runs with zero observed traces as missing (`NaN`) for latency calculations.

---

## 5. Results

[TABLE 7 HERE]
*Table Name:* Classical Centrality Results (Aggregate $\tau$ values).

[TABLE 8 HERE]
*Table Name:* Fault-Modality Results ($\tau$ values split by kill, latency, cpu).

[TABLE 9 HERE]
*Table Name:* Fan-out Comparison ($\tau$ and p-values for raw out-degree vs hybrid).

[TABLE 10 HERE]
*Table Name:* Cross-Architecture Transfer (Train vs Test $\tau$ scores).

### 5.1 RQ1: Classical Structural Centrality and Failure Impact
We evaluated the baseline association between structural metrics and the primary outcome (`recovery_time_s`), pooled across all faults. In the Social Network ($N=12$), out-degree exhibited a positive rank association with recovery time (Kendall $\tau = 0.51$, Spearman $\rho = 0.66$). Conversely, complex graph metrics such as eigenvector centrality and betweenness failed to demonstrate reliable association ($\tau < 0.20$). In Hotel Reservation ($N=7$), out-degree again provided the strongest directional indicator, though the small N warrants extreme caution interpreting global statistical strength. 

These results provide partial support for **H1**: static topology contains predictive signal, but it associates primarily through basic degree metrics rather than complex network centrality.

### 5.2 RQ2: Fault Modality Variance
When disaggregating the analysis by fault modality, the strength of the topology-impact association varied across fault modalities.

[FIGURE 6 HERE]
*Caption:* Kendall rank associations between out-degree and recovery time across fault modalities and architectures.
*Purpose:* Visually demonstrate the degradation of tau from kill to cpu.

For `kill` faults (hard partition events) in the Social Network ($N=12$), out-degree exhibited a strong positive rank association with system recovery time ($\tau = 0.84$). 

However, for `cpu` saturation faults (resource degradation), the rank association between out-degree and recovery time was substantially weaker ($\tau = 0.38$). 

This divergence supports **H2**: the relationship between structural topology and failure impact varies by fault modality.

### 5.3 RQ3: The Efficacy of Fan-Out Correction
We compared raw out-degree against the multiplicative Fan-Out Corrected Hybrid metric. While the hybrid metric correctly identified the orchestrator nodes in both architectures, statistical validation across the full service sets revealed that the fan-out correction did not consistently or significantly outperform raw out-degree in predicting `downstream_affected_count` or `recovery_time_s`. 

Consequently, **H3** is not supported by the evidence. The hypothesis that fan-out correction improves failure-impact prediction beyond classical structural measures is rejected in favor of simpler unadjusted degree metrics.

### 5.4 RQ4: Cross-Architecture Generalization
To test whether structural criticality models can generalize, we trained the weight parameters ($w_1, w_2, w_3$) of the hybrid metric on Hotel Reservation to maximize rank correlation with downstream impact, and tested those static weights on the Social Network, and vice versa.

The discrete optimization exhibited tied rank orderings on the small $N=7$ hierarchical graph, and the implementation retained the first tied solution. Regardless of the specific tied weights selected, transferring the learned model to the held-out architecture resulted in poor held-out generalization. A model trained on the hierarchical Hotel Reservation graph achieved a test $\tau$ near zero when evaluated on the cyclic Social Network graph. 

This strongly supports **H4**: static structural weighting learned on one microservice topology does not reliably transfer to another.

[FIGURE 8 HERE]
*Caption:* Cross-Architecture Transfer. Scatter plot of predicted structural scores vs actual empirical recovery time for the held-out test sets.
*Purpose:* Visually demonstrates the collapse of rank association on unseen graphs.

### 5.5 Sensitivity Analysis
Treating unobserved traces (caused by severe isolation or timeouts) as missing values (Analysis B) artificially suppressed the strongest failure impact signals. Removing these instances weakened the correlation between out-degree and latency spikes. The sensitivity analysis suggests that the observed topology-impact association is partly influenced by severe-fault runs in which no service trace was observed during the measurement window.

---

## 6. Discussion

### 6.1 Interpretation of Findings
The central finding of this study is that static structural topology is an inherently conditional proxy for microservice failure impact. 

The mechanism underlying the fault modality divergence (RQ2) is physical. A container `kill` fault forces the operating system to immediately drop TCP sockets. An orchestrator with high out-degree propagates this physical severance to all downstream dependents instantly. This pattern is consistent with the interpretation that hard service termination directly removes dependency paths mapped by static out-degree. Conversely, a `cpu` fault causes threads to block and queues to fill. The propagation of this latency depends heavily on application-layer configurations—circuit breaker thresholds, gRPC timeouts, and retry backoffs—which are entirely invisible to a static topological graph. Consequently, structural metrics associate poorly under degradation faults.

The failure of cross-architecture generalization (RQ4) likely stems from the fundamentally different roles that routing nodes play in architecturally distinct dependency topologies. In a hierarchical tree (Hotel Reservation), betweenness is zero for almost all nodes. In a cyclic mesh (Social Network), intermediate nodes form feedback loops where in-degree and betweenness carry distinct risks. A single static weighting formula cannot reconcile these distinct topological constraints.

### 6.2 Practical Implications
Despite these limitations, structural metrics remain operationally useful. Simple out-degree may serve as a low-cost screening signal for hard-failure scenarios, subject to validation in the target architecture. However, our findings caution against relying on static topology to estimate the impact of resource exhaustion, and suggest that "universal" structural criticality formulas proposed in prior literature may overfit to their specific evaluation architectures.

### 6.3 Threats to Validity
**Internal Validity:** The original study design contained target leakage during metric optimization; this was corrected in the final methodology via strict train/test segregation. 
**Construct Validity:** "Failure impact" is a multifaceted construct. We measured it via recovery time, latency, and downstream propagation, but did not measure business-level metrics.
**External Validity / Statistical Conclusion:** The Hotel Reservation architecture consists of only 7 services. Statistical correlations on $N=7$ are highly volatile. We mitigated this by reporting effect sizes ($\tau$, $\rho$) and emphasizing the failure of cross-architecture replication rather than relying on exploratory p-values. The results are strictly bounded to the evaluated topologies and the three specific fault injection mechanisms. 

---

## 7. Conclusion

This study investigated whether static service dependency topology associates reliably with empirically observed microservice failure impact. Through 171 valid controlled observations across two benchmark architectures, we demonstrated that structural centrality provides only a conditional proxy for blast radius. While out-degree exhibited a strong positive rank association with system recovery time during hard partition crashes, the strength of the topology-impact association varied across fault modalities, weakening under resource starvation faults. Furthermore, structural weighting models did not reliably transfer across structurally distinct architectural topologies. These results indicate that static topology alone provides an insufficiently stable basis for failure-impact prediction across heterogeneous fault modalities and architectural topologies.

---

## References

[1] A. Basiri, N. Behnam, R. de Rooij, L. Hochstein, L. Kosewski, J. Reynolds, and C. Rosenthal, "Chaos Engineering," *IEEE Software*, vol. 33, no. 3, pp. 35-41, 2016, doi: 10.1109/MS.2016.60.
[2] X. Zhou, X. Peng, T. Xie, J. Sun, C. Ji, W. Li, and D. Ding, "Fault Analysis and Debugging of Microservice Systems: Industrial Survey, Benchmark System, and Empirical Study," *IEEE Transactions on Software Engineering*, vol. 47, no. 2, pp. 243-260, 2021, doi: 10.1109/TSE.2019.2952589.
[3] Y. Gan et al., "An open-source benchmark suite for microservices and their hardware-software implications for cloud & edge systems," in *Proceedings of the 24th International Conference on Architectural Support for Programming Languages and Operating Systems (ASPLOS)*, pp. 3-18, 2019, doi: 10.1145/3297858.3304013.
[4] L. Ma et al., "MS-Rank: Multi-Metric and Self-Adaptive Root Cause Diagnosis for Microservice Applications," in *Proceedings of the IEEE International Conference on Web Services (ICWS)*, pp. 1-8, 2019, doi: 10.1109/ICWS.2019.00022.
[5] Y. Chen, Y. Jiang, and Y. Luo, "Modeling Cascading Failures in Microservice Architectures," in *Proceedings of the 21st IEEE/ACM International Symposium on Cluster, Cloud and Internet Computing (CCGrid)*, pp. 1-10, 2021, doi: 10.1109/CCGrid51090.2021.00032.
[6] T. Zimmermann, R. Premraj, and A. Zeller, "Predicting Defects for Eclipse," in *Proceedings of the Third International Workshop on Predictor Models in Software Engineering (PROMISE)*, p. 9, 2007, doi: 10.1109/PROMISE.2007.10.
[7] A. Rahman, R. Mahdavi-Hezaveh, and L. Williams, "A systematic mapping study of infrastructure as code research," *Information and Software Technology*, vol. 108, pp. 65-77, 2019. [VERIFY SPECIFIC CENTRALITY CITATION, this citation may refer to their empirical exploration if titled differently].
