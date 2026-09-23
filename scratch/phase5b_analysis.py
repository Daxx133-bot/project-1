import pandas as pd
import numpy as np
import scipy.stats as stats
import itertools
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def fdr_correction(p_values):
    p_values = np.array(p_values)
    n = len(p_values)
    if n == 0: return []
    sorted_indices = np.argsort(p_values)
    sorted_p = p_values[sorted_indices]
    fdr_p = np.zeros(n)
    min_p = 1.0
    for i in range(n-1, -1, -1):
        p = sorted_p[i]
        fdr = p * n / (i + 1)
        min_p = min(min_p, fdr)
        fdr_p[sorted_indices[i]] = min_p
    return np.minimum(fdr_p, 1.0)

def stat_kendall(x, y):
    # To use in permutation_test, x and y might be 1d arrays
    # But permutation_test with pairings shuffles y
    return stats.kendalltau(x, y)[0]

def stat_spearman(x, y):
    return stats.spearmanr(x, y)[0]

def permutation_correlation(x, y, corr_func, n_resamples=1000):
    x = np.array(x)
    y = np.array(y)
    if len(np.unique(x)) == 1 or len(np.unique(y)) == 1:
        return 0.0, 1.0
        
    if corr_func == stats.kendalltau:
        stat_func = stat_kendall
    else:
        stat_func = stat_spearman
        
    obs = stat_func(x, y)
    if np.isnan(obs):
        return 0.0, 1.0
        
    # permutation_test requires a statistic that takes (x,y) or just x?
    # Actually, scipy permutation_test with pairings:
    # statistic should take x, y as arguments.
    res = stats.permutation_test((x, y), stat_func, permutation_type='pairings', n_resamples=n_resamples, alternative='two-sided')
    return obs, res.pvalue

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

