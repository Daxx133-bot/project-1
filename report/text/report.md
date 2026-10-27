::lists

::abbreviations
ABBR | MEANING
BCa | Bias-corrected and accelerated (bootstrap interval)
BH | Benjamini-Hochberg (false discovery rate procedure)
CSV | Comma-separated values
DFD | Data flow diagram
FDR | False discovery rate
HC | Hybrid criticality (the fan-out-weighted metric of the original proposal)
HR | Hotel Reservation (DeathStarBench application)
p95, p99 | 95th and 99th latency percentiles
RPC | Remote procedure call
SN | Social Network (DeathStarBench application)
SRE | Site reliability engineering
WSL | Windows Subsystem for Linux

::abstract

Operators of microservice applications have to decide which services to harden first, and a tempting shortcut is to rank services by their place in the call graph instead of injecting faults into each one. A widespread intuition, and the starting point of this project, is that a service which calls many others is the most dangerous to lose. A failed service, however, mainly hurts the services that wait on it, which are its callers, so a ranking by callers could be the better guide.

This project tested both views with a fault-injection campaign on {{campaign_architectures|word}} applications of the DeathStarBench benchmark suite, Social Network and Hotel Reservation, deployed with Docker on a single laptop host. The hypotheses and every analysis choice were written down and locked before the campaign began. Dependency graphs were rebuilt from Jaeger traces, every analysable service received a process kill and a {{fault_latency_delay_ms}} ms network delay with {{campaign_reps_per_cell}} repetitions each, giving {{campaign_runs_total}} runs, and the latency and error rate of each service were measured on the spans that the service itself emits. Every degraded service was then classified as a caller (ancestor), a callee (descendant) or an unrelated service of the faulted one.

On Social Network under kill faults, the number of transitive callers of a service and the number of callers that degraded correlated at Spearman ρ = {{primary_rho}}, but none of the {{conf_family_size}} confirmatory tests survived Benjamini-Hochberg correction (adjusted p = {{primary_p_bh_locked}}), and the latency-fault replication gave the same verdict. Much of that correlation holds by construction, because most services degraded every caller they had. The fan-out-weighted centrality metric of the original proposal correlated negatively with degraded callers for both applications and both fault types, and in no case could it be told apart from zero. The clearest finding concerns direction: no callee of the faulted service degraded in {{descendant_affected_runs_zero}} of {{campaign_runs_total}} runs, so failures travelled to callers and almost never to callees.

The project therefore answers its title question mostly in the negative: the centrality metric it set out to validate did not identify the failure-prone services. It also shows that charging a request's end-to-end latency to every service on its path flags unrelated services, and it provides scripts that regenerate every number in this report from the logged data.

**Keywords:** microservices, fault injection, distributed tracing, graph centrality, failure propagation, preregistration.

::body

# 1. INTRODUCTION

## 1.1 Background

A microservice application is split into many small services that communicate over the network and can be developed, deployed and scaled independently [@dragoni2017; @jamshidi2018]. That independence is the reason teams adopt the style, but it moves complexity into operations: practitioners report real pains alongside the gains [@soldani2018], performance engineering for such systems still has open problems [@heinrich2017], and outage studies and industrial surveys show that failures in service-based systems are frequent and slow to diagnose [@gunawi2016; @zhou2021]. When one service fails, the effect can spread through the services that depend on it.

Distributed tracing records, for each request, which service called which, so the call graph of a running application can be recovered from its traces [@sigelman2010]. Graph theory offers many measures of how central a node is [@freeman1978], and network measures computed on software dependency graphs have helped predict where defects occur [@zimmermann2008]. This suggests reading a service's risk from its position in the call graph.

## 1.2 Motivations

The direct way to learn which service does the most damage when it fails is to inject faults into every service, once for each fault type and with repetitions. That is slow and costly on a large system. A ranking computed from the call graph would be almost free, so it is worth knowing whether such a ranking can be trusted.

The project began with a specific ranking: a hybrid criticality metric that boosts out-degree centrality by fan-out, on the argument that a service calling many others cuts many links when it fails. There is an argument in the opposite direction. When a service fails, the services left waiting are the ones that call it; the services it calls simply receive less traffic. If that is right, the number of services that degrade should follow a service's callers, and a fan-out ranking would be wrong exactly for the services it rates highest. Settling this question with measurement, rather than with intuition, was the motivation for the project.

## 1.3 Scope of the Project

