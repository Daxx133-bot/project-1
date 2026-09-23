"""AUDIT-ONLY recomputation. Reads existing data, writes only into _audit/repro/."""
import pandas as pd, numpy as np, json
from scipy import stats
from pathlib import Path
R=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
cent={"socialnetwork":pd.read_csv(R/"centrality/output/centrality_table.csv"),
      "hotelreservation":pd.read_csv(R/"centrality/output/hotel/centrality_table.csv")}
METRICS=["degree","in_degree","out_degree","betweenness","closeness","eigenvector","pagerank","composite_score","hybrid_criticality"]
IMP=["latency_p95_delta_ms","latency_p99_delta_ms","error_rate_delta","downstream_affected_count","recovery_time_s"]
def run(label, csv, arch, filt=None):
    d=pd.read_csv(csv)
    if filt is not None: d=filt(d)
    agg=d.groupby("service")[ [c for c in IMP if c in d.columns] ].mean().reset_index()
    m=cent[arch].merge(agg,on="service")
    rows=[]
    for met in METRICS:
        for imp in IMP:
            if imp not in m.columns: continue
            rho,p=stats.spearmanr(m[met],m[imp])
            rows.append(dict(dataset=label,n=len(m),metric=met,impact=imp,rho=round(rho,4),p=round(p,4)))
    return pd.DataFrame(rows)
res=[]
res.append(run("SN_mixed_synthetic+real (measurement/results/experiment_log.csv)",R/"measurement/results/experiment_log.csv","socialnetwork"))
res.append(run("SN_synthetic_only_48",R/"measurement/results/experiment_log.csv","socialnetwork",
    lambda d: d[d.downstream_affected_services.astype(str).str.contains("downstream_")]))
res.append(run("SN_real_only_59",R/"measurement/results/experiment_log.csv","socialnetwork",
    lambda d: d[~d.downstream_affected_services.astype(str).str.contains("downstream_")]))
res.append(run("SN_controlled_122",R/"measurement/results_controlled/socialnetwork/experiment_log.csv","socialnetwork"))
res.append(run("HR_42",R/"measurement/results/hotel/experiment_log.csv","hotelreservation"))
res.append(run("HR_controlled_81",R/"measurement/results_controlled/hotelreservation/experiment_log.csv","hotelreservation"))
df=pd.concat(res)
df.to_csv(OUT/"recomputed_correlations.csv",index=False)
key=df[(df.impact=="recovery_time_s")&(df.metric.isin(["degree","hybrid_criticality","in_degree"]))]
print(key.to_string(index=False))
