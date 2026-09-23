import pandas as pd
import numpy as np
import scipy.stats as stats
import itertools
import os

print("==================================================")
print("1. RUN INVENTORY & CLASSIFICATION")
print("==================================================")

sn_path = 'measurement/results/experiment_log.csv'
hr_path = 'measurement/results/hotel/experiment_log.csv'
cen_sn_path = 'centrality/output/centrality_table.csv'
cen_hr_path = 'centrality/output/hotel/centrality_table.csv'

df_sn = pd.read_csv(sn_path) if os.path.exists(sn_path) else pd.DataFrame()
df_hr = pd.read_csv(hr_path) if os.path.exists(hr_path) else pd.DataFrame()

df_sn['architecture'] = 'Social Network'
df_hr['architecture'] = 'Hotel Reservation'

df_all = pd.concat([df_sn, df_hr], ignore_index=True)

print(f"Total runs found: {len(df_all)}")
print("\nRuns by Architecture and Fault Type:")
print(df_all.groupby(['architecture', 'fault_type']).size().unstack(fill_value=0))

print("\nRuns by Service in SN:")
print(df_sn.groupby(['service', 'fault_type']).size().unstack(fill_value=0))

# Validating runs
# The paper claimed kill, latency, cpu. latency_100ms is undocumented.
# We will classify kill, latency, cpu as VALID, latency_100ms as INVALID (undocumented).
valid_faults = ['kill', 'latency', 'cpu']

df_sn_valid = df_sn[df_sn['fault_type'].isin(valid_faults)].copy()
df_hr_valid = df_hr[df_hr['fault_type'].isin(valid_faults)].copy()

print(f"\nValid SN runs: {len(df_sn_valid)}")
print(f"Valid HR runs: {len(df_hr_valid)}")

print("\n==================================================")
print("2. DATA AGGREGATION & ABLATION SETUP")
print("==================================================")

cen_sn = pd.read_csv(cen_sn_path)
cen_hr = pd.read_csv(cen_hr_path)

def aggregate_data(df, centrality_df, fault_types=None):
    if fault_types:
        df = df[df['fault_type'].isin(fault_types)]
    agg = df.groupby('service').agg({
        'recovery_time_s':'mean',
        'error_rate_delta':'mean',
        'downstream_affected_count':'mean'
    }).reset_index()
    merged = pd.merge(centrality_df, agg, on='service')
    return merged

sn_agg = aggregate_data(df_sn_valid, cen_sn)
hr_agg = aggregate_data(df_hr_valid, cen_hr)

print(f"Aggregated SN N={len(sn_agg)}")
print(f"Aggregated HR N={len(hr_agg)}")

def evaluate_metric(score, target, n_permutations=9999):
    rho, p_asymp = stats.spearmanr(score, target)
    tau, p_tau = stats.kendalltau(score, target)
    
    # Exact permutation test for spearman rho
    def statistic(x, y):
        return stats.spearmanr(x, y)[0]
    
    res = stats.permutation_test((score, target), statistic, vectorized=False, 
                                 n_resamples=n_permutations, alternative='two-sided')
    p_exact = res.pvalue
    
    return rho, p_exact, tau, p_tau

def optimize_weights(train_df, target_col, is_linear=False):
    steps = [round(x * 0.1, 1) for x in range(11)]
    triplets = [(w1, w2, round(1.0 - w1 - w2, 1)) for w1 in steps for w2 in steps if 0.0 <= round(1.0 - w1 - w2, 1) <= 1.0]
    
    best_rho = -1.0
    best_w = None
    
    for w1, w2, w3 in triplets:
        if is_linear:
            score = w1 * train_df['in_degree'] + w2 * train_df['out_degree'] + w3 * train_df['betweenness']
        else:
            score = w1 * train_df['in_degree'] + w2 * train_df['out_degree'] * train_df['fan_out_weight'] + w3 * train_df['betweenness']
        
        rho, _ = stats.spearmanr(score, train_df[target_col])
        # optimize for absolute correlation
        if abs(rho) > best_rho:
            best_rho = abs(rho)
            best_w = (w1, w2, w3)
            
    return best_w, best_rho

