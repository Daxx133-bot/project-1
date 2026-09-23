import json
import pandas as pd
import networkx as nx
from pathlib import Path
import numpy as np
import traceback

def safe_eigenvector(G):
    try:
        return nx.eigenvector_centrality(G, max_iter=1000, tol=1e-06)
    except:
        try:
            return nx.eigenvector_centrality_numpy(G)
        except:
            return {n: 0.0 for n in G.nodes()}

def build_graph(trace_path):
    with open(trace_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    traces = data.get('traces', [])
    G = nx.DiGraph()
    edge_counts = {}
    for trace in traces:
        processes = trace.get('processes', {})
        process_map = {k: v.get('serviceName', 'unknown') for k, v in processes.items()}
        spans = trace.get('spans', [])
        span_index = {s['spanID']: s for s in spans if 'spanID' in s}
        for span in spans:
            child_svc = process_map.get(span.get('processID', ''), 'unknown')
            for ref in span.get('references', []):
                if ref.get('refType') == 'CHILD_OF':
                    parent_span = span_index.get(ref.get('spanID'))
                    if parent_span:
                        parent_svc = process_map.get(parent_span.get('processID', ''), 'unknown')
                        if parent_svc != child_svc:
                            edge = (parent_svc, child_svc)
                            edge_counts[edge] = edge_counts.get(edge, 0) + 1
    for (u, v), c in edge_counts.items():
        G.add_edge(u, v, weight=c)
    return G

def run_pipeline():
    base_dir = Path("C:/Users/daksh/.gemini/antigravity-ide/scratch/microservice-failure-analysis")
    output_dir = base_dir / "analysis" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Dataset Audit
    manifest_path = base_dir / "measurement" / "results_controlled" / "run_manifest.csv"
    df = pd.read_csv(manifest_path)
    
    total_rows = len(df)
    valid_obs = len(df[df['status'] == 'VALID'])
    invalid_obs = len(df[df['status'] == 'INVALID'])
    retry_obs = len(df[df['run_id'].str.contains('_retry')])
    
    arch_counts = df['architecture'].value_counts().to_dict()
    svc_counts = df['service'].value_counts().to_dict()
    fault_counts = df['fault_type'].value_counts().to_dict()
    rep_counts = df['repetition'].value_counts().to_dict()
    
    missing_vals = df.isnull().sum().to_dict()
    dup_run_ids = df['run_id'].duplicated().sum()
    
    df_valid = df[df['status'] == 'VALID']
    dup_cells = df_valid.duplicated(subset=['architecture', 'service', 'fault_type', 'repetition']).sum()
    
    zero_vals = (df_valid[['baseline_p95_ms', 'fault_p95_ms']] == 0).sum().to_dict()
    neg_vals = (df_valid[['baseline_p95_ms', 'fault_p95_ms']] < 0).sum().to_dict()
    
    audit_md = f"""# Phase 5A Dataset Audit
    
- Total Rows: {total_rows}
- Valid Observations: {valid_obs}
- Invalid Observations: {invalid_obs}
- Retry Observations: {retry_obs}
- Architecture Counts: {arch_counts}
- Service Counts: {svc_counts}
- Fault Counts: {fault_counts}
- Repetition Counts: {rep_counts}
- Missing Values: {missing_vals}
- Duplicate Run IDs: {dup_run_ids}
- Duplicate Valid Cells: {dup_cells}
- Zero Values (P95): {zero_vals}
- Negative Values (P95): {neg_vals}
"""
    with open(base_dir / "docs" / "PHASE_5A_DATASET_AUDIT.md", "w") as f:
        f.write(audit_md)
        
    # 2-5. Graph Reconstruction and Centrality
    sn_trace = base_dir / "sdg" / "raw_traces" / "raw_traces.json"
    hr_trace = base_dir / "sdg" / "raw_traces" / "hotel" / "raw_traces.json"
    
    sn_graph = build_graph(sn_trace)
    hr_graph = build_graph(hr_trace)
    
    cent_rows = []
    
    def process_graph(G, arch):
        in_deg = dict(G.in_degree())
        out_deg = dict(G.out_degree())
        tot_deg = dict(G.degree())
        bet = nx.betweenness_centrality(G)
        pr = nx.pagerank(G, alpha=0.85)
        eig = safe_eigenvector(G)
        
        max_out = max(out_deg.values()) if out_deg else 1
        if max_out == 0: max_out = 1
        
        for n in G.nodes():
            cent_rows.append({
                "service": n,
                "architecture": arch,
                "in_degree": in_deg.get(n, 0),
                "out_degree": out_deg.get(n, 0),
                "total_degree": tot_deg.get(n, 0),
                "betweenness": bet.get(n, 0.0),
                "pagerank": pr.get(n, 0.0),
                "eigenvector": eig.get(n, 0.0),
                "raw_out_degree": out_deg.get(n, 0),
                "normalized_out_degree": out_deg.get(n, 0) / max_out
            })
            
        nodes = G.number_of_nodes()
        edges = G.number_of_edges()
        scc = nx.number_strongly_connected_components(G)
        cycles = len(list(nx.simple_cycles(G)))
        in_zero = sum(1 for n, d in G.in_degree() if d == 0)
        out_zero = sum(1 for n, d in G.out_degree() if d == 0)
        
        return f"""## Architecture: {arch}
- Nodes: {nodes}
- Edges: {edges}
- Strongly Connected Components: {scc}
- Cycles: {cycles}
- Nodes with in-degree 0: {in_zero}
- Nodes with out-degree 0: {out_zero}
"""

    report_md = "# Graph Reconstruction Report\n\n"
    report_md += process_graph(sn_graph, "socialnetwork")
    report_md += process_graph(hr_graph, "hotelreservation")
    
    with open(base_dir / "docs" / "PHASE_5A_GRAPH_RECONSTRUCTION_REPORT.md", "w") as f:
        f.write(report_md)
        
    pd.DataFrame(cent_rows).to_csv(output_dir / "centrality_table_frozen.csv", index=False)
    
    # 6. Map Experimental Impact
    df_valid['delta_p95'] = df_valid['fault_p95_ms'] - df_valid['baseline_p95_ms']
    df_valid['delta_error_rate'] = df_valid['fault_error_rate'] - df_valid['baseline_error_rate']
    
    keep_cols = ['architecture', 'service', 'fault_type', 'repetition', 'baseline_p95_ms', 'fault_p95_ms', 'delta_p95', 'baseline_error_rate', 'fault_error_rate', 'delta_error_rate', 'downstream_affected_count', 'recovery_time_s']
    df_valid[keep_cols].to_csv(output_dir / "service_impact_repetitions.csv", index=False)
    
    summary = df_valid.groupby(['architecture', 'service', 'fault_type']).agg(
        baseline_p95_mean=('baseline_p95_ms', 'mean'),
        baseline_p95_median=('baseline_p95_ms', 'median'),
        baseline_p95_std=('baseline_p95_ms', 'std'),
        fault_p95_mean=('fault_p95_ms', 'mean'),
        fault_p95_median=('fault_p95_ms', 'median'),
        fault_p95_std=('fault_p95_ms', 'std'),
        delta_p95_mean=('delta_p95', 'mean'),
        delta_p95_median=('delta_p95', 'median'),
        delta_p95_std=('delta_p95', 'std'),
        recovery_time_mean=('recovery_time_s', 'mean'),
        downstream_affected_mean=('downstream_affected_count', 'mean')
    ).reset_index()
    summary.to_csv(output_dir / "service_impact_summary.csv", index=False)
    
    print("DONE")

if __name__ == '__main__':
    run_pipeline()
