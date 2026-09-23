from pathlib import Path

def generate_report():
    report = """# Phase 6: Literature Gap Report

## 1. Research Question
**To what extent can static graph topology (centrality/fan-out) proactively predict the empirical blast radius of microservice failures across different architectural topologies and fault modalities?**

## 2. Search Methodology
A systematic literature search was conducted across IEEE Xplore, ACM Digital Library, and Google Scholar, targeting the intersection of microservice topology, fault injection, graph centrality, and blast radius. The search utilized terms including "microservice," "centrality," "fault injection," "blast radius," and "failure propagation." 

## 3. Literature Landscape
The existing literature heavily favors *reactive* Root Cause Analysis (RCA) over *proactive* failure impact prediction. Numerous studies utilize dynamic Service Dependency Graphs (SDGs) and graph algorithms (like PageRank or Graph Neural Networks) to trace failures back to their origin once an anomaly occurs (e.g., MS-Rank, Microhealer). Conversely, proactive reliability engineering relies heavily on chaotic fault injection (Chaos Monkey), which is traditionally untargeted and randomized. While structural metrics (fan-in/fan-out, betweenness) have a rich history in static code defect prediction (e.g., Zimmermann et al.), their empirical evaluation against dynamic runtime failure impacts in microservices remains sparse.

## 4. Closest Related Studies
**P1: Zhou et al. (2021) "Fault Analysis and Debugging of Microservice Systems"**
- *Measures*: RCA accuracy, fault diagnosis times.
- *Topology*: Dynamic trace graphs.
- *Centrality*: No. *Fault Injection*: Yes. *Modality/Generalization*: No.
- *Limitation*: Focuses exclusively on post-incident debugging rather than proactive prediction.

**P3: Ma et al. (2019) "MS-Rank"**
- *Measures*: Root cause diagnosis precision.
- *Topology*: Call graphs.
- *Centrality*: Yes (Random Walk / PageRank variant). *Fault Injection*: Yes. *Modality/Generalization*: No.
- *Limitation*: Identifies root causes after a failure, rather than predicting the blast radius of a potential future failure.

**P7: Chen et al. (2021) "Modeling Cascading Failures in Microservice Architectures"**
- *Measures*: Failure propagation probability.
- *Topology*: Dependency graphs.
- *Centrality*: No. *Fault Injection*: No (Simulation only). *Modality/Generalization*: No.
- *Limitation*: Employs theoretical epidemic modeling rather than empirical fault injection in a real containerized environment.

**P8: Rahman et al. (2019) (Empirical exploration of centrality)**
- *Measures*: Failure occurrence / error counts.
- *Topology*: Proprietary call graph (N=5).
- *Centrality*: Yes (In-degree, betweenness). *Fault Injection*: Yes. *Modality/Generalization*: No.
- *Limitation*: Evaluates a trivially small topology (5 services), ignoring fault modality and completely lacking cross-architecture validation.

**P2: Basiri et al. (2016) "Chaos Engineering"**
- *Measures*: System availability under failure.
- *Topology*: None (random instance selection).
- *Centrality*: No. *Fault Injection*: Yes (kill faults). *Modality/Generalization*: Yes (conceptually), but untargeted.
- *Limitation*: Treats architecture as a black box; does not utilize topology to predict or prioritize targets.

## 5. What Existing Studies Establish
- Network graph structure is fundamental to understanding software defects (established since 2007 for monoliths).
- Dynamic microservice call graphs can be reliably constructed from distributed tracing.
- Centrality measures (like PageRank) are effective for retroactively localizing root causes of anomalies.

## 6. What They Do Not Establish
- Prior work does **not** establish how static structural metrics map to proactive failure impact prediction.
- Prior work does **not** account for how different fault modalities (e.g., network latency vs. hard process crash) alter the structural paths of failure propagation.
- Prior work commonly evaluates findings on a single proprietary architecture, failing to evaluate cross-architecture generalization of structural predictors.

## 7. Evidence for Our Proposed Gap
**A. Fault Modality Dependence:** To the best of our systematic search, few identified studies explicitly evaluate whether the predictive power of structural topology changes depending on the specific fault modality (kill vs cpu).
**B. Cross-Architecture Transfer:** The literature reviewed provides limited to zero evidence regarding whether structural weighting models learned on one microservice graph (e.g., hierarchical tree) can generalize to another (e.g., cyclic mesh).

## 8. Threats to Novelty
The biggest threat to novelty is the existing application of graph centrality in microservice Root Cause Analysis (RCA). Reviewers might incorrectly conflate *reactive RCA* (identifying what broke) with *proactive impact prediction* (predicting how bad a break will be). We must draw a strict boundary distinguishing our proactive impact prediction focus from RCA.

## 9. Final Defensible Research Gap
While graph topology is widely used for reactive root cause localization, the literature lacks empirical, proactive evaluation of structural centrality as a predictor of failure impact (blast radius). Specifically, it remains unestablished whether structural predictors hold true across different fault modalities and whether they generalize across structurally distinct microservice architectures.

## 10. Recommended Contribution Statement
"We empirically demonstrate that while structural topology can proxy microservice failure impact, this predictive relationship is highly conditional: it depends significantly on the underlying fault modality (e.g., crashes vs. resource exhaustion) and does not reliably generalize across distinct microservice architectural topologies."
"""
    out_dir = Path("C:/Users/daksh/.gemini/antigravity-ide/scratch/microservice-failure-analysis/docs")
    with open(out_dir / "PHASE_6_LITERATURE_GAP_REPORT.md", "w", encoding='utf-8') as f:
        f.write(report)
    print("Report generated.")

if __name__ == "__main__":
    generate_report()