The study covers the Social Network and Hotel Reservation applications of DeathStarBench [@gan2019], built from one pinned commit and run with Docker Compose on a single laptop host, one application at a time. {{campaign_fault_types|word}} fault types were used: a process kill and an injected network delay. Load came from a synthetic workload with a fixed request mix. The call graphs were reconstructed from traces collected under that workload.

Outside the scope are production systems, Kubernetes orchestration, multi-host deployments, containment mechanisms such as retries and circuit breakers, and fault types other than kill and delay. CPU contention was tried in the pilot and dropped because its effect was too small to classify reliably. The results describe these two benchmark applications under this workload and are not a claim about production behaviour.

## 1.4 Changes Since the Review-2 Draft

The draft report presented at Review 2 reported strong correlations between centrality metrics and failure impact. After that review, an audit of the project's own pipeline found that those results were not supported by measurement: part of the measurement log consumed by the correlation scripts had been generated by a script rather than measured, the recovery-time column did not measure what its definition said, and the metric weights had been chosen by searching for the weighting that maximised the same correlation that was then reported.

The preliminary results of the Review-2 draft are therefore withdrawn. The affected files were moved to a quarantine folder rather than deleted ({{quarantine_items}} items, each with a note of why), the measurement code was corrected, the hypotheses and analysis were locked in advance, and a new campaign was run. Everything in this report comes from that new campaign. The registered project title is kept unchanged as required, but it should be read as the question the project tested; the answer, as Chapter 7 shows, is largely negative.

# 2. PROJECT DESCRIPTION AND GOALS

## 2.1 Literature Review

**Microservices and their operation.** Dragoni and colleagues trace the evolution of the microservice style and define its main traits [@dragoni2017], and Jamshidi and colleagues review its history and the challenges ahead [@jamshidi2018]. A systematic review of grey literature collects the pains and gains reported by practitioners [@soldani2018], and Heinrich and colleagues set out research challenges in performance engineering for microservices [@heinrich2017]. On failures, Gunawi and colleagues draw lessons from hundreds of cloud service outages [@gunawi2016], and Zhou and colleagues combine an industrial survey of fault analysis in microservice systems with a benchmark system and an empirical study [@zhou2021]. The applications studied here come from DeathStarBench, an open-source suite of end-to-end microservice benchmarks [@gan2019].

**Graph measures.** Freeman clarified several distinct notions of centrality, from direct ties to shortest paths, and gave them normalised forms [@freeman1978]. Brandes made betweenness practical on large graphs with a faster algorithm [@brandes2001]. Bonacich proposed a family of power-based centrality measures related to eigenvector centrality [@bonacich1987], PageRank came from the design of a web search engine [@brin1998], and Lengauer and Tarjan gave a fast algorithm for dominators in flow graphs [@lengauer1979]. The NetworkX library used here implements these measures [@hagberg2008].

**Robustness of networks.** Albert, Jeong and Barabási studied how complex networks tolerate random errors and targeted attacks [@albert2000], and Motter and Lai examined attacks that act through cascades [@motter2002]. These studies remove nodes from a graph; in a running microservice system the failed service stays in the graph and its effect shows up as latency and errors in other services, which must be measured on the running system.

**Graphs in software engineering.** Zimmermann and Nagappan showed that network measures on the dependency graph of a large system help predict which components contain defects [@zimmermann2008]. Ma and colleagues built a service dependency graph to analyse and test microservice systems [@ma2018]. This project shares the premise that position in a dependency graph carries information about risk, but its outcome is the run-time spread of a failure under load.

**Fault injection and chaos engineering.** Basiri and colleagues describe chaos engineering at Netflix, where controlled experiments build confidence that a system tolerates failure [@basiri2016], and later its automation in production [@basiri2019]. Gremlin tests the resilience of microservices by injecting faults between services [@heorhiadi2016], and Meiklejohn and colleagues bring fault injection testing down to individual services [@meiklejohn2021]. Lineage-driven fault injection reasons backwards from a correct outcome to choose the faults most likely to break it [@alvaro2015]. Huang and colleagues describe gray failure, where a component keeps running but works badly [@huang2017]; an injected delay is a controlled form of such a partial failure. These tools look for bugs or check fallbacks; here faults are used as a measuring instrument in a fixed, balanced design.

