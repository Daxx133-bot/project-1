import pandas as pd
import numpy as np

df_old = pd.read_csv('analysis/outputs/fault_specific_correlations.csv')
df_new = pd.read_csv('analysis/outputs/phase8_6_verified_statistics.csv')

df_new = df_new.rename(columns={'Architecture': 'architecture', 'Fault': 'fault_type', 'Centrality': 'metric', 'Target': 'outcome'})
merged = pd.merge(df_old, df_new, on=['architecture', 'fault_type', 'metric', 'outcome'])

diffs = []
for idx, row in merged.iterrows():
    tau_old = row['kendall_tau']
    tau_new = row['Kendall_Tau']
    if not pd.isna(tau_old) and not pd.isna(tau_new):
        if abs(tau_old - tau_new) > 0.001:
            diffs.append(f"{row['architecture']} {row['fault_type']} {row['metric']} {row['outcome']}: {tau_old} vs {tau_new}")

if len(diffs) == 0:
    print('All Kendall Tau values match exactly between Phase 5 and Independent Recomputation!')
else:
    print('Discrepancies found:')
    for d in diffs[:10]: print(d)
