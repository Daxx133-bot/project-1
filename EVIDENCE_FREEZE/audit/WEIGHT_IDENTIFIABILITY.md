# Cross-Architecture Weight Identifiability Audit

This document traces the implementation of the cross-architecture optimization logic in `EVIDENCE_FREEZE/implementation/hybrid_weight_optimizer.py` and `phase5b_analysis.py`.

## The Objective Function
The grid search attempts to find optimal weights ($W_1, W_2, W_3$) for the hybrid metric:
$S_{hybrid} = W_1(\text{In-Degree}) + W_2(\text{Fan-Out}) + W_3(\text{Betweenness})$

subject to $W_1 + W_2 + W_3 = 1.0$.

The optimization objective is to maximize the absolute Spearman rank correlation $|\rho|$ between the hybrid score and empirical recovery time on a training architecture (Social Network).

## Identifiability Analysis

1. **Rank Degeneracy:** The Social Network training architecture contains only 12 services (N=12). The objective function optimizes a *rank* correlation. Because degree and betweenness take on a very small set of discrete values across only 12 nodes, there are massive, contiguous regions of the parameter space $(W_1, W_2, W_3)$ that produce the **exact same rank ordering** of those 12 services.
2. **Tie-Breaking:** The original Phase 5 optimization logic used a strict inequality `abs(rho) > best_rho`. If multiple weight combinations produce the exact same maximal Spearman $\rho$, the algorithm simply keeps the **first** one it encountered in its arbitrary nested loop order. 
3. **Number of Tied Optima:** The independent recomputation explicitly tracked ties. It found **2 distinct weight combinations** that yield the exact same mathematically maximal rank correlation.
4. **Overfitting:** Tuning 2 independent degrees of freedom on a discrete rank ordering of 12 samples is mathematically unidentifiable. The "optimal" weights are spurious artifacts of the grid search iteration path, rather than a genuine physical relationship.

## Conclusion
The cross-architecture transfer claim is structurally invalid. The model is over-parameterized relative to the discrete rank space of the 12 training samples, resulting in unidentifiable parameters. The optimization process merely memorized an arbitrary linear combination that satisfied a tie-breaker.