**Tracing and call graphs.** Dapper introduced the span model followed by most tracing systems, in which a request becomes a tree of spans with parent links [@sigelman2010]; the parent-child links between spans of different services give the caller-to-callee edges used in this project. Luo and colleagues found that call graphs in Alibaba's production traces are highly dynamic [@luo2021], a reminder that a graph built from traces depends on the traffic that produced it.

**Failure diagnosis.** Pinpoint addressed problem determination in large Internet services [@chen2002]. For microservices, Microscope locates performance problems using causal graphs [@lin2018], MicroRCA ranks candidate root causes on a graph of the running system [@wu2020], and Seer applies large-scale data analysis to performance debugging [@gan2019seer]. Soldani and Brogi survey anomaly detection and root-cause analysis for service-based cloud applications [@soldani2022]. These methods start after an anomaly has begun; this project asks whether graph structure alone, before any fault, indicates which services matter most.

**Statistical method.** Preregistration separates planned analyses from those found after seeing the data [@nosek2018]. The Benjamini-Hochberg procedure controls the false discovery rate across a family of tests [@benjamini1995]. Permutation p-values should never be zero, which is ensured by adding one to both counts [@phipson2010]. Bias-corrected and accelerated bootstrap intervals [@efron1987] and the Cox proportional hazards model [@cox1972] complete the toolkit used here.

## 2.2 Research Gap

Graph measures have been used to rank software components by defect risk, network studies examine tolerance to node loss, fault-injection tools test whether systems survive failures, and diagnosis methods use the graph once an anomaly is under way. Among the works reviewed, none reports a test, fixed in advance, of whether a graph-derived ranking of services anticipates how far failures spread when they are measured in a controlled campaign. In particular, the common fan-out intuition and the opposing caller-based argument had not been compared against measured outcomes with a correction for the many tests involved. This project fills that gap, and reports the result even though it came out null.

## 2.3 Objectives

- Reconstruct the call graph of each application from traces of the running system rather than from documentation, and freeze it as a file.
- Compute, for every service, the caller count (number of transitive callers), the hybrid criticality metric of the original proposal and further graph measures as comparators.
- Write down and lock the hypotheses, outcomes, thresholds and statistical tests before collecting any campaign data, and log every later change as a dated deviation.
- Run a fully crossed, balanced fault-injection campaign in which every analysable service receives each fault type the same number of times.
- Measure latency and error rate per service on that service's own spans, and classify every degraded service by its graph relation to the faulted one.
- Test whether the caller count (H1) or the hybrid metric (H2) tracks the number of degraded callers, with permutation tests and Benjamini-Hochberg correction.
- Make every number in the report reproducible by a script from the logged data.

## 2.4 Problem Statement

Let the call graph of an application have the services as nodes and an edge from u to v when u calls v under the traced workload. The ancestors of a service v are all services from which v can be reached (its transitive callers) and its descendants are all services v can reach (its transitive callees). When a fault is applied to v, the degraded set is the set of other services whose own latency or error rate crosses the degradation rule during the fault window. The primary outcome *Y* of a service is the median, over its repetitions, of the number of degraded ancestors; degraded descendants and degraded unrelated services are counted separately and never added to *Y*.

The problem is to find out whether a graph property of a service, known before any fault, predicts *Y*. The primary predictor *X* is the caller count. The comparator of interest is the hybrid criticality metric HC, which adds weighted in-degree centrality, out-degree centrality scaled by the service's share of the maximum out-degree, and betweenness centrality, with weights {{hybrid_w_in}}, {{hybrid_w_out}} and {{hybrid_w_btw}}. Hypothesis H1 states that *X* is positively correlated with *Y*. Hypothesis H2 states that HC is not positively correlated with *Y*, that is, that the fan-out premise points the wrong way.

## 2.5 Project Plan

The project timeline is shown in [[fig_gantt]]. It is built by a script from the dates of the commits in the project repository, so it shows what was actually done and when, rather than a plan drawn afterwards. Work before the first commit, such as topic selection and the first review, left no dated record in the repository and is not shown. The audit, the rebuilt pipeline, the pilot, the locked plan and the campaign took place within a few days of one another, after which the analysis and the write-up followed.

::figure report/figures/fig_gantt.png | Project timeline, built from the dates of the repository's commits; each phase ends at a milestone commit.

# 3. TECHNICAL SPECIFICATION

## 3.1 Requirements

### 3.1.1 Functional

