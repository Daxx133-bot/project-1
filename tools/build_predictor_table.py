"""
build_predictor_table.py — structural predictors per service, for the preregistration.

Pure graph computation from data/graphs/*_CANONICAL.json. Touches no outcome data, so it
can be run at any time without leakage. Writes data/analysis/predictor_table.csv.
"""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
import networkx as nx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from measurement.blast_radius import is_gateway  # noqa: E402

GRAPHS = {"socialnetwork": ROOT/"data"/"graphs"/"sn_CANONICAL.json",
          "hotelreservation": ROOT/"data"/"graphs"/"hr_CANONICAL.json"}

rows = []
for app, p in GRAPHS.items():
    G = nx.node_link_graph(json.loads(p.read_text(encoding="utf-8")), edges="edges")
    for s in sorted(G.nodes()):
        rows.append({
            "architecture": app, "service": s,
            "in_degree_raw": G.in_degree(s), "out_degree_raw": G.out_degree(s),
            "n_ancestors": len(nx.ancestors(G, s)),
            "n_descendants": len(nx.descendants(G, s)),
            "is_gateway": is_gateway(G, s),
            "in_analysis_set": not is_gateway(G, s),
        })

out = ROOT/"data"/"analysis"/"predictor_table.csv"
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"[WROTE] {out.relative_to(ROOT)}  ({len(rows)} services)")
for app in GRAPHS:
    keep = [r for r in rows if r["architecture"] == app and r["in_analysis_set"]]
    anc = sorted(r["n_ancestors"] for r in keep)
    print(f"  {app}: analysis n={len(keep)}, |ancestors| levels={sorted(set(anc))}, values={anc}")
