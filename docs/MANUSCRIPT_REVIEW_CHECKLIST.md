# MANUSCRIPT REVIEW CHECKLIST

1. **What problem is being studied?** Using static graph topology to predict microservice failure impact.
2. **Why does it matter?** Essential for prioritizing chaos testing and resilience engineering without expensive empirical testing.
3. **What is genuinely missing from prior work?** Proactive empirical validation across different fault modalities and cross-architecture evaluation.
4. **What exactly was tested?** 7 structural metrics against recovery time and downstream impact under 3 fault types across 2 architectures (171 runs).
5. **Can the experiment be reproduced?** Yes, methodology details Pumba targets, durations, bare-metal specs, and graph definitions.
6. **Are statistical conclusions appropriate?** Yes. N=7 and N=12 limitations explicitly acknowledged; effect sizes emphasized over p-values.
7. **What did they discover?** Topology predicts impact conditionally; out-degree works for crashes but fails for CPU starvation. Static weights do not generalize.
8. **What did they fail to demonstrate?** The proposed hybrid fan-out metric did not universally outperform basic metrics.
9. **Why is the result useful?** It establishes boundaries on the usage of graph heuristics in practice, warning against blind application of structural algorithms for resource exhaustion faults.
10. **What are the limitations?** Small service counts (N=7, N=12), specific open-source benchmarks rather than industrial proprietary systems.