- Trace collection: query the Jaeger API for the traces of each application service and store the raw spans.
- Graph reconstruction: build a directed caller-to-callee graph from parent-child span links between different services, and save it as a frozen file.
- Predictor computation: compute the caller count, descendant count, hybrid criticality, degree-based, path-based and spectral centralities and dominator subtree size for every service.
- Target resolution: find the container to fault as the single container whose compose service label equals the service name, and stop if none or several match.
- Fault injection: apply a kill (SIGKILL) or a network delay with jitter through Pumba, hold it for a fixed time, and restore the service afterwards.
- Per-service measurement: compute each service's latency percentiles and error rate from its own spans in the baseline and fault windows.
- Blast-radius classification: split the degraded services into ancestors, descendants and unrelated services of the faulted one.
- Recovery probe: measure the time from fault removal until all indicators are back within tolerance of the baseline, or record the run as censored.
- Run records: write one record per run, with the raw spans of the baseline and fault windows stored alongside.
- Integrity gates: before any statistics, confirm that every expected service was present in every run and that no baseline was anomalous.
- Statistical analysis: compute Spearman correlations with permutation p-values, bootstrap intervals and Benjamini-Hochberg correction within each test family.
- Reproducibility: regenerate every number, table and figure from the logged data with one build command.

### 3.1.2 Non-Functional

- Integrity: no measurement, impact value or recovery time may be generated rather than measured; a value that cannot be traced to a script and an input file is reported as missing.
- Reproducibility: the benchmark code is pinned to one upstream commit ({{dsb_commit}}), and raw spans are kept so that any metric can be recomputed without re-running the experiment.
- Isolation: only one application stack runs at a time, and a lock file prevents two runs from overlapping.
- Robustness: the campaign runner is resumable after a crash and repeats a run with incomplete telemetry in its own cell, never filling it in.
- Traceability: every number in the paper and in this report carries a claim id that names its source file and script.
- Safety: faults are injected only into local containers of the benchmark applications; no production system or real user data is involved.

## 3.2 Feasibility Study

### 3.2.1 Technical Feasibility

All components are mature open-source tools: Docker and Docker Compose for deployment, Jaeger for tracing, Locust for load, Pumba for fault injection, and Python with NetworkX, SciPy and statsmodels for analysis. The whole campaign ran on one laptop, with the two stacks brought up one at a time to stay within the memory available to Docker. The {{campaign_runs_total}} campaign runs took about {{campaign_duration_hours}} hours of wall-clock time, so the experiment is feasible without a cluster.

### 3.2.2 Economic Feasibility

No licence fees or cloud resources were needed. The software is open source, Docker Desktop is free for educational use, and the experiments ran on the author's own laptop. The only cost is computing time on an existing machine, which makes the method affordable for a student project and easy for others to repeat.

### 3.2.3 Social Feasibility

The experiments use public benchmark applications in an isolated local environment, so no real users or personal data are affected. The findings are relevant to operations teams who must decide where to spend resilience effort. Reporting a null result honestly, instead of presenting a favourable one, is itself part of the project's contribution to sound practice.

## 3.3 System Specification

### 3.3.1 Hardware Specification

::table tbl_ieee_testbed | Hardware of the test host | Host OS;Host CPU;Host RAM (GB);Docker VM memory (GiB);Containers per stack

### 3.3.2 Software Specification

::table tbl_ieee_testbed | Software used, with versions as recorded | Docker Desktop;Docker client / Compose;DeathStarBench commit;Jaeger;Pumba;Python;Python libraries;Locust

# 4. DESIGN APPROACH AND DETAILS

## 4.1 System Architecture

The test bed is a single Windows host. The application stack, the Jaeger tracing backend and the Pumba fault injector run as containers inside the virtual machine of Docker Desktop's WSL2 backend, while the Locust load generator and the campaign runner run on the host ([[fig_deployment]]). The Social Network stack has {{testbed_containers_sn}} containers and the Hotel Reservation stack {{testbed_containers_hr}}; the runner never runs both at once.

::figure paper/figures/fig_deployment.png | Deployment of the test bed: the host, the Docker virtual machine with the application, Jaeger and Pumba containers, and the load generator and campaign runner on the host.

The software is organised as a pipeline ([[fig_pipeline]]). The first steps build the dependency graphs and predictors and lock the plan before any campaign data exist; the middle steps repeat in every run; the final steps run once the campaign is complete. Each box names the files that implement the step.

::figure paper/figures/fig_pipeline.png | Pipeline in execution order, with the repository files that carry out each step.

## 4.2 Design

