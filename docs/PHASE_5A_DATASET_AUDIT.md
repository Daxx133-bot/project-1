# Phase 5A Dataset Audit
    
- Total Rows: 174
- Valid Observations: 171
- Invalid Observations: 3
- Retry Observations: 3
- Architecture Counts: {'socialnetwork': 111, 'hotelreservation': 63}
- Service Counts: {'user-timeline-service': 12, 'home-timeline-service': 9, 'nginx-web-server': 9, 'text-service': 9, 'user-mention-service': 9, 'media-service': 9, 'url-shorten-service': 9, 'unique-id-service': 9, 'post-storage-service': 9, 'social-graph-service': 9, 'user-service': 9, 'compose-post-service': 9, 'frontend': 9, 'search': 9, 'reservation': 9, 'rate': 9, 'geo': 9, 'profile': 9, 'recommendation': 9}
- Fault Counts: {'kill': 60, 'latency': 57, 'cpu': 57}
- Repetition Counts: {1: 58, 2: 58, 3: 58}
- Missing Values: {'run_id': 0, 'architecture': 0, 'service': 0, 'fault_type': 0, 'repetition': 0, 'rps': 0, 'jaeger_port': 0, 'status': 0, 'start_time': 0, 'end_time': 0, 'baseline_p95_ms': 3, 'fault_p95_ms': 3, 'baseline_error_rate': 3, 'fault_error_rate': 3, 'downstream_affected_count': 3, 'recovery_time_s': 3, 'notes': 0}
- Duplicate Run IDs: 0
- Duplicate Valid Cells: 0
- Zero Values (P95): {'baseline_p95_ms': 11, 'fault_p95_ms': 27}
- Negative Values (P95): {'baseline_p95_ms': 0, 'fault_p95_ms': 0}
