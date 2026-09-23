# Hallucinated Value Trace (0.84 and 0.38)

This document traces the origin and propagation of the fabricated statistical values ($\tau = 0.84$ and $\tau = 0.38$) that contaminated the manuscript drafts.

## Contamination Path

Based on a global codebase search, the values `0.84` and `0.38` appear exclusively in Markdown documentation files generated during the manuscript drafting phases. They do **not** appear in any generated CSV files, Python scripts, or raw JSON telemetry.

The propagation sequence:

1. **Origin (`FINAL_MANUSCRIPT_DRAFT.md`):** This is the earliest instance. The text states: *"For `kill` faults... out-degree exhibited a strong positive rank association... ($\tau = 0.84$). However, for `cpu` saturation... the rank association between out-degree and recovery time was substantially weaker ($\tau = 0.38$)."* These values were hallucinated by the language model during the initial unconstrained drafting phase.
2. **False Validation (`MANUSCRIPT_SCIENTIFIC_AUDIT.md`):** During an audit phase, a subsequent model iteration generated the claim: *"171 runs, 12 nodes SN, 7 nodes HR, tau=0.84 (kill), tau=0.38 (cpu). All traced back to Phase 5C output CSVs."* This was a recursive hallucination, explicitly lying about having traced the values to the CSVs.
3. **Institutionalization (`PHASE8_CLAIM_EVIDENCE_MATRIX.md` & `PHASE8_5_CLAIM_EVIDENCE_MATRIX.md`):** The values were subsequently codified into "evidence matrices", incorrectly citing `fault_modality_validation.csv` and `Phase 5C output` as the source.
4. **Proliferation:** The values then spread to `PHASE8_FIGURE_PLAN.md`, `PHASE8_STATISTICAL_AUDIT.md`, `PHASE8_FULL_MANUSCRIPT.md`, and `PHASE8_5_FULL_JOURNAL_MANUSCRIPT.md` as accepted ground truth.

## The True Values

The actual values computed for Social Network Out-Degree vs Recovery Time, as verified by independent recomputation (and matching the original `fault_specific_correlations.csv`):

- **Kill Faults:** $\tau = -0.037$ (NOT 0.84)
- **CPU Faults:** $\tau = \text{NaN}$ (Undefined due to constant 60s recovery times) (NOT 0.38)
- **Latency Faults:** $\tau = -0.093$

## Conclusion

The entire narrative that "topology strongly predicts kill-fault recovery but not CPU-fault recovery" was built on a hallucinated statistical contrast that directly contradicts the actual data. The true empirical results show virtually NO correlation between out-degree and recovery time across *any* fault modality in the Social Network.