### 4.2.1 Data Flow Diagram

At the context level ([[fig_dfd_level0]]) the pipeline exchanges data with its external entities: the researcher, who supplies the locked plan and the run manifest and receives the results; the application stack, which receives load, fault and restore commands; and the Jaeger backend, which supplies the spans that the services emit.

::figure report/figures/fig_dfd_level0.png | Data flow diagram, Level 0 (context diagram).

At Level 1 ([[fig_dfd_level1]]) the pipeline splits into processes 1.0 to 6.0. Graph reconstruction (1.0) and predictor computation (2.0) run before the campaign. For every entry of the run manifest, process 3.0 drives one run while process 4.0 measures its outcome from the spans and writes a run record. Statistical analysis (5.0) reads all run records and the predictor table, and the build step (6.0) turns the analysis outputs into the numbers, tables and figures of the paper and this report.

::figure report/figures/fig_dfd_level1.png | Data flow diagram, Level 1. Data stores D1 to D6 are folders and files of the repository.

### 4.2.2 Use Case Diagram

[[fig_use_case]] shows the actors. The researcher locks the plan, reconstructs the graphs, runs the campaign (which includes injecting a fault and measuring its effect) and checks run integrity. A reviewer can rerun the confirmatory analysis, regenerate every number, table and figure, and inspect the stored run records and spans without access to the test bed.

::figure report/figures/fig_use_case.png | Use case diagram.

### 4.2.3 Class Diagram

The pipeline is written as Python modules of functions that pass plain data (graphs, dictionaries and CSV rows) between steps; the only classes are small helpers such as the run lock and the recovery-probe result. A class diagram would therefore add little, and the module structure is described by [[fig_pipeline]] and the data flow diagrams instead.

### 4.2.4 Sequence Diagram

[[fig_sequence]] shows the messages exchanged in one campaign run. W is the warm-up and baseline window, H the fault hold, P the recovery-probe interval and C the recovery cap; their values are given in Section 5.1.3.

::figure report/figures/fig_sequence.png | Sequence diagram of one campaign run (function one_run in tools/run_pilot.py).

# 5. METHODOLOGY AND TESTING

## 5.1 Module Description

### 5.1.1 Graph Reconstruction Module

`tools/extract_graph.py` asks Jaeger for the traces of every application service and adds a directed edge from service a to service b whenever a span of a is the parent of a span of b. The Social Network graph was built from {{graph_sn_traces_examined}} traces holding {{graph_sn_spans_examined}} spans, and the Hotel Reservation graph from {{graph_hr_traces_examined}} traces holding {{graph_hr_spans_examined}} spans. The graphs have {{graph_sn_nodes}} and {{graph_hr_nodes}} services with {{graph_sn_edges}} and {{graph_hr_edges}} edges ([[fig_graph_sn]] and [[fig_graph_hr]]). Graphs from traces show the calls the system actually makes: for Hotel Reservation, the traces recover {{hr_manifest_edges_recovered}} of the {{hr_manifest_expected_edges}} call edges implied by its documentation, and the observed graph was used.

::figure paper/figures/fig_graph_sn.png | Social Network dependency graph as observed in traces, with the gateway marked.

::figure paper/figures/fig_graph_hr.png | Hotel Reservation dependency graph as observed in traces, with the gateway marked.

The gateway of each application (nginx-web-server and frontend) has no caller in the graph, because its traffic comes from the load generator, so it is left out of every correlation. That leaves {{sn_services}} services in Social Network and {{hr_services}} in Hotel Reservation.

### 5.1.2 Predictor Module

`tools/build_predictor_table.py` and `centrality/compute_centrality.py` compute the caller count, the hybrid metric and the comparators: degree, in-degree, out-degree, betweenness, closeness, eigenvector centrality, PageRank, a composite rank, descendant count and dominator subtree size. The hybrid metric keeps the weights of the original proposal; the tuning step planned in the preregistration was never run (Deviation 10), and no weight was re-tuned on campaign data. Where a predictor is constant across services, as eigenvector centrality is on the acyclic Social Network graph, the correlation is undefined, so {{degenerate_pairs|word}} such pairs were declared degenerate in advance, leaving {{testable_pairs}} testable pairs.

### 5.1.3 Run and Fault-Injection Module

