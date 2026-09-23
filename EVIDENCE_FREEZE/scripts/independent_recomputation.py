import pandas as pd
import numpy as np
import scipy.stats as stats
from pathlib import Path
import os
import warnings
warnings.filterwarnings('ignore')

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

def compute_hybrid(df, w1, w2, w3):
    return (w1 * df['in_degree'] + w2 * df['raw_out_degree'] * df['normalized_out_degree'] + w3 * df['betweenness'])

def optimize_weights(train_df, target_col):
    best_w = (0.0, 0.0, 0.0)
    best_rho = -2.0
    steps = np.arange(0, 1.1, 0.1)
    
    tied_optima = []
    
    for w1 in steps:
        for w2 in steps:
            w3 = round(1.0 - w1 - w2, 2)
            if 0 <= w3 <= 1.0:
                score = compute_hybrid(train_df, w1, w2, w3)
                rho, _ = stats.spearmanr(score, train_df[target_col])
                if not np.isnan(rho):
                    if abs(rho) > best_rho + 1e-9:
                        best_rho = abs(rho)
                        best_w = (round(w1,2), round(w2,2), round(w3,2))
                        tied_optima = [best_w]
                    elif abs(abs(rho) - best_rho) < 1e-9:
                        tied_optima.append((round(w1,2), round(w2,2), round(w3,2)))
    return best_w, tied_optima

def main():
    freeze = Path(os.path.abspath(__file__)).parent.parent
    df = pd.read_csv(freeze / "derived" / "primary_analysis_dataset.csv")
    cent = pd.read_csv(freeze / "derived" / "centrality_table_frozen.csv")
    
    results = []
    centrality_metrics = ['in_degree', 'out_degree', 'total_degree', 'betweenness', 'pagerank', 'eigenvector', 'normalized_out_degree']
    targets = ['recovery_time_s', 'downstream_affected_count']
    
    # 1. Standard Aggregated Correlations
    for arch in ['socialnetwork', 'hotelreservation']:
        # By architecture and fault
        agg = df[df['architecture'] == arch].groupby(['service', 'fault_type']).agg({
            'recovery_time_s': 'mean',
            'downstream_affected_count': 'mean'
        }).reset_index()
        merged = pd.merge(cent[cent['architecture'] == arch], agg, on='service')
        
        for ftype in ['kill', 'latency', 'cpu']:
            fm = merged[merged['fault_type'] == ftype]
            for cent_m in centrality_metrics:
                for t in targets:
                    x = fm[cent_m].values
                    y = fm[t].values
                    if len(x) < 3: continue
                    tau, p_tau = permutation_correlation(x, y, stats.kendalltau)
                    rho, p_rho = permutation_correlation(x, y, stats.spearmanr)
                    results.append({
                        'architecture': arch, 'fault': ftype, 'metric': cent_m, 'outcome': t,
                        'N': len(x), 'kendall_tau': tau, 'kendall_p': p_tau, 'spearman_rho': rho, 'spearman_p': p_rho,
                        'source_dataset': 'primary_analysis_dataset.csv', 'calculation_method': 'independent_permutation'
                    })
    
    # 2. Cross-Architecture
    sn_df = df[df['architecture'] == 'socialnetwork'].groupby('service')['recovery_time_s'].mean().reset_index()
    sn_merged = pd.merge(cent[cent['architecture'] == 'socialnetwork'], sn_df, on='service')
    hr_df = df[df['architecture'] == 'hotelreservation'].groupby('service')['recovery_time_s'].mean().reset_index()
    hr_merged = pd.merge(cent[cent['architecture'] == 'hotelreservation'], hr_df, on='service')
    
    best_w, tied = optimize_weights(sn_merged, 'recovery_time_s')
    
    hr_hybrid = compute_hybrid(hr_merged, *best_w)
    transfer_rho, _ = permutation_correlation(hr_hybrid, hr_merged['recovery_time_s'].values, stats.spearmanr)
    transfer_tau, _ = permutation_correlation(hr_hybrid, hr_merged['recovery_time_s'].values, stats.kendalltau)
    
    results.append({
        'architecture': 'cross_transfer_sn_hr', 'fault': 'pooled', 'metric': f'hybrid_{best_w}', 'outcome': 'recovery_time_s',
        'N': len(hr_merged), 'kendall_tau': transfer_tau, 'kendall_p': np.nan, 'spearman_rho': transfer_rho, 'spearman_p': np.nan,
        'source_dataset': 'primary_analysis_dataset.csv', 'calculation_method': 'independent_grid_search'
    })
    
    # Save Results
    pd.DataFrame(results).to_csv(freeze / 'audit' / 'INDEPENDENT_STATISTICAL_RESULTS.csv', index=False)
    
    # Disputed Values Explicit Output
    print(f"--- DISPUTED VALUES EXPLICIT RECOMPUTATION ---")
    df_res = pd.DataFrame(results)
    queries = [
        ('socialnetwork', 'kill', 'out_degree', 'recovery_time_s'),
        ('socialnetwork', 'cpu', 'out_degree', 'recovery_time_s'),
        ('hotelreservation', 'cpu', 'out_degree', 'recovery_time_s'),
        ('hotelreservation', 'latency', 'out_degree', 'recovery_time_s')
    ]
    for q in queries:
        row = df_res[(df_res['architecture'] == q[0]) & (df_res['fault'] == q[1]) & (df_res['metric'] == q[2]) & (df_res['outcome'] == q[3])]
        if not row.empty:
            r = row.iloc[0]
            print(f"{q[0]} / {q[1]} / {q[2]} / {q[3]} -> N={r['N']}, tau={r['kendall_tau']}, p={r['kendall_p']}")
        else:
            print(f"NOT FOUND: {q}")

    print(f"--- CROSS-ARCHITECTURE WEIGHT OPTIMIZATION ---")
    print(f"Best Weights chosen: {best_w}")
    print(f"Number of tied weight combinations: {len(tied)}")
    
if __name__ == '__main__':
    main()
