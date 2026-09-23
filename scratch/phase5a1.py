import pandas as pd
import json
import networkx as nx
from pathlib import Path

def main():
    base_dir = Path("C:/Users/daksh/.gemini/antigravity-ide/scratch/microservice-failure-analysis")
    manifest_path = base_dir / "measurement" / "results_controlled" / "run_manifest.csv"
    df = pd.read_csv(manifest_path)
    
    # ISSUE 2: Zero values
    zero_rows = []
    
    for _, row in df.iterrows():
        if row['status'] != 'VALID':
            continue
        zero_baseline = (row['baseline_p95_ms'] == 0)
        zero_fault = (row['fault_p95_ms'] == 0)
        
        if zero_baseline or zero_fault:
            if zero_baseline and zero_fault:
                zero_field = 'both'
            elif zero_baseline:
                zero_field = 'baseline_p95_ms'
            else:
                zero_field = 'fault_p95_ms'
                
            arch = row['architecture']
            run_id = row['run_id']
            # Let's read the corresponding json to see trace count
            json_name = f"run_{row['start_time'].replace(':', '-').replace('.', 'p')[:24]}_{row['service']}_{row['fault_type']}.json"
            # Since we don't know the exact json filename format easily due to timestamp variations, let's just inspect the directory or leave it blank
            zero_reason = "TODO: investigate"
            zero_rows.append({
                'run_id': run_id,
                'architecture': arch,
                'service': row['service'],
                'fault_type': row['fault_type'],
                'repetition': row['repetition'],
                'status': row['status'],
                'baseline_p95_ms': row['baseline_p95_ms'],
                'fault_p95_ms': row['fault_p95_ms'],
                'baseline_error_rate': row['baseline_error_rate'],
                'fault_error_rate': row['fault_error_rate'],
                'downstream_affected_count': row['downstream_affected_count'],
                'recovery_time_s': row['recovery_time_s'],
                'zero_field': zero_field,
                'zero_reason': 'Unknown - investigate json/log',
                'trace_count': '?',
                'notes': row['notes']
            })
            
    pd.DataFrame(zero_rows).to_csv(base_dir / "analysis" / "outputs" / "zero_p95_audit.csv", index=False)
    
    # ISSUE 1: Graph Reconstruction
    sn_trace = base_dir / "sdg" / "raw_traces" / "raw_traces.json"
    with open(sn_trace, 'r') as f:
        data = json.load(f)
    
    traces = data.get('traces', [])
    unique_services = set()
    for t in traces:
        for p in t.get('processes', {}).values():
            unique_services.add(p.get('serviceName'))
            
    print(f"Social Network Traces: {len(traces)}")
    print(f"Unique Services in SN traces: {unique_services}")
    
if __name__ == '__main__':
    main()