`tools/run_campaign.py` works through the run manifest and calls `one_run` in `tools/run_pilot.py` for each run. Locust starts {{protocol_load_users}} users at {{protocol_spawn_rate}} per second, each waiting between {{protocol_sn_wait_min_s}} and {{protocol_sn_wait_max_s}} s between requests drawn from a fixed weighted mix. After {{protocol_warmup_s}} s, which also serve as the baseline window (W), the fault is applied and held for {{protocol_fault_duration_s}} s (H). A kill fault sends {{fault_kill_signal}}; a latency fault adds {{fault_latency_delay_ms}} ms of delay with {{fault_latency_jitter_ms}} ms of jitter through a netem rule. The recovery probe then polls every {{trec_poll_interval_nominal_s}} s (P), with a cap of {{protocol_recovery_cap_s}} s (C), and a {{protocol_cooldown_s}} s cooldown separates runs. The exact commands, generated from the runner code, are listed in [[tbl_ieee_commands]].

::table tbl_ieee_commands | Commands issued by the runner in each run

### 5.1.4 Measurement Module

`measurement/metrics_collector.py` computes each service's latency percentiles and error rate from the spans that service emits itself. This choice matters. A tracing backend returns, for a service, every trace that touches it, and the root span of each trace times the whole request; a percentile over root spans therefore gives every service on a request path the same end-to-end value. In {{q3_pilot_runs|word}} pilot runs on Hotel Reservation with a delay in the search service, that shortcut flagged several services that were not faulted, some of them neither callers nor callees of search; per-service attribution flagged only one, an actual caller of search ([[fig_q3_artifact]]).

::figure paper/figures/fig_q3_artifact.png | Per-service p95 under a latency fault in search, measured on the end-to-end root span (left) and on each service's own spans (right); an asterisk marks a service flagged as degraded.

A service counts as degraded when its p95 exceeds {{threshold_degradation_factor}} times its baseline and rises by at least {{threshold_degradation_floor_ms}} ms, or when its error rate rises by at least {{threshold_error_rate_abs}}. `measurement/blast_radius.py` then splits the degraded services into ancestors, descendants and unrelated services of the faulted one (Appendix A). `measurement/recovery_probe.py` measures recovery time from fault removal until p95, p99, error rate and the affected count are all within {{protocol_recovery_tolerance_pct}}% of baseline for {{protocol_confirm_s}} s; a run that does not recover within the cap is recorded as censored, never filled in.

### 5.1.5 Analysis Module

`analysis/final/run_confirmatory_analysis.py` takes the median outcome of each service over its repetitions and computes Spearman's ρ between each predictor and each outcome. P-values come from permutation tests ({{primary_n_permutations}} random permutations where exact enumeration is impractical), intervals from the bias-corrected and accelerated bootstrap, and each family of tests is corrected with the Benjamini-Hochberg procedure at q = {{fdr_q}}. Kill faults form the confirmatory family of {{conf_family_size}} tests, and latency faults repeat every test as a replication family of {{repl_family_size}}.

### 5.1.6 Preregistration and Deviations

The hypotheses and analysis were locked before the campaign, and every later change was logged with its date ([[tbl_ieee_deviations]]). Of the {{deviations_total}} deviations, {{deviations_no_data}} invalidated no data; the other {{deviations_with_data|word}} invalidated {{deviations_runs_invalidated}} runs, each of which was collected again in its own cell, so the final data set is complete and balanced.

::table tbl_ieee_deviations | Deviations from the locked plan

## 5.2 Testing

Testing worked at several levels.

**Unit tests.** The repository has a pytest suite covering the statistics, the degradation rule and per-service metrics, container resolution, the recovery probe, the structural metrics, the campaign runner and the report and reference builders. With the Docker-dependent integration tests deselected, {{pytest_passed}} tests passed and {{pytest_failed}} failed in the run made for this report; {{pytest_deselected}} integration tests need the live stacks and were not run.

**Pre-analysis integrity gates.** Before any statistic was computed, one gate confirmed that every expected service was present in every run and another compared each run's fault-free baseline with all other runs using the median and the median absolute deviation. All {{integrity_checks_total}} checks passed. These gates are what exposed Deviation 4, a delay rule that outlived its run.

**Verification of the analysis.** An independent reimplementation of the primary statistic, written without reference to the analysis code and reading only the stored spans and the graph, reproduced the reported correlation and agreed on which services were affected in all {{sn_runs}} Social Network runs. A replay restricted to server spans changed {{replay_runs_changed}} of {{replay_runs}} run outcomes and none of the service-level medians. A leave-one-out recomputation is reported with the results.

