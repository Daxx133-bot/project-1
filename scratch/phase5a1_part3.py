import pandas as pd
import networkx as nx
from pathlib import Path
import json

def safe_eigenvector(G):
    try:
        return nx.eigenvector_centrality(G, max_iter=1000, tol=1e-06)
    except:
        try:
            return nx.eigenvector_centrality_numpy(G)
        except:
            return {n: 0.0 for n in G.nodes()}

def main():
    base_dir = Path("C:/Users/daksh/.gemini/antigravity-ide/scratch/microservice-failure-analysis")
    
    # HR Graph (Observed)
    hr_trace = base_dir / "sdg" / "raw_traces" / "hotel" / "raw_traces.json"
    with open(hr_trace, 'r') as f:
        data_hr = json.load(f)
    G_hr = nx.DiGraph()
    for trace in data_hr.get('traces', []):
        process_map = {k: v.get('serviceName', 'unknown') for k, v in trace.get('processes', {}).items()}
        span_index = {s['spanID']: s for s in trace.get('spans', []) if 'spanID' in s}
        for span in trace.get('spans', []):
            child_svc = process_map.get(span.get('processID', ''), 'unknown')
            for ref in span.get('references', []):
                if ref.get('refType') == 'CHILD_OF':
                    parent_span = span_index.get(ref.get('spanID'))
                    if parent_span:
                        parent_svc = process_map.get(parent_span.get('processID', ''), 'unknown')
                        if parent_svc != child_svc and parent_svc != 'jaeger-query':
                            G_hr.add_edge(parent_svc, child_svc)
                            
    # SN Graph (Configured)
    EXPECTED_SERVICES = {
        "nginx-web-server", "compose-post-service", "text-service",
        "user-mention-service", "url-shorten-service", "media-service",
        "unique-id-service", "user-service", "social-graph-service",
        "post-storage-service", "user-timeline-service", "home-timeline-service"
    }
    G_sn = nx.DiGraph()
    for s in EXPECTED_SERVICES:
        G_sn.add_node(s)
    edges_configured = [
        ("nginx-web-server", "compose-post-service"),
        ("nginx-web-server", "home-timeline-service"),
        ("nginx-web-server", "user-timeline-service"),
        ("compose-post-service", "text-service"),
        ("compose-post-service", "media-service"),
        ("compose-post-service", "unique-id-service"),
        ("compose-post-service", "user-mention-service"),
        ("compose-post-service", "url-shorten-service"),
        ("compose-post-service", "user-service"),
        ("compose-post-service", "home-timeline-service"),
        ("compose-post-service", "post-storage-service"),
        ("user-mention-service", "user-service"),
        ("home-timeline-service", "post-storage-service"),
        ("home-timeline-service", "social-graph-service"),
        ("user-timeline-service", "post-storage-service"),
    ]
    G_sn.add_edges_from(edges_configured)
    
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
            
    process_graph(G_sn, "socialnetwork")
    process_graph(G_hr, "hotelreservation")
    
    pd.DataFrame(cent_rows).to_csv(base_dir / "analysis" / "outputs" / "centrality_table_frozen.csv", index=False)

if __name__ == '__main__':
    main()
