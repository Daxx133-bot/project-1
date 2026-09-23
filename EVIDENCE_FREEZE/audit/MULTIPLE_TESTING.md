# Phase 8.7: Multiple Testing Audit

## Exact Procedure Used in Phase 5

A forensic review of the original Phase 5 statistical scripts (`phase5c_validation.py`, `phase5c_fast.py`, `phase5b_analysis.py`) reveals the following:

- **Correction Applied:** None
- **Correction Method/Family:** N/A
- **Number of Tests Conducted:** The scripts iterated over 2 architectures $\times$ 3 faults $\times$ 7 centrality metrics $\times$ 2 target outcomes = **84 independent correlation tests**.
- **Adjusted p-values:** Not calculated.

**No multiple-testing correction was applied.**

## Consequence on Hotel Reservation CPU Claim

The previous Phase 5 reports noted that `out_degree` for Hotel Reservation CPU faults had a significant rank correlation ($\tau=-0.742, p=0.023$). 

However, given that 84 distinct, uncorrected permutation tests were executed simultaneously, the family-wise error rate (FWER) is profoundly inflated. If an appropriate FDR control (e.g., Benjamini-Hochberg) or FWER control (e.g., Bonferroni) were applied to this ensemble of tests, $p=0.023$ would universally fail to achieve significance at $\alpha=0.05$. 

Therefore, any claim resting on the significance of that specific result is statistically invalid in the context of the broader experimental design.