# 6. PROJECT DEMONSTRATION

The project can be demonstrated in stages. The first needs only the repository and shows that every result follows from the logged data:

- `python -m pytest -q -m "not integration"` runs the unit tests.
- `python analysis/final/run_confirmatory_analysis.py` reruns the full preregistered analysis from the run records.
- `python paper/build_all.py` regenerates `paper/numbers.csv`, the tables and the figures, and fails if any claim in the paper does not resolve to a row.

The second needs Docker and the DeathStarBench checkout, and shows the live experiment:

- `python tools/run_campaign.py --status` shows the run manifest and which runs are pending.
- `python tools/run_campaign.py --max-runs 1` executes one run: the load starts, the fault is applied to the target container, the degraded services are listed by relation, the recovery probe runs, and a run record is written to `data/campaign/runs/`.

Each row of `paper/numbers.csv` names a claim, its value, its unit, the file it was read from and the script that produced it. This report is itself built the same way: `python report/build_report.py` fills every number in the text from those rows and refuses to build if a number was typed by hand.

# 7. RESULT AND DISCUSSION

## 7.1 Campaign Completion

All {{campaign_runs_total}} planned runs completed across {{campaign_cells}} balanced cells, {{sn_runs}} on Social Network and {{hr_runs}} on Hotel Reservation. No run was lost to telemetry failure and no recovery time was censored. The campaign ran from {{campaign_start_utc}} to {{campaign_end_utc}} UTC. [[tbl_ieee_predictors_sn]] lists the graph predictors and measured outcomes of the Social Network services.

::table tbl_ieee_predictors_sn | Graph predictors and measured outcomes, Social Network | | 0,1,2,3,4,5,10,11,12,13

## 7.2 The Caller Count (H1)

On Social Network under kill faults, the caller count *X* and the number of degraded callers *Y* correlated at ρ = {{primary_rho}} across {{primary_n_services}} services, with a bootstrap interval from {{primary_ci_lo}} to {{primary_ci_hi}}. The uncorrected p-value was {{primary_p_locked}}, but after correction across the {{conf_family_size}} tests of the confirmatory family it became {{primary_p_bh_locked}}. None of the confirmatory tests was significant ([[tbl_ieee_primary]]), so H1 is not confirmed.

::table tbl_ieee_primary | The primary test in each family and application

The correlation is also partly definitional. *Y* counts degraded callers and *X* counts callers, so *Y* can never exceed *X*, and when every caller degrades the two coincide. On Hotel Reservation this happened for every service in every run, so its results only restate the predictor and are treated as directional. On Social Network, all but one of the {{sn_services}} services lay exactly on the line *y = x* ([[fig_primary_sn]]); only user-service, with {{userservice_ancestor_count}} callers of which {{userservice_measured}} degraded in every kill run, departed from it. Withholding one service at a time moves ρ between {{loo_rho_min}} and {{loo_rho_max}} ([[fig_leave_one_out]]), and withholding user-service gives {{loo_userservice_rho}}.

::figure paper/figures/fig_primary_sn.png | Caller count X against the measured number of degraded callers Y for each Social Network service; points on the dashed line are saturated.

::figure paper/figures/fig_leave_one_out.png | Leave-one-out check (post hoc): ρ between X and Y on Social Network under kill faults, with each service withheld in turn.

## 7.3 The Fan-Out Metric (H2)

The hybrid criticality metric correlated negatively with degraded callers in every application and fault type: ρ = {{h1b_sn_kill_rho}} on Social Network and ρ = {{h1b_hr_kill_rho}} on Hotel Reservation ([[tbl_ieee_h2]]). After correction no cell could be told apart from zero, so no negative relationship is claimed; the data simply give the fan-out premise no support.

::table tbl_ieee_h2 | The hybrid criticality metric against degraded callers

The case that motivated the metric shows why. compose-post-service calls {{composepost_out_degree}} services directly and has {{composepost_descendants}} descendants, so the hybrid metric ranks it first of {{composepost_set_size}}; by callers it ranks last, with a single caller ([[fig_rank_inversion]]). In all {{composepost_runs_total}} of its runs exactly one caller degraded, and that caller was always the gateway.

::figure paper/figures/fig_rank_inversion.png | Rank of each Social Network service by the hybrid metric and by caller count, with compose-post-service highlighted.

