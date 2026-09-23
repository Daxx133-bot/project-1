# Phase 8.6: Cross-Architecture Weight Identifiability

This document analyzes the structural identifiability of the hybrid metric weight optimization process.

## The Objective Function

The grid search attempts to find the optimal weights ($W_1$, $W_2$, $W_3$) for the hybrid metric equation:
$$S_{hybrid} = W_1(\text{In-Degree}) + W_2(\text{Fan-Out}) + W_3(\text{Betweenness})$$
subject to $W_1 + W_2 + W_3 = 1.0$.

The optimization objective is to maximize the absolute Spearman rank correlation $|\rho|$ between the hybrid score and empirical recovery time on a training architecture.

```python
    best_rho = 0
    # ...
    if not np.isnan(rho) and abs(rho) > abs(best_rho):
        best_rho = rho
        best_w = (w1, w2, w3)
```

## Identifiability Analysis

1. **Rank Degeneracy:** The Social Network training architecture contains only 12 services. The objective function is a *rank* correlation, not a continuous loss function. Because the metric values (degree, betweenness) take on a small discrete set of values across only 12 nodes, there are vast, contiguous regions of the parameter space $(W_1, W_2, W_3)$ that produce the **exact same rank ordering** of those 12 services.
2. **Tie-Breaking:** The optimization uses a strict inequality `abs(rho) > abs(best_rho)`. If multiple weight combinations produce the exact same maximal Spearman $\rho$, the algorithm simply keeps the **first** one it encountered in its arbitrary loop order.
3. **Overfitting:** Tuning 2 degrees of freedom on a discrete rank ordering of 12 samples is mathematically unidentifiable. The resulting "optimal" weights (previously reported as 0.0, 0.1, 0.9) are spurious artifacts of the grid search iteration path, rather than a genuine physical relationship.

## Conclusion

The cross-architecture transfer claim is structurally invalid. The model is massively over-parameterized relative to the discrete rank space of the 12 training samples, resulting in unidentifiable parameters. The optimization process merely memorized an arbitrary linear combination that satisfied a tie-breaker. This explains why the metric performed no better than chance (and in some cases perfectly inverted, $\rho=-1.0$) when transferred to the Hotel Reservation architecture.