def run_analysis():
    base_dir = Path("C:/Users/daksh/.gemini/antigravity-ide/scratch/microservice-failure-analysis")
    out_dir = base_dir / "analysis" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Primary Analytical Dataset
    df = pd.read_csv(base_dir / "measurement" / "results_controlled" / "run_manifest.csv")
    df = df[df['status'] == 'VALID'].copy()
    
    df['delta_p95_ms'] = df['fault_p95_ms'] - df['baseline_p95_ms']
    df['delta_error_rate'] = df['fault_error_rate'] - df['baseline_error_rate']
    
    df['baseline_trace_observed'] = (df['baseline_p95_ms'] != 0)
    df['fault_trace_observed'] = (df['fault_p95_ms'] != 0)
    
    cols = ['run_id', 'architecture', 'service', 'fault_type', 'repetition', 
            'baseline_p95_ms', 'fault_p95_ms', 'baseline_error_rate', 'fault_error_rate', 
            'downstream_affected_count', 'recovery_time_s', 'delta_p95_ms', 'delta_error_rate',
            'baseline_trace_observed', 'fault_trace_observed']
    
    df[cols].to_csv(out_dir / "primary_analysis_dataset.csv", index=False)
    
    # 4. Descriptive Analysis
    desc_arch = df.groupby('architecture').agg({
        'recovery_time_s': ['count', 'mean', 'median', 'std', lambda x: np.percentile(x, 75)-np.percentile(x, 25), 'min', 'max'],
        'downstream_affected_count': ['mean', 'median', 'std'],
        'delta_p95_ms': ['mean', 'median', 'std'],
        'baseline_trace_observed': 'sum',
        'fault_trace_observed': 'sum'
    })
    desc_arch.to_csv(out_dir / "descriptive_by_architecture.csv")
    
    desc_fault = df.groupby(['architecture', 'fault_type']).agg({
        'recovery_time_s': ['count', 'mean', 'median', 'std'],
        'delta_p95_ms': ['mean', 'median', 'std'],
        'baseline_trace_observed': 'sum'
    })
    desc_fault.to_csv(out_dir / "descriptive_by_fault.csv")
    
    desc_svc = df.groupby(['architecture', 'service']).agg({
        'recovery_time_s': ['count', 'mean', 'median', 'std'],
        'baseline_trace_observed': 'sum'
    })
    desc_svc.to_csv(out_dir / "descriptive_by_service.csv")
    
    # 5. Service-Level Structural Table & Classical Centrality Analysis
    cent_df = pd.read_csv(out_dir / "centrality_table_frozen.csv")
    
    agg_df = df.groupby(['architecture', 'service']).agg({
        'recovery_time_s': 'mean',
        'downstream_affected_count': 'mean',
        'delta_p95_ms': 'mean',
        'delta_error_rate': 'mean'
    }).reset_index()
    
    df_sens = df.copy()
    df_sens.loc[~df_sens['fault_trace_observed'], 'delta_p95_ms'] = np.nan
    agg_df_sens = df_sens.groupby(['architecture', 'service']).agg({
        'delta_p95_ms': 'mean' 
    }).reset_index().rename(columns={'delta_p95_ms': 'delta_p95_ms_sens'})
    
    merged = pd.merge(cent_df, agg_df, on=['architecture', 'service'])
    merged = pd.merge(merged, agg_df_sens, on=['architecture', 'service'])
    
    metrics = ['in_degree', 'out_degree', 'total_degree', 'betweenness', 'pagerank', 'eigenvector']
    outcomes = ['recovery_time_s', 'downstream_affected_count', 'delta_p95_ms', 'delta_error_rate', 'delta_p95_ms_sens']
    
    corr_results = []
    for metric in metrics:
        for out in outcomes:
            valid_idx = ~merged[out].isna()
            if valid_idx.sum() < 3: continue
            x = merged.loc[valid_idx, metric]
            y = merged.loc[valid_idx, out]
            tau, p_tau = permutation_correlation(x, y, stats.kendalltau)
            rho, p_rho = permutation_correlation(x, y, stats.spearmanr)
            corr_results.append({
                'architecture': 'ALL_POOLED',
                'fault_type': 'ALL',
                'metric': metric,
                'outcome': out,
                'N': len(x),
                'kendall_tau': tau,
                'tau_pval': p_tau,
                'spearman_rho': rho,
                'rho_pval': p_rho
            })
            
    for arch in ['socialnetwork', 'hotelreservation']:
        arch_df = merged[merged['architecture'] == arch]
        for metric in metrics:
            for out in outcomes:
                valid_idx = ~arch_df[out].isna()
                if valid_idx.sum() < 3: continue
                x = arch_df.loc[valid_idx, metric]
                y = arch_df.loc[valid_idx, out]
                tau, p_tau = permutation_correlation(x, y, stats.kendalltau)
                rho, p_rho = permutation_correlation(x, y, stats.spearmanr)
                corr_results.append({
                    'architecture': arch,
                    'fault_type': 'ALL',
                    'metric': metric,
                    'outcome': out,
                    'N': len(x),
                    'kendall_tau': tau,
                    'tau_pval': p_tau,
                    'spearman_rho': rho,
                    'rho_pval': p_rho
                })
    pd.DataFrame(corr_results).to_csv(out_dir / "metric_correlations.csv", index=False)
    
    # 6. Fault Specific Analysis
    fault_results = []
    for arch in ['socialnetwork', 'hotelreservation']:
        for ftype in ['kill', 'latency', 'cpu']:
            f_df = df[(df['architecture'] == arch) & (df['fault_type'] == ftype)]
            f_agg = f_df.groupby('service').agg({
                'recovery_time_s': 'mean',
                'downstream_affected_count': 'mean'
            }).reset_index()
            f_merged = pd.merge(cent_df[cent_df['architecture'] == arch], f_agg, on='service')
            
            for metric in metrics:
                for out in ['recovery_time_s', 'downstream_affected_count']:
                    x = f_merged[metric]
                    y = f_merged[out]
                    if len(x) < 3: continue
                    tau, p_tau = permutation_correlation(x, y, stats.kendalltau)
                    rho, p_rho = permutation_correlation(x, y, stats.spearmanr)
                    fault_results.append({
                        'architecture': arch,
                        'fault_type': ftype,
                        'metric': metric,
                        'outcome': out,
                        'N': len(x),
                        'kendall_tau': tau,
                        'tau_pval': p_tau,
                        'spearman_rho': rho,
                        'rho_pval': p_rho
                    })
    pd.DataFrame(fault_results).to_csv(out_dir / "fault_specific_correlations.csv", index=False)
    
    # 8. Fan-Out Analysis
    fan_results = []
    w1, w2, w3 = 0.4, 0.4, 0.2
    merged['hybrid_linear'] = w1 * merged['in_degree'] + w2 * merged['raw_out_degree'] + w3 * merged['betweenness']
    merged['hybrid_fanout'] = w1 * merged['in_degree'] + w2 * (merged['raw_out_degree'] * merged['normalized_out_degree']) + w3 * merged['betweenness']
    
    fan_metrics = ['raw_out_degree', 'normalized_out_degree', 'hybrid_linear', 'hybrid_fanout']
    for arch in ['socialnetwork', 'hotelreservation', 'ALL_POOLED']:
        m_df = merged if arch == 'ALL_POOLED' else merged[merged['architecture'] == arch]
        for metric in fan_metrics:
            for out in ['downstream_affected_count']:
                x = m_df[metric]
                y = m_df[out]
                tau, p_tau = permutation_correlation(x, y, stats.kendalltau)
                rho, p_rho = permutation_correlation(x, y, stats.spearmanr)
                fan_results.append({
                    'architecture': arch,
                    'metric': metric,
                    'outcome': out,
                    'N': len(x),
                    'spearman_rho': rho,
                    'rho_pval': p_rho
                })
    pd.DataFrame(fan_results).to_csv(out_dir / "fanout_analysis.csv", index=False)
    
    # 9. Cross-Architecture Weight Validation
    cross_results = []
    for train_arch, test_arch in [('hotelreservation', 'socialnetwork'), ('socialnetwork', 'hotelreservation')]:
        train_df = merged[merged['architecture'] == train_arch]
        test_df = merged[merged['architecture'] == test_arch]
        
        best_w = optimize_weights(train_df, 'downstream_affected_count')
        
        test_score = compute_hybrid(test_df, best_w[0], best_w[1], best_w[2])
        tau, p_tau = permutation_correlation(test_score, test_df['downstream_affected_count'], stats.kendalltau)
        rho, p_rho = permutation_correlation(test_score, test_df['downstream_affected_count'], stats.spearmanr)
        
        cross_results.append({
            'train_arch': train_arch,
            'test_arch': test_arch,
            'w1': best_w[0],
            'w2': best_w[1],
            'w3': best_w[2],
            'train_N': len(train_df),
            'test_N': len(test_df),
            'kendall_tau': tau,
            'tau_pval': p_tau,
            'spearman_rho': rho,
            'rho_pval': p_rho
        })
    pd.DataFrame(cross_results).to_csv(out_dir / "cross_architecture_results.csv", index=False)
    
    # Multiple comparisons (FDR) on metric_correlations
    df_metric = pd.read_csv(out_dir / "metric_correlations.csv")
    df_metric['tau_pval_fdr'] = fdr_correction(df_metric['tau_pval'])
    df_metric['rho_pval_fdr'] = fdr_correction(df_metric['rho_pval'])
    df_metric.to_csv(out_dir / "metric_correlations.csv", index=False)
    
    print("Statistical Analysis complete.")

if __name__ == '__main__':
    run_analysis()