A sweep over all {{ws_triplets}} weightings on the preregistered grid, run after the confirmatory results were known, found no weighting with a significant association with degraded callers ([[fig_weight_sensitivity]]), so the null result does not depend on the inherited weights.

::figure paper/figures/fig_weight_sensitivity.png | Post hoc weight sensitivity: ρ of the hybrid metric against degraded callers and against gateway error rate for every weight triplet.

## 7.4 Replication and Direction of Propagation

The latency-fault replication family also had no significant test after correction; its smallest adjusted p-value was {{repl_best_bh_p}}. Which services degraded hardly depended on how the fault was delivered: {{fault_invariant_services_all}} of {{fault_invariant_services_all_total}} services showed identical per-run counts under kill and delay.

The clearest result is the direction of propagation. No descendant of the faulted service degraded in {{descendant_affected_runs_zero}} of {{campaign_runs_total}} runs, and unrelated services stayed unaffected in {{unrelated_affected_runs_zero}} of {{campaign_runs_total}}. A failure travelled up to the services that wait on the failed one and almost never down to the services it calls. This is consistent with the reasoning in Section 1.2: a callee of a dead or slow service simply receives fewer requests.

## 7.5 Limits of the Design

With the service as the unit of analysis, the sample sizes are {{power_sn_n}} and {{power_hr_n}} services, and the caller count takes only {{power_sn_levels|word}} and {{power_hr_levels|word}} distinct values. These ties cap the correlation an untied outcome could reach at {{power_sn_ceiling}} and {{power_hr_ceiling}} ([[tbl_ieee_power]]). On Hotel Reservation even that ceiling gives a p-value of {{power_hr_ceiling_p}}, above the usual threshold before any correction, so that application could not have produced a significant result on its own. These limits were computed before data collection.

::table tbl_ieee_power | What the design could detect

Recovery time showed no significant association with either predictor in either family. Observed recovery times ranged from {{trec_min_s}} to {{trec_max_s}} s, with a median of {{trec_median_s}} s.

## 7.6 Discussion

The findings point towards looking up the graph, at callers, and away from looking down it, at callees, when ranking services for hardening. The caveat is important: the project's own test of the caller ranking did not reach significance, so it is not claimed that the caller count predicts failure impact. In an exploratory analysis, the error rate seen at the gateway followed the share of traffic that passed through the failed service, which suggests that a ranking weighting callers by traffic is worth testing as a new, preregistered hypothesis.

Measurement also taught lessons. Attributing latency per service, rather than charging end-to-end latency to every service on a path, changed which services counted as degraded. And a structural predictor tested against a structurally defined outcome needs a saturation measure next to the correlation; without it, a high ρ can look like evidence when it mostly restates the definition.

The main threats to validity are the small number of services, the single benchmark suite and workload, a call graph that depends on the traffic used to build it, and fault types limited to a kill and a delay.

## 7.7 Cost Analysis

The project incurred no monetary cost. All software is open source or free for educational use, and the experiments ran on the author's laptop without cloud resources. The main cost was machine time: the campaign itself took about {{campaign_duration_hours}} hours, and the full analysis can be rerun from the stored data without Docker.

# 8. CONCLUSION

The project set out to identify failure-prone microservices from graph centrality metrics, and tested that idea with a preregistered fault-injection campaign of {{campaign_runs_total}} balanced runs on {{campaign_architectures|word}} benchmark applications. The centrality metric the project began with, which favours services with high fan-out, did not identify the services whose failure did the most damage: its correlation with degraded callers was negative everywhere and never distinguishable from zero. The caller count correlated strongly with degraded callers on Social Network, but no test survived correction, and much of that correlation follows from how the outcome is defined.

What held without any statistical test is the direction of propagation: failures reached callers and almost never callees. The project also showed that per-service latency attribution is essential when traces are used to judge which services degrade, and it rebuilt its pipeline so that every number can be regenerated from logged data after an audit of the earlier version.

Future work follows from these results: test a ranking of services by callers weighted by the traffic they carry, as a new preregistered hypothesis; use larger applications to lift the ceiling that a handful of services place on any correlation; and study how containment mechanisms such as retries and circuit breakers change how far a failure travels. A manuscript describing the study has been prepared for submission to IEEE Access.

# 9. REFERENCES

::references

# APPENDIX A – SAMPLE CODE

The function below classifies the services that degraded in a run by their relation to the faulted service. It is read from the repository when this report is built, so it matches the code that produced the results.

::code measurement/blast_radius.py | classify_affected
