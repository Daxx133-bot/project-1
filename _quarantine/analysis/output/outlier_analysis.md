## Outlier Analysis

Services where centrality rank and blast radius rank diverge significantly.

| Service | Centrality Rank | Blast Rank | Rank Diff | Downstream Affected | Type |
|---|---|---|---|---|---|
| compose-post-service | 7 | 2 | 5 | 3.4 | False Negative (low centrality, high impact) |
| url-shorten-service | 8 | 11 | 3 | 1.0 | Aligned |
| nginx-web-server | 12 | 10 | 2 | 1.1 | Aligned |
| home-timeline-service | 4 | 6 | 2 | 1.8 | Aligned |
| user-service | 2 | 4 | 2 | 2.9 | Aligned |
| post-storage-service | 3 | 5 | 2 | 2.4 | Aligned |
| user-timeline-service | 5 | 3 | 2 | 3.2 | Aligned |
| media-service | 10 | 11 | 1 | 1.0 | Aligned |
| unique-id-service | 10 | 9 | 1 | 1.4 | Aligned |
| social-graph-service | 1 | 1 | 0 | 3.8 | Aligned |
| text-service | 6 | 6 | 0 | 1.8 | Aligned |
| user-mention-service | 8 | 8 | 0 | 1.5 | Aligned |
