import pandas as pd
import scipy.stats as stats
from pathlib import Path
import numpy as np

freeze = Path('C:/Users/daksh/.gemini/antigravity-ide/scratch/microservice-failure-analysis/EVIDENCE_FREEZE')
df = pd.read_csv(freeze / 'derived' / 'primary_analysis_dataset.csv')
cent = pd.read_csv(freeze / 'derived' / 'centrality_table_frozen.csv')

# 1. Inspect the 12 SN CPU observations
sn_cpu = df[(df['architecture'] == 'socialnetwork') & (df['fault_type'] == 'cpu')]

# 2. To get 12 values, we must aggregate by service, as there are 3 reps per service
# Let's check how the script did it:
agg = sn_cpu.groupby('service')['recovery_time_s'].mean().reset_index()

# Merge with centrality
merged = pd.merge(cent[cent['architecture'] == 'socialnetwork'], agg, on='service')

x = merged['out_degree'].values
y = merged['recovery_time_s'].values

print("=== RECOVERY TIME VALUES ===")
for svc, val in zip(merged['service'], y):
    print(f"{svc}: {val}")

print(f"\nVariance of recovery_time_s: {np.var(y)}")
print(f"Variance of out_degree: {np.var(x)}")

print("\n=== KENDALL TAU ===")
tau, p = stats.kendalltau(x, y)
print(f"Scipy Kendall Tau: {tau}, p={p}")

# Permutation test replication
def permutation_correlation(x, y, stat_func, n_resamples=9999):
    try:
        obs = stat_func(x, y).statistic
    except AttributeError:
        obs = stat_func(x, y)[0]
    
    if np.isnan(obs) or len(x) < 3:
        return np.nan, np.nan
        
    try:
        res = stats.permutation_test((x, y), stat_func, permutation_type='pairings', n_resamples=n_resamples, alternative='two-sided')
        return obs, res.pvalue
    except Exception as e:
        return obs, 1.0

tau_perm, p_perm = permutation_correlation(x, y, stats.kendalltau)
print(f"Permutation Kendall Tau: {tau_perm}, p={p_perm}")
