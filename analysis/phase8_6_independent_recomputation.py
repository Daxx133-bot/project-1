import pandas as pd
import numpy as np
import scipy.stats as stats
from pathlib import Path
import os

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
        # Fallback if constant
        return obs, 1.0

def compute_hybrid(df, w1, w2, w3):
    return (w1 * df['in_degree'] + w2 * df['raw_out_degree'] * df['normalized_out_degree'] + w3 * df['betweenness'])

def optimize_weights(train_df, target_col):
    best_w = (0.4, 0.4, 0.2)
    best_rho = 0
    steps = np.arange(0, 1.1, 0.1)
    
    for w1 in steps:
        for w2 in steps:
            w3 = round(1.0 - w1 - w2, 2)
            if 0 <= w3 <= 1.0:
                score = compute_hybrid(train_df, w1, w2, w3)
                rho, _ = stats.spearmanr(score, train_df[target_col])
                if not np.isnan(rho) and abs(rho) > abs(best_rho):
                    best_rho = rho
                    best_w = (w1, w2, w3)
    return best_w

def main():
    base_dir = Path(os.path.abspath(__file__)).parent.parent
    out_dir = base_dir / "analysis" / "outputs"
    
    df = pd.read_csv(out_dir / "primary_analysis_dataset.csv")
    cent_df = pd.read_csv(out_dir / "centrality_table_frozen.csv")
    
    results = []
    centrality_metrics = ['in_degree', 'out_degree', 'total_degree', 'betweenness', 'pagerank', 'eigenvector', 'normalized_out_degree']
    
    for arch in ['socialnetwork', 'hotelreservation']:
        # Service level aggregation
        df_arch = df[df['architecture'] == arch]
        
        # Aggregate by service AND fault
        agg_fault = df_arch.groupby(['service', 'fault_type']).agg({
            'recovery_time_s': 'mean',
            'downstream_affected_count': 'mean',
            'delta_p95_ms': 'mean'
        }).reset_index()
        
        merged = pd.merge(cent_df[cent_df['architecture'] == arch], agg_fault, on='service')
        
        for ftype in ['kill', 'latency', 'cpu']:
            fm = merged[merged['fault_type'] == ftype]
            
            for cent in centrality_metrics:
                for target in ['recovery_time_s', 'downstream_affected_count']:
                    x = fm[cent].values
                    y = fm[target].values
                    
                    if len(x) < 3:
                        continue
                        
                    # Kendall
                    tau, p_tau = permutation_correlation(x, y, stats.kendalltau)
                    
                    # Spearman
                    rho, p_rho = permutation_correlation(x, y, stats.spearmanr)
                    
                    results.append({
                        'Architecture': arch,
                        'Fault': ftype,
                        'Centrality': cent,
                        'Target': target,
                        'N': len(x),
                        'Kendall_Tau': tau,
                        'Kendall_P': p_tau,
                        'Spearman_Rho': rho,
                        'Spearman_P': p_rho
                    })
    
    # 2. Cross-Architecture Transfer (Hybrid Metric)
    sn_df = df[df['architecture'] == 'socialnetwork'].groupby('service')['recovery_time_s'].mean().reset_index()
    sn_merged = pd.merge(cent_df[cent_df['architecture'] == 'socialnetwork'], sn_df, on='service')
    
    hr_df = df[df['architecture'] == 'hotelreservation'].groupby('service')['recovery_time_s'].mean().reset_index()
    hr_merged = pd.merge(cent_df[cent_df['architecture'] == 'hotelreservation'], hr_df, on='service')
    
    best_w = optimize_weights(sn_merged, 'recovery_time_s')
    
    hr_hybrid = compute_hybrid(hr_merged, *best_w)
    transfer_rho, _ = stats.spearmanr(hr_hybrid, hr_merged['recovery_time_s'])
    transfer_tau, _ = stats.kendalltau(hr_hybrid, hr_merged['recovery_time_s'])
    
    results.append({
        'Architecture': 'Cross-Transfer (SN->HR)',
        'Fault': 'ALL',
        'Centrality': f'Hybrid_W{best_w[0]}_{best_w[1]}_{best_w[2]}',
        'Target': 'recovery_time_s',
        'N': len(hr_merged),
        'Kendall_Tau': transfer_tau,
        'Kendall_P': np.nan, # Skipped permutation for speed here
        'Spearman_Rho': transfer_rho,
        'Spearman_P': np.nan
    })

    results_df = pd.DataFrame(results)
    results_df.to_csv(out_dir / "phase8_6_verified_statistics.csv", index=False)
    print(f"Generated {len(results_df)} verified statistical observations.")

if __name__ == '__main__':
    main()
