import pandas as pd
from pathlib import Path
import numpy as np

freeze = Path('C:/Users/daksh/.gemini/antigravity-ide/scratch/microservice-failure-analysis/EVIDENCE_FREEZE')
df_old = pd.read_csv(freeze / 'derived' / 'fault_specific_correlations.csv')
df_new = pd.read_csv(freeze / 'audit' / 'INDEPENDENT_STATISTICAL_RESULTS.csv')

df_new = df_new.rename(columns={'fault': 'fault_type'})
merged = pd.merge(df_old, df_new, on=['architecture', 'fault_type', 'metric', 'outcome'], how='inner')

results = []
for idx, row in merged.iterrows():
    tau_old = row['kendall_tau_x']
    tau_new = row['kendall_tau_y']
    
    status = 'IDENTICAL'
    notes = ''
    
    if pd.isna(tau_old) and pd.isna(tau_new):
        status = 'IDENTICAL'
    elif pd.isna(tau_old) or pd.isna(tau_new):
        status = 'IMPLEMENTATION_DIFFERENCE'
        notes = 'NaN mismatch'
    elif abs(tau_old - tau_new) > 1e-5:
        status = 'IMPLEMENTATION_DIFFERENCE'
        notes = f'Value mismatch {tau_old} vs {tau_new}'
        
    results.append({
        'architecture': row['architecture'],
        'fault': row['fault_type'],
        'metric': row['metric'],
        'outcome': row['outcome'],
        'phase5_tau': tau_old,
        'independent_tau': tau_new,
        'status': status,
        'notes': notes
    })

recon_df = pd.DataFrame(results)
recon_df.to_csv(freeze / 'audit' / 'STATISTICAL_RECONCILIATION.csv', index=False)
print("Generated STATISTICAL_RECONCILIATION.csv")
