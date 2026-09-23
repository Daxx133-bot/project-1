# MANUSCRIPT SCIENTIFIC AUDIT

## 1. Substantive Corrections Made
- **Predictive Language:** Replaced "predicts" and "prediction accuracy" with "structural proxy," "rank association," and "held-out generalization." Only retained "predictor" in a conceptual sense.
- **Statistical Language:** Removed "significantly" when discussing H2 variance, as we did not calculate interaction terms between tau coefficients. Replaced with "The strength of the topology-impact association varied..."
- **Independence Language:** Audited all 171 instances. Exclusively refer to "171 valid controlled observations" rather than "independent experimental runs." Added explicit language in Section 4.6 explaining the service-level analytical unit.
- **Recovery Time:** Revised methodology to explicitly detail the 10% tolerance threshold, the 10-second stability requirement, and the 60-second cap based on implementation logic.
- **Fan-out:** Corrected "quadratic" phrasing to "multiplicative fan-out correction based on normalized out-degree."
- **Architecture Descriptions:** Replaced subjective graph terms with objective edge/node counts, max depth, and generic labels like "architecturally distinct dependency topologies".
- **Zero-trace:** Revised conclusion to neutrally state that severe-fault runs with no trace heavily influenced the association, removing the claim that topology intrinsically predicts catastrophic states over latency.

## 2. Claims Weakened
- Weakened H3 conclusion from "universally improves" to "does not consistently outperform."
- Weakened general applicability in Practical Implications. Emphasized that it's a "low cost screening signal... subject to validation".
- Weakened H4 from "fail completely" to "did not reliably transfer."
- Weakened Conclusion statement from demanding fault-aware models to stating that static topology is "insufficiently stable."

## 3. Numerical Claims Verified
- 171 runs, 12 nodes SN, 7 nodes HR, tau=0.84 (kill), tau=0.38 (cpu). All traced back to Phase 5C output CSVs.

## 4. References Verified
- Corrected MS-Rank DOI to 10.1109/ICWS.2019.00022.
- Verified Zimmermann et al. (PROMISE 2007). Modified citation text to specify that it analyzed "static source code dependency graphs" mapped to "post-release defect density for Eclipse plugins," matching the paper exactly.

## 5. Remaining [VERIFY] Items
- The specific Rahman et al. citation concerning microservice centrality empirical outcomes. (Ref 7). The prior draft text referred to a specific 5-service proprietary finding that might be from a different Rahman paper or pre-print.

## 6. Remaining Methodological Uncertainties
- None directly contradictory to the findings, though the $N=7$ Hotel Reservation statistical power remains fundamentally limited, which is extensively caveated.

## 7. Final Contribution Statement
"This study empirically demonstrates that structural centrality provides only a conditional proxy for microservice failure impact: its predictive relationship varies by fault modality, and static structural weighting does not reliably generalize across distinct architecture topologies."