print("\n==================================================")
print("3. CROSS-ARCHITECTURE VALIDATION (Recovery Time)")
print("==================================================")

target = 'recovery_time_s'

for train_name, train_df, test_name, test_df in [('SN', sn_agg, 'HR', hr_agg), ('HR', hr_agg, 'SN', sn_agg)]:
    print(f"\n--- Train: {train_name} | Test: {test_name} ---")
    
    # Linear Ablation
    w_lin, _ = optimize_weights(train_df, target, is_linear=True)
    score_lin = w_lin[0]*test_df['in_degree'] + w_lin[1]*test_df['out_degree'] + w_lin[2]*test_df['betweenness']
    r_lin, p_lin, tau_lin, ptau_lin = evaluate_metric(score_lin, test_df[target])
    
    # Fan-Out Corrected
    w_fan, _ = optimize_weights(train_df, target, is_linear=False)
    score_fan = w_fan[0]*test_df['in_degree'] + w_fan[1]*test_df['out_degree']*test_df['fan_out_weight'] + w_fan[2]*test_df['betweenness']
    r_fan, p_fan, tau_fan, ptau_fan = evaluate_metric(score_fan, test_df[target])
    
    # Classical Composite (Baseline)
    r_comp, p_comp, tau_comp, ptau_comp = evaluate_metric(test_df['composite_score'], test_df[target])
    # invert because lower rank = better
    r_comp = -r_comp
    tau_comp = -tau_comp
    
    print(f"Classical Composite     : rho={r_comp:.4f} (p={p_comp:.4f}), tau={tau_comp:.4f}")
    print(f"Linear Hybrid {w_lin}  : rho={r_lin:.4f} (p={p_lin:.4f}), tau={tau_lin:.4f}")
    print(f"Fan-Out Hybrid {w_fan} : rho={r_fan:.4f} (p={p_fan:.4f}), tau={tau_fan:.4f}")


print("\n==================================================")
print("4. FAULT-SPECIFIC ANALYSIS (SN Holdout, Train on HR)")
print("==================================================")
w_fan_hr, _ = optimize_weights(hr_agg, target, is_linear=False)
print(f"Weights from HR: {w_fan_hr}")

for f_type in valid_faults:
    sn_f = aggregate_data(df_sn_valid, cen_sn, [f_type])
    score = w_fan_hr[0]*sn_f['in_degree'] + w_fan_hr[1]*sn_f['out_degree']*sn_f['fan_out_weight'] + w_fan_hr[2]*sn_f['betweenness']
    r, p, t, pt = evaluate_metric(score, sn_f[target])
    print(f"Fault: {f_type:<8} | N={len(sn_f)} | rho={r:.4f} (p={p:.4f}) | tau={t:.4f}")

print("\n==================================================")
print("5. ORIGINAL (LEAKED) VS CORRECTED (HOLDOUT) RESULTS")
print("==================================================")
# The leaked original was w=(0.4, 0.4, 0.2) on SN, tested on SN.
score_leaked = 0.4*sn_agg['in_degree'] + 0.4*sn_agg['out_degree']*sn_agg['fan_out_weight'] + 0.2*sn_agg['betweenness']
r_leak, p_leak, _, _ = evaluate_metric(score_leaked, sn_agg[target])

print(f"Original (LEAKED) SN    : rho={r_leak:.4f}, p={p_leak:.4f} (N={len(sn_agg)})")
# Corrected is Train on HR, Test on SN (w_fan_hr)
score_corr = w_fan_hr[0]*sn_agg['in_degree'] + w_fan_hr[1]*sn_agg['out_degree']*sn_agg['fan_out_weight'] + w_fan_hr[2]*sn_agg['betweenness']
r_corr, p_corr, _, _ = evaluate_metric(score_corr, sn_agg[target])
print(f"Corrected (HOLDOUT) SN  : rho={r_corr:.4f}, p={p_corr:.4f} (N={len(sn_agg)})")
