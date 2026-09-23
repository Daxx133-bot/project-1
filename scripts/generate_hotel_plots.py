"""
Generate all missing Hotel Reservation plots for paper publication.
Uses the actual empirical data from measurement/results/hotel/experiment_log.csv
and centrality/output/hotel/centrality_table.csv
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os
from scipy import stats

# --- Paths ---
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP_LOG = os.path.join(BASE, "measurement", "results", "hotel", "experiment_log.csv")
CENT_TABLE = os.path.join(BASE, "centrality", "output", "hotel", "centrality_table.csv")
OUT_DIR = os.path.join(BASE, "analysis", "plots", "hotel")
os.makedirs(OUT_DIR, exist_ok=True)

# --- Style ---
plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'figure.dpi': 150,
})

COLORS = {
    'kill':    '#E63946',
    'latency': '#F4A261',
    'cpu':     '#2A9D8F',
    'hybrid':  '#3A86FF',
    'classical': '#8D99AE',
}

# --- Load Data ---
df = pd.read_csv(EXP_LOG)
centrality = pd.read_csv(CENT_TABLE)

print("Hotel experiment log loaded:", df.shape)
print("Services:", df['service'].unique())
print("Fault types:", df['fault_type'].unique())
print("\nRecovery time stats by service:")
print(df.groupby('service')['recovery_time_s'].mean().sort_values(ascending=False))

# --- Merge centrality with experiment log ---
agg = df.groupby('service').agg(
    recovery_time_s=('recovery_time_s', 'mean'),
    error_rate_delta=('error_rate_delta', 'mean'),
    latency_p95_delta_ms=('latency_p95_delta_ms', 'mean'),
    downstream_affected_count=('downstream_affected_count', 'mean')
).reset_index()

merged = agg.merge(centrality, on='service')
print("\nMerged table:")
print(merged[['service','recovery_time_s','hybrid_rank','composite_rank','hybrid_criticality','degree']].to_string())

# ===========================================================================
# PLOT 1: Recovery Time by Service and Fault Type (Bar Chart)
# ===========================================================================
fig, ax = plt.subplots(figsize=(10, 5))
fault_types = ['kill', 'latency', 'cpu']
services = sorted(df['service'].unique())
x = np.arange(len(services))
width = 0.28

for i, ft in enumerate(fault_types):
    means = []
    for svc in services:
        val = df[(df['service'] == svc) & (df['fault_type'] == ft)]['recovery_time_s'].mean()
        means.append(val if not np.isnan(val) else 0)
    bars = ax.bar(x + i * width, means, width, label=ft.capitalize(),
                  color=COLORS[ft], alpha=0.88, edgecolor='white', linewidth=0.5)

ax.set_xlabel('Service')
ax.set_ylabel('Mean Recovery Time (s)')
ax.set_title('Hotel Reservation — Mean Recovery Time by Service and Fault Type')
ax.set_xticks(x + width)
ax.set_xticklabels(services, rotation=35, ha='right')
ax.legend(title='Fault Type', framealpha=0.5)
ax.grid(axis='y', linestyle='--', alpha=0.4)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'hotel_recovery_time_by_fault.png'), bbox_inches='tight')
plt.close()
print("Plot 1 saved: hotel_recovery_time_by_fault.png")

# ===========================================================================
# PLOT 2: Classical Rank vs Hybrid Rank Comparison (Lollipop)
# ===========================================================================
fig, ax = plt.subplots(figsize=(9, 5))
merged_sorted = merged.sort_values('hybrid_rank')
y = np.arange(len(merged_sorted))

for i, row in merged_sorted.iterrows():
    idx = list(merged_sorted.index).index(i)
    ax.plot([row['composite_rank'], row['hybrid_rank']], [idx, idx],
            color='#CED4DA', linewidth=2, zorder=1)

ax.scatter(merged_sorted['composite_rank'], y, color=COLORS['classical'], s=90,
           label='Classical Composite Rank', zorder=3)
ax.scatter(merged_sorted['hybrid_rank'], y, color=COLORS['hybrid'], s=90,
           label='Hybrid Criticality Rank', zorder=3)

# Annotate the false negative correction
for i, row in merged_sorted.iterrows():
    idx = list(merged_sorted.index).index(i)
    if row['composite_rank'] - row['hybrid_rank'] >= 4:
        ax.annotate(f"  {row['service']}\n  FN corrected",
                    xy=(row['hybrid_rank'], idx),
                    xytext=(row['hybrid_rank'] + 0.3, idx + 0.3),
                    fontsize=8.5, color='#E63946',
                    arrowprops=dict(arrowstyle='->', color='#E63946', lw=1))

ax.set_yticks(y)
ax.set_yticklabels(merged_sorted['service'])
ax.set_xlabel('Rank (1 = most critical)')
ax.set_title('Hotel Reservation — Classical vs. Hybrid Criticality Rank')
ax.legend(loc='lower right', framealpha=0.6)
ax.grid(axis='x', linestyle='--', alpha=0.4)
ax.invert_yaxis()
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'hotel_rank_comparison.png'), bbox_inches='tight')
plt.close()
print("Plot 2 saved: hotel_rank_comparison.png")

# ===========================================================================
# PLOT 3: Hybrid Criticality Score vs Recovery Time (Scatter)
# ===========================================================================
fig, ax = plt.subplots(figsize=(7, 5))
sc = ax.scatter(merged['hybrid_criticality'], merged['recovery_time_s'],
                c=merged['hybrid_rank'], cmap='RdYlGn_r',
                s=110, edgecolors='white', linewidths=0.8, zorder=3)

for _, row in merged.iterrows():
    ax.annotate(row['service'],
                xy=(row['hybrid_criticality'], row['recovery_time_s']),
                xytext=(5, 3), textcoords='offset points', fontsize=8.5)

# Fit line if variance exists
if merged['hybrid_criticality'].std() > 0 and merged['recovery_time_s'].std() > 0:
    rho, pval = stats.spearmanr(merged['hybrid_criticality'], merged['recovery_time_s'])
    ax.set_title(f'Hotel Reservation — Hybrid Criticality vs. Recovery Time\nSpearman ρ = {rho:.3f}, p = {pval:.3f}')
else:
    ax.set_title('Hotel Reservation — Hybrid Criticality Score vs. Mean Recovery Time')

plt.colorbar(sc, ax=ax, label='Hybrid Rank')
ax.set_xlabel('Hybrid Criticality Score')
ax.set_ylabel('Mean Recovery Time (s)')
ax.grid(linestyle='--', alpha=0.4)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'hotel_scatter_hybrid_vs_recovery.png'), bbox_inches='tight')
plt.close()
print("Plot 3 saved: hotel_scatter_hybrid_vs_recovery.png")

# ===========================================================================
# PLOT 4: Correlation Heatmap for Hotel
# ===========================================================================
metrics = ['degree', 'in_degree', 'out_degree', 'betweenness', 'closeness',
           'eigenvector', 'pagerank', 'hybrid_criticality']
impacts = ['recovery_time_s', 'error_rate_delta', 'latency_p95_delta_ms', 'downstream_affected_count']
impact_labels = ['Recovery Time (s)', 'Error Rate Delta', 'P95 Latency Delta (ms)', 'Downstream Count']

rho_matrix = np.zeros((len(metrics), len(impacts)))
pval_matrix = np.zeros((len(metrics), len(impacts)))

for i, m in enumerate(metrics):
    for j, imp in enumerate(impacts):
        if merged[m].std() > 0 and merged[imp].std() > 0:
            rho, p = stats.spearmanr(merged[m], merged[imp])
            rho_matrix[i, j] = rho
            pval_matrix[i, j] = p
        else:
            rho_matrix[i, j] = 0.0
            pval_matrix[i, j] = 1.0

fig, ax = plt.subplots(figsize=(9, 6))
im = ax.imshow(rho_matrix, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')

ax.set_xticks(range(len(impact_labels)))
ax.set_xticklabels(impact_labels, rotation=25, ha='right')
ax.set_yticks(range(len(metrics)))
ax.set_yticklabels([m.replace('_', ' ').title() for m in metrics])

for i in range(len(metrics)):
    for j in range(len(impacts)):
        sig = '*' if pval_matrix[i, j] < 0.05 else ''
        ax.text(j, i, f'{rho_matrix[i, j]:.2f}{sig}',
                ha='center', va='center', fontsize=9,
                color='white' if abs(rho_matrix[i, j]) > 0.5 else 'black')

plt.colorbar(im, ax=ax, label="Spearman ρ")
ax.set_title('Hotel Reservation — Spearman ρ Correlation Heatmap\n(* p < 0.05)')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'hotel_correlation_heatmap.png'), bbox_inches='tight')
plt.close()
print("Plot 4 saved: hotel_correlation_heatmap.png")

# ===========================================================================
# PLOT 5: Kill vs Latency vs CPU — Recovery Time Overlay
# ===========================================================================
fig, ax = plt.subplots(figsize=(10, 5))
kill_times = df[df['fault_type']=='kill'].groupby('service')['recovery_time_s'].mean()
lat_times  = df[df['fault_type']=='latency'].groupby('service')['recovery_time_s'].mean()
cpu_times  = df[df['fault_type']=='cpu'].groupby('service')['recovery_time_s'].mean()

all_svcs = sorted(set(kill_times.index) | set(lat_times.index) | set(cpu_times.index))
x = np.arange(len(all_svcs))

ax.plot(x, [kill_times.get(s, 0) for s in all_svcs], 'o-',
        color=COLORS['kill'], label='Kill', linewidth=2, markersize=7)
ax.plot(x, [lat_times.get(s, 0) for s in all_svcs], 's--',
        color=COLORS['latency'], label='Latency', linewidth=2, markersize=7)
ax.plot(x, [cpu_times.get(s, 0) for s in all_svcs], '^:',
        color=COLORS['cpu'], label='CPU', linewidth=2, markersize=7)

ax.set_xticks(x)
ax.set_xticklabels(all_svcs, rotation=35, ha='right')
ax.set_xlabel('Service')
ax.set_ylabel('Mean Recovery Time (s)')
ax.set_title('Hotel Reservation — Recovery Time Profile by Fault Mode')
ax.legend(title='Fault Type', framealpha=0.5)
ax.grid(linestyle='--', alpha=0.4)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'hotel_fault_mode_comparison.png'), bbox_inches='tight')
plt.close()
print("Plot 5 saved: hotel_fault_mode_comparison.png")

# ===========================================================================
# PLOT 6: Topology Diagram — Hotel Reservation Service Graph
# ===========================================================================
try:
    import networkx as nx
    fig, ax = plt.subplots(figsize=(9, 6))
    G = nx.DiGraph()
    edges = [
        ('frontend', 'search'),
        ('frontend', 'recommendation'),
        ('frontend', 'reservation'),
        ('frontend', 'geo'),
        ('frontend', 'profile'),
        ('frontend', 'rate'),
        ('search', 'geo'),
        ('search', 'rate'),
        ('search', 'profile'),
    ]
    G.add_edges_from(edges)

    pos = {
        'frontend': (0, 0),
        'search': (2, 1),
        'recommendation': (2, 0.3),
        'reservation': (2, -0.3),
        'geo': (4, 1.5),
        'profile': (4, 0.5),
        'rate': (4, -0.3),
    }

    # Color by hybrid rank from data
    hr_map = dict(zip(centrality['service'], centrality['hybrid_rank']))
    max_rank = centrality['hybrid_rank'].max()
    node_colors = []
    for node in G.nodes():
        r = hr_map.get(node, max_rank)
        norm = (r - 1) / (max_rank - 1) if max_rank > 1 else 0
        node_colors.append(plt.cm.RdYlGn_r(norm))

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=1800, ax=ax, alpha=0.9)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=8.5, font_weight='bold')
    nx.draw_networkx_edges(G, pos, ax=ax, arrows=True,
                           arrowstyle='-|>', arrowsize=20,
                           edge_color='#555', width=1.8,
                           connectionstyle='arc3,rad=0.05')

    sm = plt.cm.ScalarMappable(cmap='RdYlGn_r',
                                norm=plt.Normalize(vmin=1, vmax=max_rank))
    sm.set_array([])
    plt.colorbar(sm, ax=ax, label='Hybrid Rank (1=most critical)', shrink=0.7)
    ax.set_title('Hotel Reservation — Service Dependency Graph\n(node color = hybrid criticality rank)')
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'hotel_dependency_graph.png'), bbox_inches='tight')
    plt.close()
    print("Plot 6 saved: hotel_dependency_graph.png")
except ImportError:
    print("networkx not available, skipping topology plot")

print("\n✅ All Hotel Reservation plots generated in:", OUT_DIR)
