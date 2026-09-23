import requests
import json
import sys
from collections import defaultdict

JAEGER_URL = "http://localhost:16687"

def fetch_traces(service="frontend", limit=10):
    try:
        r = requests.get(f"{JAEGER_URL}/api/traces", params={"service": service, "limit": limit}, timeout=5)
        return r.json().get("data", [])
    except Exception as e:
        print(f"Error: {e}")
        return []

def print_trace_tree(trace):
    spans = trace.get("spans", [])
    processes = trace.get("processes", {})
    
    # Map span ID to span
    span_map = {s["spanID"]: s for s in spans}
    
    # Build tree
    children = defaultdict(list)
    roots = []
    
    for s in spans:
        parent_id = None
        for ref in s.get("references", []):
            if ref.get("refType") == "CHILD_OF":
                parent_id = ref.get("spanID")
                break
        
        if parent_id and parent_id in span_map:
            children[parent_id].append(s)
        else:
            roots.append(s)
            
    def get_service_name(span):
        pid = span.get("processID")
        if pid and pid in processes:
            return processes[pid].get("serviceName", "unknown")
        return "unknown"
        
    def get_tags(span):
        res = {}
        for tag in span.get("tags", []):
            res[tag["key"]] = tag["value"]
        return res
        
    def print_node(span, depth=0):
        svc = get_service_name(span)
        op = span.get("operationName", "")
        duration = span.get("duration", 0) / 1000.0  # ms
        tags = get_tags(span)
        
        status = tags.get("http.status_code", "")
        error = tags.get("error", False)
        
        indent = "  " * depth
        info = f"{indent}- {svc}::{op} [{duration:.2f}ms]"
        if status:
            info += f" HTTP {status}"
        if error:
            info += f" [ERROR: True]"
            
        print(info)
        
        for c in children.get(span["spanID"], []):
            print_node(c, depth + 1)
            
    print(f"\nTrace ID: {trace.get('traceID')}")
    for root in roots:
        print_node(root)


if __name__ == "__main__":
    traces = fetch_traces()
    print(f"Fetched {len(traces)} traces.")
    
    # Let's print the first 5 traces to see path variations
    for t in traces[:5]:
        print_trace_tree(t)
