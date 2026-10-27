"""
make_report_figures.py -- draw the figures that only the project report needs.

Outputs (report/figures/)
  fig_gantt.png        project timeline, built from the dates of this repository's commits
  fig_dfd_level0.png   data flow diagram, context level
  fig_dfd_level1.png   data flow diagram, level 1, one process per pipeline stage
  fig_use_case.png     use case diagram
  fig_sequence.png     sequence diagram of one campaign run (tools/run_pilot.py, one_run)
  gantt_phases.csv     the phase boundaries and commit counts behind fig_gantt.png

The Gantt chart contains no planned dates. Each phase ends at a milestone commit named in
PHASES, and its bar runs from the date of its first commit to the date of its last. The
diagrams name the repository files that carry out each step; they contain no measured
values. Every result figure in the report comes from paper/figures/, not from here.

Run: python report/make_report_figures.py
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import re
import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, "figures")
DPI = 200

# (phase label, regular expression matching the subject of the commit that closes the
# phase). The last phase runs to the newest commit.
PHASES = [
    ("Original pipeline and Review-2 draft", r"^snapshot before audit"),
    ("Integrity audit and remediation", r"^add PREREGISTRATION\.md"),
    ("Pilot runs, graph reconstruction, preregistration", r"^LOCK preregistration"),
    ("Fault-injection campaign", r"^campaign complete"),
    ("Confirmatory analysis and verification",
     r"^regenerate paper/ artifacts so the recorded commit"),
    ("Paper, post hoc analyses and project report", None),
]

INK = "#1a1a1a"
FILL_PROCESS = "#dbe8f5"
FILL_ENTITY = "#f2f2f2"
FILL_STORE = "#fff6dc"
FILL_CASE = "#e8f1e4"


# ── Gantt chart from the commit history ──────────────────────────────────────

def commits():
    out = subprocess.run(["git", "-C", REPO, "log", "--reverse", "--date=short",
                          "--format=%ad%x09%s"], capture_output=True, text=True,
                         encoding="utf-8", check=True).stdout
    rows = []
    for line in out.splitlines():
        date, _, subject = line.partition("\t")
        rows.append((dt.date.fromisoformat(date), subject))
    return rows


def phases(rows):
    result, start = [], 0
    for label, closing in PHASES:
        if closing is None:
            end = len(rows) - 1
        else:
            hits = [i for i in range(start, len(rows)) if re.search(closing, rows[i][1])]
            if not hits:
                sys.exit("no commit closes phase %r (pattern %r)" % (label, closing))
            end = hits[0]
        part = rows[start:end + 1]
        result.append({"phase": label, "first_commit": part[0][0].isoformat(),
                       "last_commit": part[-1][0].isoformat(), "commits": len(part)})
        start = end + 1
    if start != len(rows):
        sys.exit("commits after the last phase were not assigned")
    return result


def gantt():
    table = phases(commits())
    with open(os.path.join(OUT, "gantt_phases.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)

    fig, ax = plt.subplots(figsize=(9.5, 3.6))
    for i, row in enumerate(table):
        a = dt.date.fromisoformat(row["first_commit"])
        b = dt.date.fromisoformat(row["last_commit"]) + dt.timedelta(days=1)
        y = len(table) - 1 - i
        ax.barh(y, (b - a).days, left=mdates.date2num(a), height=0.55,
                color="#4a7ab5", edgecolor=INK, linewidth=0.6)
        ax.text(mdates.date2num(b) + 0.6, y, "%s to %s" % (row["first_commit"][5:],
                                                         row["last_commit"][5:]),
                va="center", fontsize=7.5, color=INK)
    ax.set_yticks(range(len(table)))
    ax.set_yticklabels([r["phase"] for r in reversed(table)], fontsize=8.5)
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.tick_params(axis="x", labelsize=7.5)
    first = dt.date.fromisoformat(table[0]["first_commit"])
    last = dt.date.fromisoformat(table[-1]["last_commit"])
    ax.set_xlim(mdates.date2num(first) - 1, mdates.date2num(last) + 9)
    ax.grid(axis="x", color="#cccccc", linewidth=0.5)
    ax.set_axisbelow(True)
    ax.set_xlabel("Date of commit (week starting Monday)", fontsize=8.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_gantt.png"), dpi=DPI)
    plt.close(fig)
    return table


# ── drawing helpers for the diagrams ─────────────────────────────────────────

def canvas(w, h, size):
    fig, ax = plt.subplots(figsize=size)
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def process(ax, x, y, num, text, w=3.3, h=1.35):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                boxstyle="round,pad=0.02,rounding_size=0.35",
                                facecolor=FILL_PROCESS, edgecolor=INK, linewidth=1))
    ax.plot([x - w / 2, x + w / 2], [y + h / 2 - 0.38] * 2, color=INK, linewidth=0.7)
    ax.text(x, y + h / 2 - 0.19, num, ha="center", va="center", fontsize=8, weight="bold")
    ax.text(x, y - 0.17, text, ha="center", va="center", fontsize=7.6, linespacing=1.15)
    return (x, y, w, h)


def entity(ax, x, y, text, w=3.1, h=1.0, duplicate=False):
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, facecolor=FILL_ENTITY,
                           edgecolor=INK, linewidth=1.1))
    if duplicate:                     # DFD convention for an entity drawn twice
        ax.plot([x - w / 2, x - w / 2 + 0.3], [y - h / 2 + 0.3, y - h / 2], color=INK,
                linewidth=0.8)
    ax.text(x, y, text, ha="center", va="center", fontsize=8, linespacing=1.15)
    return (x, y, w, h)


def store(ax, x, y, ident, text, w=3.3, h=0.85):
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, facecolor=FILL_STORE,
                           edgecolor="none"))
    ax.plot([x - w / 2, x + w / 2], [y + h / 2] * 2, color=INK, linewidth=1)
    ax.plot([x - w / 2, x + w / 2], [y - h / 2] * 2, color=INK, linewidth=1)
    ax.plot([x - w / 2, x - w / 2], [y - h / 2, y + h / 2], color=INK, linewidth=1)
    ax.plot([x - w / 2 + 0.55] * 2, [y - h / 2, y + h / 2], color=INK, linewidth=0.7)
    ax.text(x - w / 2 + 0.275, y, ident, ha="center", va="center", fontsize=7.6,
            weight="bold")
    ax.text(x + 0.27, y, text, ha="center", va="center", fontsize=7.4, linespacing=1.1)
    return (x, y, w, h)


def edge_point(node, toward):
    """Point on the border of a box node in the direction of another point."""
    x, y, w, h = node
    tx, ty = toward
    dx, dy = tx - x, ty - y
    if dx == 0 and dy == 0:
        return x, y
    sx = (w / 2) / abs(dx) if dx else float("inf")
    sy = (h / 2) / abs(dy) if dy else float("inf")
    s = min(sx, sy)
    return x + dx * s, y + dy * s


def flow(ax, a, b, label="", rad=0.0, offset=(0, 0.22), dashed=False, fs=7.0):
    p = edge_point(a, b[:2])
    q = edge_point(b, a[:2])
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=11,
                                 connectionstyle="arc3,rad=%s" % rad, color=INK,
                                 linewidth=0.9, linestyle="--" if dashed else "-"))
    if label:
        mx, my = (p[0] + q[0]) / 2 + offset[0], (p[1] + q[1]) / 2 + offset[1]
        ax.text(mx, my, label, ha="center", va="center", fontsize=fs, color="#333333",
                linespacing=1.1, bbox=dict(facecolor="white", edgecolor="none", pad=0.6))


# ── data flow diagrams ───────────────────────────────────────────────────────

def dfd_level0():
    fig, ax = canvas(16, 8.2, (10, 5.1))
    sysbox = process(ax, 8, 4.1, "0", "Fault-injection and\nanalysis pipeline", w=4.2, h=2.0)
    res = entity(ax, 1.9, 4.1, "Researcher")
    app = entity(ax, 14.0, 6.6, "Application stack\n(DeathStarBench\ncontainers)", h=1.3)
    jae = entity(ax, 14.0, 1.6, "Jaeger tracing\nbackend", h=1.1)
    flow(ax, res, sysbox, "locked analysis plan,\ncampaign manifest", rad=-0.25,
         offset=(0, 0.75))
    flow(ax, sysbox, res, "run records, numbers,\ntables, figures", rad=-0.25,
         offset=(0, -0.75))
    flow(ax, sysbox, app, "load requests; kill, delay\nand restore commands", rad=0.0,
         offset=(-0.4, 0.55))
    flow(ax, jae, sysbox, "trace spans", rad=0.0, offset=(0.4, -0.35))
    flow(ax, app, jae, "spans emitted by\nthe services", rad=0.0, offset=(1.3, 0),
         dashed=True)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_dfd_level0.png"), dpi=DPI)
    plt.close(fig)


def dfd_level1():
    fig, ax = canvas(21.2, 15.0, (13, 9.2))
    r0, r1, r2, r3, r4 = 13.7, 10.4, 7.1, 3.8, 1.0
    c1, c2, c3, c4, c5 = 1.9, 6.3, 10.7, 15.1, 19.3

    d3 = store(ax, c1, r0, "D3", "Run manifest\ndata/campaign/manifest.json")
    p3 = process(ax, c2, r0, "3.0", "Execute one run\ntools/run_campaign.py,\ntools/run_pilot.py")
    app = entity(ax, c3, r0, "Application stack\n(DeathStarBench)", w=3.3, h=1.1)

    jae = entity(ax, c1, r1, "Jaeger tracing\nbackend", h=1.1)
    p1 = process(ax, c2, r1, "1.0", "Reconstruct dependency\ngraph\ntools/extract_graph.py")
    d1 = store(ax, c3, r1, "D1", "Dependency graphs\ndata/graphs/")
    p2 = process(ax, c4, r1, "2.0", "Compute predictors\ntools/build_predictor_\ntable.py")
    d2 = store(ax, c5, r1, "D2", "Predictor table\ndata/analysis/")

    jae2 = entity(ax, c1, r2, "Jaeger tracing\nbackend", h=1.1, duplicate=True)
    p4 = process(ax, c2, r2, "4.0", "Measure outcomes\nmeasurement/metrics_\ncollector.py, blast_radius.py,\nrecovery_probe.py", h=1.7)
    d5 = store(ax, c3, r2, "D5", "Run records\ndata/campaign/runs/")
    p5 = process(ax, c4, r2, "5.0", "Statistical analysis\nanalysis/final/run_\nconfirmatory_analysis.py")

    d4 = store(ax, c2, r3, "D4", "Stored raw spans\ndata/spans/")
    d6 = store(ax, c4, r3, "D6", "Analysis outputs\nanalysis/final/*.csv")
    p6 = process(ax, c5, r3, "6.0", "Build numbers, tables\nand figures\npaper/build_all.py")
    res = entity(ax, c5, r4, "Researcher", h=0.9)

    flow(ax, d3, p3, "next pending run")
    flow(ax, p3, app, "load; fault and\nrestore commands")
    flow(ax, jae, p1, "spans of the\ngraph traces")
    flow(ax, p1, d1, "caller-to-callee\nedges")
    flow(ax, d1, p2, "graph")
    flow(ax, p2, d2, "predictors")
    flow(ax, jae2, p4, "baseline, fault and\nprobe-window spans")
    flow(ax, d1, p4, "graph", offset=(0.35, 0.2))
    flow(ax, p4, d5, "run record")
    flow(ax, p4, d4, "raw spans", offset=(0.75, 0))
    flow(ax, d5, p5, "runs")
    flow(ax, d2, p5, "predictors", offset=(0.4, 0.15))
    flow(ax, p5, d6, "test results", offset=(0.8, 0))
    flow(ax, d6, p6, "outputs")
    flow(ax, p6, res, "numbers.csv,\ntables, figures", offset=(1.2, 0))
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_dfd_level1.png"), dpi=DPI)
    plt.close(fig)


# ── use case diagram ─────────────────────────────────────────────────────────

def actor(ax, x, y, name):
    ax.add_patch(Ellipse((x, y + 1.15), 0.5, 0.5, facecolor="white", edgecolor=INK, lw=1))
    ax.plot([x, x], [y + 0.9, y + 0.15], color=INK, lw=1)
    ax.plot([x - 0.45, x + 0.45], [y + 0.65, y + 0.65], color=INK, lw=1)
    ax.plot([x, x - 0.38], [y + 0.15, y - 0.45], color=INK, lw=1)
    ax.plot([x, x + 0.38], [y + 0.15, y - 0.45], color=INK, lw=1)
    ax.text(x, y - 0.8, name, ha="center", va="top", fontsize=8.5)
    return (x, y + 0.4)


def case(ax, x, y, text, w=4.6, h=1.0):
    ax.add_patch(Ellipse((x, y), w, h, facecolor=FILL_CASE, edgecolor=INK, lw=0.9))
    ax.text(x, y, text, ha="center", va="center", fontsize=7.8, linespacing=1.1)
    return (x, y, w, h)


def link(ax, a, c, side):
    x = c[0] - c[2] / 2 if side == "left" else c[0] + c[2] / 2
    ax.plot([a[0], x], [a[1], c[1]], color=INK, lw=0.8)


def include(ax, base, inc):
    flow(ax, base, inc, "«include»", dashed=True, offset=(0.95, 0.0), fs=6.8)


def use_case():
    fig, ax = canvas(17, 11.6, (10.5, 7.2))
    ax.add_patch(Rectangle((3.1, 0.3), 10.8, 11.0, facecolor="none", edgecolor=INK, lw=1))
    ax.text(8.5, 11.0, "Failure-impact study pipeline", ha="center", va="center",
            fontsize=9, weight="bold")
    researcher = actor(ax, 1.4, 5.6, "Researcher")
    reviewer = actor(ax, 15.6, 5.6, "Reviewer")
    lock = case(ax, 6.2, 10.0, "Lock the analysis plan")
    graph = case(ax, 6.2, 8.6, "Reconstruct dependency\ngraphs from traces")
    camp = case(ax, 6.2, 7.0, "Run the fault-injection\ncampaign")
    gate = case(ax, 6.2, 4.4, "Check run integrity\n(pre-analysis gates)")
    ana = case(ax, 8.5, 2.9, "Run the confirmatory\nanalysis")
    build = case(ax, 8.5, 1.3, "Regenerate numbers,\ntables and figures")
    inspect = case(ax, 11.6, 4.4, "Inspect run records\nand stored spans", w=4.0)
    inj = case(ax, 11.4, 8.0, "Inject a fault into\none service", w=3.8)
    meas = case(ax, 11.4, 6.2, "Measure degraded\nservices and recovery", w=3.8)
    for c in (lock, graph, camp, gate):
        link(ax, researcher, c, "left")
    for c in (ana, build):
        link(ax, researcher, c, "left")
        link(ax, reviewer, c, "right")
    link(ax, reviewer, inspect, "right")
    include(ax, camp, inj)
    include(ax, camp, meas)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_use_case.png"), dpi=DPI)
    plt.close(fig)


# ── sequence diagram of one run ──────────────────────────────────────────────

def sequence():
    names = ["Campaign runner\nrun_campaign.py", "one_run()\nrun_pilot.py", "Locust",
             "Docker and\nPumba", "Application\nstack", "Jaeger"]
    xs = [1.3, 4.3, 7.3, 10.0, 12.7, 15.4]
    top, bottom = 13.0, 0.4
    fig, ax = canvas(16.8, 13.9, (10.5, 8.7))
    for x, n in zip(xs, names):
        ax.add_patch(Rectangle((x - 1.15, top), 2.3, 0.85, facecolor=FILL_ENTITY,
                               edgecolor=INK, lw=1))
        ax.text(x, top + 0.425, n, ha="center", va="center", fontsize=7.5, linespacing=1.1)
        ax.plot([x, x], [bottom, top], color="#777777", lw=0.8, linestyle=(0, (4, 3)))

    steps = [
        (0, 1, "next pending run (application, service, fault, repetition)"),
        (1, 3, "find the one container whose compose label equals the service"),
        (1, 2, "start the load against the gateway"),
        (2, 4, "weighted mix of requests"),
        (1, 5, "after W s: baseline spans"),
        (1, 3, "kill (SIGKILL) or netem delay on the target"),
        (3, 4, "fault applied to the target container"),
        (1, 5, "after H s: fault-window spans; degraded services"),
        (1, 3, "kill: compose up -d; latency: wait for Pumba to exit"),
        (1, 5, "probe every P s until recovered or cap C"),
        (1, 3, "latency only: recreate the target container"),
        (1, 2, "stop the load"),
        (1, 0, "run record (with stored spans)"),
    ]
    y = top - 0.75
    for a, b, text in steps:
        x1, x2 = xs[a], xs[b]
        ax.add_patch(FancyArrowPatch((x1, y), (x2, y), arrowstyle="-|>", mutation_scale=10,
                                     color=INK, lw=0.9,
                                     linestyle="--" if b < a else "-"))
        ax.text((x1 + x2) / 2, y + 0.2, text, ha="center", va="bottom", fontsize=6.9,
                bbox=dict(facecolor="white", edgecolor="none", pad=0.3))
        y -= 0.93
    ax.add_patch(Rectangle((xs[1] - 0.12, y + 0.5), 0.24, top - 0.45 - (y + 0.5),
                           facecolor="#dbe8f5", edgecolor=INK, lw=0.7, zorder=0))
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_sequence.png"), dpi=DPI)
    plt.close(fig)


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    table = gantt()
    dfd_level0()
    dfd_level1()
    use_case()
    sequence()
    for row in table:
        print("%-52s %s to %s  (%d commits)" % (row["phase"], row["first_commit"],
                                               row["last_commit"], row["commits"]))
    print("figures written to report/figures/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
