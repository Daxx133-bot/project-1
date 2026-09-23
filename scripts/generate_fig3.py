import matplotlib.pyplot as plt
import matplotlib.patches as patches

fig, ax = plt.subplots(figsize=(15, 4))
ax.set_xlim(0, 7)
ax.set_ylim(0, 2)
ax.axis('off')

# Data for boxes
steps = [
    {"title": "Step 1: Stack Up", "desc": "(1) Stack brought up\nDocker Compose", "color": "#4B8BBE"},
    {"title": "Step 2: Warm-up", "desc": "(2) 60s warm-up\nwith wrk2 load", "color": "#5D9C59"},
    {"title": "Step 3: Extract Graph", "desc": "(3) Jaeger traces\nqueried & SDG built", "color": "#FF9900"},
    {"title": "Step 4: Fault Inject", "desc": "(4) Fault injected\nvia Pumba", "color": "#D34336"},
    {"title": "Step 5: Collect Data", "desc": "(5) Impact metrics\ncollected 30-60s", "color": "#8E44AD"},
    {"title": "Step 6: Reset", "desc": "(6) Stack reset\nnext run begins", "color": "#7F8C8D"}
]

box_w = 0.95
box_h = 1.0
start_x = 0.2

for i, step in enumerate(steps):
    x = start_x + i * 1.1
    y = 0.5
    
    # Create Box
    rect = patches.FancyBboxPatch((x, y), box_w, box_h, boxstyle="round,pad=0.05", 
                                  linewidth=2, edgecolor='black', facecolor=step["color"], alpha=0.85)
    ax.add_patch(rect)
    
    # Add Text
    ax.text(x + box_w/2, y + box_h - 0.25, step["title"], ha='center', va='center', 
            fontsize=11, fontweight='bold', color='white', family='sans-serif')
    ax.text(x + box_w/2, y + 0.35, step["desc"], ha='center', va='center', 
            fontsize=9.5, color='white', family='sans-serif', linespacing=1.5)
            
    # Add Arrow between boxes
    if i < len(steps) - 1:
        ax.annotate('', xy=(x + box_w + 0.15, y + box_h/2), 
                    xytext=(x + box_w, y + box_h/2),
                    arrowprops=dict(facecolor='black', arrowstyle='-|>', lw=2, mutation_scale=15))

plt.title('Figure 3: Experimental workflow', fontsize=16, fontweight='bold', y=0.9, family='serif')
plt.savefig(r'C:\Users\daksh\.gemini\antigravity-ide\brain\554b5cc2-285e-49fe-ab57-5cbf6744cd41\figure3_experimental_workflow.png', dpi=300, bbox_inches='tight')
print("Figure 3 generated successfully.")
