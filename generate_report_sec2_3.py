#!/usr/bin/env python3
"""
generate_report_sec2_3.py
=========================
Generates Sections 2 (Project Description & Goals) and 3 (Technical Specification)
of the VIT BCSE497J Project-I report for:
  "Identifying Failure-Prone Microservices Using Graph Centrality Metrics"

Formatting: VIT BCSE497J standard
  - Section Header   : Times New Roman 14, Bold, UPPER CASE, centred, 1.5 line spacing
  - Sub-section       : Times New Roman 13, Bold, Title Case, left, 1.5 spacing
  - Sub-sub-section   : Times New Roman 12, Bold Italic, Title Case, left, 1.5 spacing
  - Body text         : Times New Roman 12, Justified, 1.15 line spacing
  - Margins           : 1 inch all sides, A4 paper
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, PageBreak, KeepTogether,
)
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ─────────────────────────────────────────────────────────────────
# Output path
# ─────────────────────────────────────────────────────────────────
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "report_sections_2_3.pdf"

PAGE_W, PAGE_H = A4
MARGIN = 1 * inch
CONTENT_W = PAGE_W - 2 * MARGIN

# ─────────────────────────────────────────────────────────────────
# Font Registration  (Times New Roman from Windows fonts)
# ─────────────────────────────────────────────────────────────────
_WIN_FONTS = {
    "TNR":    "C:/Windows/Fonts/times.ttf",
    "TNRB":   "C:/Windows/Fonts/timesbd.ttf",
    "TNRI":   "C:/Windows/Fonts/timesi.ttf",
    "TNRBI":  "C:/Windows/Fonts/timesbi.ttf",
}
_FALLBACKS = {
    "TNR": "Times-Roman", "TNRB": "Times-Bold",
    "TNRI": "Times-Italic", "TNRBI": "Times-BoldItalic",
}

F = {}
for key, path in _WIN_FONTS.items():
    if Path(path).exists():
        pdfmetrics.registerFont(TTFont(key, path))
        F[key] = key
    else:
        F[key] = _FALLBACKS[key]

TNR, TNRB, TNRI, TNRBI = F["TNR"], F["TNRB"], F["TNRI"], F["TNRBI"]


# ─────────────────────────────────────────────────────────────────
# Styles
# ─────────────────────────────────────────────────────────────────
def build_styles():
    return {
        "sec": ParagraphStyle(
            "sec", fontName=TNRB, fontSize=14,
            alignment=TA_CENTER, leading=14 * 1.5,
            spaceBefore=0, spaceAfter=8,
        ),
        "sub": ParagraphStyle(
            "sub", fontName=TNRB, fontSize=13,
            alignment=TA_LEFT, leading=13 * 1.5,
            spaceBefore=10, spaceAfter=4,
        ),
        "subsub": ParagraphStyle(
            "subsub", fontName=TNRBI, fontSize=12,
            alignment=TA_LEFT, leading=12 * 1.5,
            spaceBefore=8, spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "body", fontName=TNR, fontSize=12,
            alignment=TA_JUSTIFY, leading=12 * 1.15,
            firstLineIndent=0.5 * inch, spaceAfter=6,
        ),
        "blt": ParagraphStyle(
            "blt", fontName=TNR, fontSize=12,
            alignment=TA_JUSTIFY, leading=12 * 1.15,
            leftIndent=0.3 * inch, firstLineIndent=0,
            spaceAfter=4,
        ),
        "cap": ParagraphStyle(
            "cap", fontName=TNRI, fontSize=11,
            alignment=TA_CENTER, leading=11 * 1.15,
            spaceBefore=3, spaceAfter=6,
        ),
        "tbl_hdr": ParagraphStyle(
            "tbl_hdr", fontName=TNRB, fontSize=10,
            alignment=TA_LEFT, leading=10 * 1.2,
        ),
        "tbl_body": ParagraphStyle(
            "tbl_body", fontName=TNR, fontSize=10,
            alignment=TA_LEFT, leading=10 * 1.2,
        ),
    }


def b(text):
    """Wrap key term in bold tags."""
    return text  # inline <b>...</b> handled at call site


# ─────────────────────────────────────────────────────────────────
# Gantt Chart
# ─────────────────────────────────────────────────────────────────
def gantt_chart(S):
    months  = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"]
    tasks = [
        ("Task 1", "Literature Survey",                  [1,1,0,0,0,0,0,0]),
        ("Task 2", "Environment Setup & Deployment",     [1,1,1,0,0,0,0,0]),
        ("Task 3", "SDG Extraction Pipeline",            [0,1,1,1,0,0,0,0]),
        ("Task 4", "Centrality Computation Module",      [0,0,1,1,0,0,0,0]),
        ("Task 5", "Fault Injection & Measurement",      [0,0,0,1,1,1,0,0]),
        ("Task 6", "Statistical Analysis & Plots",       [0,0,0,0,1,1,0,0]),
        ("Task 7", "Testing & Validation",               [0,0,0,0,0,1,1,0]),
        ("Task 8", "Documentation & Report Writing",     [0,0,0,0,0,0,1,1]),
    ]

    header = ["Task", "Activity"] + months
    data   = [header]
    for tnum, tname, sched in tasks:
        row = [tnum, tname] + ["" for _ in sched]
        data.append(row)

    tw_task   = 0.55 * inch
    tw_act    = 2.20 * inch
    tw_month  = (CONTENT_W - tw_task - tw_act) / 8

    col_widths = [tw_task, tw_act] + [tw_month] * 8
    row_h      = [0.30 * inch] * (len(tasks) + 1)

    tbl = Table(data, colWidths=col_widths, rowHeights=row_h)

    BLUE  = colors.HexColor("#4472C4")
    LGREY = colors.HexColor("#D9D9D9")
    WHITE = colors.white
    FAINT = colors.HexColor("#EEF2FA")

    cmds = [
        ("FONTNAME",   (0, 0), (-1, 0),  TNRB),
        ("FONTNAME",   (0, 1), (-1, -1), TNR),
        ("FONTSIZE",   (0, 0), (-1, -1), 8),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("ALIGN",      (1, 0), (1, -1),  "LEFT"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.black),
        ("BACKGROUND", (0, 0), (-1,  0), LGREY),
        ("LEFTPADDING",(0, 0), (-1, -1), 3),
        ("RIGHTPADDING",(0, 0),(-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0,0),(-1, -1), 2),
    ]

    for ri, (_, _, sched) in enumerate(tasks, start=1):
        bg = FAINT if ri % 2 == 0 else WHITE
        cmds.append(("BACKGROUND", (0, ri), (1, ri), bg))
        for ci, active in enumerate(sched):
            col = ci + 2
            if active:
                cmds.append(("BACKGROUND", (col, ri), (col, ri), BLUE))
                cmds.append(("TEXTCOLOR",  (col, ri), (col, ri), WHITE))
            else:
                cmds.append(("BACKGROUND", (col, ri), (col, ri), bg))

    tbl.setStyle(TableStyle(cmds))
    return tbl


# ─────────────────────────────────────────────────────────────────
# Hardware / Software Specification Tables
# ─────────────────────────────────────────────────────────────────
def hw_table():
    rows = [
        ["Component", "Minimum Specification", "Recommended Specification"],
        ["Processor",
         "Intel Core i5 / AMD Ryzen 5\n4 cores, ≥ 2.0 GHz",
         "Intel Core i7 / AMD Ryzen 7\n8 cores, ≥ 3.0 GHz"],
        ["Memory (RAM)", "8 GB DDR4", "16 – 32 GB DDR4"],
        ["Storage",      "30 GB free SSD / HDD", "50 GB free NVMe SSD"],
        ["GPU",          "Not required", "Not required (CPU-only)"],
        ["Network",      "Local Docker bridge",  "Gigabit LAN"],
        ["Monitor",      "1920 × 1080 (Full HD)", "Full HD or higher"],
    ]
    cw = [1.2*inch, 2.5*inch, 2.6*inch]
    t  = Table(rows, colWidths=cw)
    LGREY = colors.HexColor("#D9D9D9")
    t.setStyle(TableStyle([
        ("FONTNAME",      (0,0), (-1, 0), TNRB),
        ("FONTNAME",      (0,1), (-1,-1), TNR),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ALIGN",         (0,0), (-1,-1), "LEFT"),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.black),
        ("BACKGROUND",    (0,0), (-1, 0), LGREY),
        ("ROWBACKGROUNDS",(0,1), (-1,-1),
         [colors.white, colors.HexColor("#F5F5F5")]),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING",   (0,0), (-1,-1), 4),
    ]))
    return t


def sw_table():
    rows = [
        ["Category", "Tool / Version", "Purpose"],
        ["Operating System",
         "Windows 11 + WSL2 /\nUbuntu 22.04 LTS / macOS 13+",
         "Host environment for Docker & Python"],
        ["Programming Language", "Python 3.11+",
         "All pipeline scripts, analysis & orchestration"],
        ["Development Environment", "VS Code / PyCharm",
         "Code editing, debugging, project management"],
        ["Graph Library", "NetworkX 3.1",
         "SDG construction & 7 centrality metric computation"],
        ["Data Analysis", "Pandas 2.0, NumPy 1.24, SciPy 1.11",
         "Aggregation, ranking, Spearman correlation"],
        ["Visualization", "Matplotlib 3.7, Seaborn 0.12",
         "Heatmaps, scatter plots, bar charts"],
        ["Container Platform", "Docker Desktop 4.0+ (WSL2)",
         "Multi-container microservice deployment"],
        ["Distributed Tracing", "Jaeger All-in-One v1.62.0",
         "Trace collection, span storage, REST API"],
        ["Load Generation", "Locust 2.15 / wrk2 (Docker)",
         "Synthetic HTTP traffic at 50 req/s"],
        ["Chaos Engineering", "Pumba (ghcr.io/alexei-led/pumba)",
         "Container SIGKILL & tc netem latency injection"],
        ["HTTP Client", "Requests 2.31",
         "Jaeger API queries & DeathStarBench API calls"],
        ["Testing Framework", "pytest 7.4",
         "Integration tests for post-fault recovery validation"],
        ["Build System", "setuptools 68.0, pip",
         "Package management & dependency installation"],
    ]
    cw = [1.4*inch, 2.1*inch, 2.8*inch]
    t  = Table(rows, colWidths=cw)
    LGREY = colors.HexColor("#D9D9D9")
    t.setStyle(TableStyle([
        ("FONTNAME",      (0,0), (-1, 0), TNRB),
        ("FONTNAME",      (0,1), (-1,-1), TNR),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ALIGN",         (0,0), (-1,-1), "LEFT"),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.black),
        ("BACKGROUND",    (0,0), (-1, 0), LGREY),
        ("ROWBACKGROUNDS",(0,1), (-1,-1),
         [colors.white, colors.HexColor("#F5F5F5")]),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING",   (0,0), (-1,-1), 4),
    ]))
    return t


# ─────────────────────────────────────────────────────────────────
# Section 2 Content
# ─────────────────────────────────────────────────────────────────
def section2(story, S):

    # ── Header ────────────────────────────────────────────────────
    story.append(Paragraph("2. PROJECT DESCRIPTION AND GOALS", S["sec"]))
    story.append(Spacer(1, 0.12 * inch))

    # ── 2.1 Literature Review ─────────────────────────────────────
    story.append(Paragraph("2.1 Literature Review", S["sub"]))

    lit = [
        "Barabási and Albert (1999) introduced the scale-free network model, demonstrating "
        "that real-world complex networks follow power-law degree distributions and that a "
        "small number of highly connected hub nodes dominate information flow. This foundational "
        "work established the theoretical basis for identifying structurally critical nodes "
        "using graph centrality, which our project directly adapts for microservice dependency "
        "graphs.",

        "Newman (2010) provided a comprehensive formalization of network centrality metrics, "
        "including betweenness centrality—defined as the fraction of all-pairs shortest paths "
        "that pass through a given node. This work supplies the mathematical grounding for "
        "quantifying which services act as bottlenecks in inter-service communication chains, "
        "a role that directly corresponds to cascading failure propagation in distributed "
        "systems.",

        "Gan et al. (2019) presented DeathStarBench, a suite of end-to-end microservice "
        "benchmarks that faithfully model industry-scale social networks, media streaming "
        "platforms, and hotel reservation systems. Their work provides the validated, "
        "reproducible experimental substrate on which our fault injection experiments are "
        "conducted, ensuring findings are relevant to real-world production deployments.",

        "Sigelman et al. (2010) introduced Dapper-style distributed tracing at Google, "
        "establishing the practice of propagating trace context across process boundaries "
        "so that the full causal chain of a request can be reconstructed. Jaeger, the "
        "open-source implementation adopted in this project, captures parent–child span "
        "relationships that enable dynamic construction of service call graphs, overcoming "
        "the fundamental limitation of static architecture documentation.",

        "Basiri et al. (2016) formalised Chaos Engineering through Netflix's Chaos Monkey "
        "program, establishing the principle of deliberately injecting failures into "
        "production-like environments to expose resilience weaknesses proactively. Their "
        "methodology of controlled, hypothesis-driven experiments forms the experimental "
        "backbone of this project, extended here with graph-theoretic prioritisation of "
        "fault targets.",

        "Beyer et al. (2016), in the Google Site Reliability Engineering handbook, articulated "
        "service dependency management and blast-radius minimisation as core SRE disciplines. "
        "Their framework of error budgets and Service Level Objectives (SLOs) provides the "
        "industry motivation for automatically ranking microservices by failure risk—the "
        "precise problem our graph centrality approach addresses.",

        "Nedelkoski et al. (2019) investigated fault localisation in microservice architectures "
        "using inter-service metric correlation and dependency analysis. While demonstrating "
        "the value of service relationships for root cause analysis, their approach required "
        "post-failure data. Our work extends this to the proactive dimension: ranking services "
        "by predicted blast radius before any incident occurs.",

        "Ma et al. (2020) applied PageRank-inspired walk algorithms to service dependency "
        "graphs for anomaly detection, showing that services with high stationary walk "
        "probability exhibited greater error propagation rates. This directly motivates "
        "the inclusion of PageRank as one of our seven evaluated centrality metrics and "
        "aligns with the hypothesis that walk-based importance scores reflect operational "
        "failure-propagation likelihood.",
    ]
    for p in lit:
        story.append(Paragraph(p, S["body"]))

    story.append(Spacer(1, 0.08 * inch))

    # ── 2.2 Research Gap ──────────────────────────────────────────
    story.append(Paragraph("2.2 Research Gap", S["sub"]))

    gaps = [
        "Despite the maturity of graph centrality theory and distributed-tracing "
        "infrastructure, a critical research gap persists at their intersection. No prior "
        "work has systematically and empirically validated whether static structural "
        "centrality metrics—derived from runtime trace-based Service Dependency Graphs "
        "(SDGs)—can predict the real-world blast radius of chaos fault-injection events.",

        "Existing fault localisation and anomaly detection literature focuses primarily on "
        "reactive root cause analysis: identifying the source of a failure after it has "
        "occurred. This project addresses the orthogonal, proactive dimension—can structural "
        "graph analysis rank services by failure risk before any incidents occur, enabling "
        "pre-emptive resilience investment?",

        "Furthermore, prior art typically employs either (a) static, manually maintained "
        "architecture diagrams that become stale in continuously deployed environments, or "
        "(b) single-metric evaluations that test only one centrality measure against one "
        "failure indicator. This project contributes a seven-metric comparative study "
        "evaluated across five independent blast radius dimensions, providing a holistic "
        "and statistically rigorous correlation matrix validated against real chaos "
        "experiments.",

        "Finally, the systematic identification of outliers—services where centrality "
        "predictions diverge significantly from empirical blast radius—has not been "
        "studied. Understanding False Negatives (structurally peripheral services that "
        "cause disproportionate damage, such as compose-post-service in our study) is "
        "essential for defining the limits of pure graph-theoretic risk models and "
        "motivating hybrid approaches that combine structural and semantic service "
        "knowledge.",
    ]
    for p in gaps:
        story.append(Paragraph(p, S["body"]))

    story.append(Spacer(1, 0.08 * inch))

    # ── 2.3 Objectives ────────────────────────────────────────────
    story.append(Paragraph("2.3 Objectives", S["sub"]))
    story.append(Paragraph(
        "The primary objectives of this project are defined below, each formulated as a "
        "Specific, Measurable, Achievable, Relevant, and Time-Bound (SMART) goal:",
        S["body"]))

    objs = [
        ("<b>SDG Extraction</b>: To dynamically construct a directed, weighted Service "
         "Dependency Graph from live Jaeger distributed traces collected from the "
         "DeathStarBench Social Network application, capturing all inter-service RPC "
         "call relationships and their associated latency characteristics."),
        ("<b>Centrality Computation</b>: To compute seven normalised graph centrality "
         "metrics—Degree, In-Degree, Out-Degree, Betweenness, Closeness, Eigenvector, "
         "and PageRank—for every microservice node in the SDG, using the NetworkX "
         "graph analysis library."),
        ("<b>Composite Ranking</b>: To derive a composite centrality score as the mean "
         "of normalised per-metric ranks, providing a single aggregate structural "
         "importance ranking across all seven dimensions."),
        ("<b>Chaos Fault Injection</b>: To systematically inject two fault types "
         "(container kill via SIGKILL and 100 ms network-latency injection via "
         "tc netem through Pumba) into each of the 12 application microservices, "
         "with two experimental repetitions per (service, fault-type) combination."),
        ("<b>Blast Radius Measurement</b>: To quantitatively measure fault impact "
         "across five dimensions—tail latency degradation (p95 and p99), error rate "
         "increase, number of downstream services affected, and system recovery "
         "time—collected from Jaeger traces during active fault windows."),
        ("<b>Statistical Correlation</b>: To compute Spearman's rank correlation "
         "coefficient (ρ) and two-tailed p-values between each centrality metric "
         "and each blast radius measure, identifying the graph structural properties "
         "that most reliably predict failure impact at the p < 0.05 significance level."),
        ("<b>Outlier Analysis</b>: To identify and qualitatively explain services "
         "where centrality rank and empirical blast-radius rank diverge by more than "
         "N/3 positions, exposing the limitations of static graph metrics and "
         "informing future hybrid risk models."),
        ("<b>Visualization</b>: To produce correlation heatmaps, centrality-vs-blast "
         "scatter plots, and composite score bar charts enabling communication of "
         "findings to non-specialist SRE practitioners."),
    ]
    for o in objs:
        story.append(Paragraph(f"• {o}", S["blt"]))

    story.append(Spacer(1, 0.08 * inch))

    # ── 2.4 Problem Statement ──────────────────────────────────────
    story.append(Paragraph("2.4 Problem Statement", S["sub"]))

    ps = [
        "In modern cloud-native architectures composed of dozens of independently deployed "
        "microservices, a single service failure can cascade through dependency chains and "
        "trigger system-wide outages affecting thousands of concurrent users. Site Reliability "
        "Engineers (SREs) currently lack a principled, data-driven methodology to proactively "
        "identify which microservices pose the greatest systemic risk, forcing reliance on "
        "subjective expertise or reactive post-incident analysis.",

        "This project addresses the following core research problem: <i>Can graph-theoretic "
        "centrality metrics, derived from dynamically extracted runtime Service Dependency "
        "Graphs, serve as statistically significant and practically useful predictors of the "
        "blast radius caused by fault injection in a representative microservice architecture?</i>",

        "The problem encompasses three interrelated sub-challenges: (1) the dynamic, automated "
        "construction of accurate SDGs from distributed trace data, avoiding the staleness "
        "inherent in manually maintained architecture diagrams; (2) the empirical quantification "
        "of blast radius across multiple orthogonal dimensions using controlled chaos "
        "experiments; and (3) the rigorous statistical validation of the structural-to-operational "
        "centrality correspondence hypothesis.",

        "Successfully solving this problem enables a shift from reactive incident response "
        "to proactive resilience engineering, empowering platform teams to quantitatively "
        "prioritise investment in redundancy, autoscaling, circuit breakers, and other "
        "fault-tolerance mechanisms based on objective graph-structural evidence.",
    ]
    for p in ps:
        story.append(Paragraph(p, S["body"]))

    story.append(Spacer(1, 0.08 * inch))

    # ── 2.5 Project Plan ──────────────────────────────────────────
    story.append(Paragraph("2.5 Project Plan", S["sub"]))
    story.append(Paragraph(
        "The project is planned over an eight-month timeline, structured into eight "
        "sequential phases aligned with the six-stage experimental pipeline. Each phase "
        "produces a concrete deliverable that feeds directly into the subsequent stage. "
        "The Gantt chart below illustrates task durations, sequencing, and overlapping "
        "phases.",
        S["body"]))
    story.append(Spacer(1, 0.10 * inch))
    story.append(gantt_chart(S))
    story.append(Spacer(1, 0.06 * inch))
    story.append(Paragraph("Fig. 1. Project Gantt Chart — Microservice Failure Analysis Pipeline",
                            S["cap"]))

    # ── Page break before Section 3 ───────────────────────────────
    story.append(PageBreak())


# ─────────────────────────────────────────────────────────────────
# Section 3 Content
# ─────────────────────────────────────────────────────────────────
def section3(story, S):

    # ── Header ────────────────────────────────────────────────────
    story.append(Paragraph("3. TECHNICAL SPECIFICATION", S["sec"]))
    story.append(Spacer(1, 0.12 * inch))

    # ── 3.1 Requirements ──────────────────────────────────────────
    story.append(Paragraph("3.1 Requirements", S["sub"]))

    # 3.1.1 Functional
    story.append(Paragraph("3.1.1   Functional", S["subsub"]))

    func = [
        ("<b>Trace Collection</b>: The system shall query the Jaeger REST API "
         "(/api/traces endpoint) to retrieve distributed trace data from the live "
         "DeathStarBench stack within a configurable lookback window and trace-count "
         "limit, exporting raw spans as structured JSON."),
        ("<b>SDG Construction</b>: The system shall parse Jaeger trace JSON to resolve "
         "parentSpanID→spanID relationships and map processID to service name, "
         "constructing a directed weighted NetworkX DiGraph where nodes represent "
         "services and edges represent inter-service RPC call dependencies annotated "
         "with call count and average latency."),
        ("<b>Graph Export</b>: The system shall export the constructed SDG to both "
         "GraphML format (for use with visual tools such as Gephi) and JSON node-link "
         "format for downstream programmatic consumption by analysis modules."),
        ("<b>Centrality Computation</b>: The system shall compute seven normalised "
         "centrality metrics per service node: Degree, In-Degree, Out-Degree, "
         "Betweenness, Closeness, Eigenvector, and PageRank (damping = 0.85), "
         "using NetworkX standard library implementations."),
        ("<b>Composite Scoring</b>: The system shall compute a composite centrality "
         "score as the mean of per-service normalised ranks across all seven metrics, "
         "and produce a composite rank where rank 1 denotes the structurally most "
         "critical service."),
        ("<b>Fault Injection Orchestration</b>: The system shall orchestrate "
         "per-service chaos cycles using Pumba, supporting Container Kill (SIGKILL) "
         "and Network Latency Injection (tc netem) fault types with configurable "
         "duration, jitter, and repetition count."),
        ("<b>Blast Radius Measurement</b>: During each fault window, the system shall "
         "query Jaeger to compute tail-latency percentiles (p95, p99), error rate "
         "fractions, downstream affected service count (services showing >2× baseline "
         "latency or new errors), and container recovery time in seconds."),
        ("<b>Statistical Correlation</b>: The system shall compute Spearman's rank "
         "correlation coefficient (ρ) and two-tailed p-values for all 40 combinations "
         "of eight centrality metrics and five blast radius measures using "
         "scipy.stats.spearmanr."),
        ("<b>Visualisation Generation</b>: The system shall produce Spearman "
         "correlation heatmaps, per-pair scatter plots annotated with service labels, "
         "and composite-score bar charts using Matplotlib and Seaborn."),
        ("<b>Outlier Detection</b>: The system shall identify services flagged as "
         "False Positives (high centrality, low blast) or False Negatives (low "
         "centrality, high blast) based on absolute rank discrepancy exceeding a "
         "configurable fraction threshold (default N/3)."),
        ("<b>Integration Testing</b>: After each fault recovery cycle the system shall "
         "execute pytest integration tests verifying core user flows (registration, "
         "login, post composition, timeline retrieval) to confirm functional system "
         "correctness."),
        ("<b>Experiment Logging</b>: The system shall append all experiment run "
         "records—service, fault type, repetition, all measured metrics—to a "
         "persistent CSV log file for full reproducibility and audit traceability."),
    ]
    for f in func:
        story.append(Paragraph(f"• {f}", S["blt"]))

    story.append(Spacer(1, 0.06 * inch))

    # 3.1.2 Non-Functional
    story.append(Paragraph("3.1.2   Non-Functional", S["subsub"]))

    nonfunc = [
        ("<b>Performance</b>: Trace collection and SDG construction shall complete "
         "within five minutes for a two-hour lookback window with up to 2,000 traces. "
         "Centrality computation shall complete within 30 seconds for graphs of up "
         "to 100 nodes."),
        ("<b>Scalability</b>: The SDG extraction and centrality computation pipeline "
         "shall accommodate microservice applications containing up to 100 service "
         "nodes without requiring architectural modification."),
        ("<b>Reliability</b>: The fault injection module shall guarantee container "
         "restart and service recovery verification before initiating the next "
         "experiment run, preventing state contamination between runs."),
        ("<b>Reproducibility</b>: All stochastic components shall use a fixed random "
         "seed (seed = 42). All experiment parameters, trace collection window "
         "boundaries, and Pumba command arguments shall be fully logged for exact "
         "replication of results."),
        ("<b>Portability</b>: The system shall operate on any platform supporting "
         "Docker Desktop 4.0+ and Python 3.11+, including Windows 11 with WSL2 "
         "backend, macOS 13+, and Ubuntu 22.04 LTS."),
        ("<b>Maintainability</b>: The codebase shall be organised into independent, "
         "single-responsibility Python modules with comprehensive docstrings and type "
         "annotations. All modules shall be covered by unit and integration tests "
         "using pytest."),
        ("<b>Security</b>: The fault injection module shall operate exclusively within "
         "the isolated Docker bridge network. No production systems shall be targeted. "
         "The Pumba container shall mount only /var/run/docker.sock."),
        ("<b>Usability</b>: All pipeline phases shall be executable via a single "
         "orchestrator script (run_full_experiment.py) with configurable CLI flags. "
         "A --dry-run mode shall allow plan inspection without execution."),
    ]
    for n in nonfunc:
        story.append(Paragraph(f"• {n}", S["blt"]))

    story.append(Spacer(1, 0.10 * inch))

    # ── 3.2 Feasibility Study ─────────────────────────────────────
    story.append(Paragraph("3.2 Feasibility Study", S["sub"]))

    # 3.2.1 Technical
    story.append(Paragraph("3.2.1   Technical Feasibility", S["subsub"]))
    tech = [
        ("<b>Technology Availability</b>: All core technologies—Docker, Python 3.11, "
         "Jaeger distributed tracing, NetworkX, SciPy, and Pumba—are mature, open-source, "
         "and actively maintained with extensive public documentation and community support."),
        ("<b>Algorithm Availability</b>: All seven centrality metrics are available as "
         "single-call standard functions in NetworkX. Spearman's rank correlation is "
         "provided by scipy.stats. No novel algorithm development is required; project "
         "effort is focused on integration and experimental design."),
        ("<b>Benchmark Availability</b>: DeathStarBench is a peer-reviewed, publicly "
         "available benchmark deployable via Docker Compose on commodity hardware, "
         "providing a reproducible and representative experimental substrate."),
        ("<b>Hardware Accessibility</b>: The full experiment stack runs on a single "
         "developer workstation with 16 GB RAM and 8 CPU cores—equipment accessible "
         "in any university computer science laboratory."),
        ("<b>Integration Feasibility</b>: All components communicate through standard "
         "interfaces: HTTP REST (Jaeger API), Docker SDK for Python (container "
         "management), and the Linux network namespace (Pumba tc netem injection)."),
    ]
    for t in tech:
        story.append(Paragraph(f"• {t}", S["blt"]))

    # 3.2.2 Economic
    story.append(Paragraph("3.2.2   Economic Feasibility", S["subsub"]))
    econ = [
        ("<b>Zero Licensing Cost</b>: All software components—Python, Docker Community "
         "Edition, Jaeger, NetworkX, Pumba, Matplotlib, and pytest—are open-source and "
         "available at no cost under permissive licences (Apache 2.0, MIT, BSD)."),
        ("<b>Infrastructure Cost</b>: Experiments run on existing university lab hardware "
         "or a personal developer laptop. Optional cloud deployment on an AWS EC2 "
         "m5.2xlarge spot instance (~$0.10/hour) would cost under ₹500 for a full "
         "experiment run."),
        ("<b>Return on Investment</b>: A single prevented enterprise production outage "
         "carries an average cost of $300,000 per hour (Gartner, 2022). The methodology "
         "produced by this project provides an overwhelming positive ROI by enabling "
         "targeted, evidence-based resilience investment."),
        ("<b>Maintenance Cost</b>: The open-source toolchain requires no licence renewals. "
         "The Python codebase requires only periodic dependency version updates, "
         "estimated at less than one engineering day per quarter."),
    ]
    for e in econ:
        story.append(Paragraph(f"• {e}", S["blt"]))

    # 3.2.3 Social
    story.append(Paragraph("3.2.3   Social Feasibility", S["subsub"]))
    social = [
        ("<b>Industry Relevance</b>: The methodology directly addresses a pain point "
         "experienced by Site Reliability Engineering teams at technology organisations "
         "of all sizes. The output—a ranked risk table of microservices—is immediately "
         "actionable without requiring graph theory expertise."),
        ("<b>User Acceptance</b>: SREs and platform engineers are already familiar with "
         "distributed tracing tools (Jaeger, Zipkin) and container orchestration (Docker, "
         "Kubernetes). The proposed system builds on existing tooling, minimising adoption "
         "friction and training overhead."),
        ("<b>Ethical Considerations</b>: All fault injection experiments are performed in "
         "isolated Docker environments on a local developer machine using a benchmark "
         "application containing no real user data. No production systems or personal "
         "information are involved."),
        ("<b>Impact on Workforce</b>: Automated service risk ranking augments SRE "
         "capabilities rather than replacing human engineering judgement. It frees "
         "engineers from time-consuming manual dependency audits, enabling focus on "
         "higher-level architectural resilience decisions."),
        ("<b>Knowledge Dissemination</b>: Findings will be documented in this project "
         "report, and the full experimental pipeline will be made publicly available, "
         "enabling the academic community to replicate, extend, and build upon the "
         "validated methodology."),
    ]
    for s in social:
        story.append(Paragraph(f"• {s}", S["blt"]))

    story.append(Spacer(1, 0.10 * inch))

    # ── 3.3 System Specification ──────────────────────────────────
    story.append(Paragraph("3.3 System Specification", S["sub"]))

    # Hardware
    story.append(Paragraph("3.3.1   Hardware Specification", S["subsub"]))
    story.append(Paragraph(
        "The following hardware specifications are required to deploy and execute the "
        "complete DeathStarBench microservice stack alongside the fault injection "
        "orchestrator and analysis pipeline:",
        S["body"]))
    story.append(Spacer(1, 0.06 * inch))
    story.append(hw_table())
    story.append(Spacer(1, 0.04 * inch))
    story.append(Paragraph("Table 1. Hardware Specification", S["cap"]))
    story.append(Spacer(1, 0.06 * inch))

    # Software
    story.append(Paragraph("3.3.2   Software Specification", S["subsub"]))
    story.append(Paragraph(
        "The software ecosystem required to execute the full six-phase experiment "
        "pipeline is listed below. All tools are open-source and cross-platform "
        "compatible:",
        S["body"]))
    story.append(Spacer(1, 0.06 * inch))
    story.append(sw_table())
    story.append(Spacer(1, 0.04 * inch))
    story.append(Paragraph("Table 2. Software Specification", S["cap"]))


# ─────────────────────────────────────────────────────────────────
# Page-number footer
# ─────────────────────────────────────────────────────────────────
_pn_font = TNR

def _add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont(_pn_font, 10)
    num = canvas.getPageNumber()
    canvas.drawCentredString(PAGE_W / 2, 0.45 * inch, str(num))
    canvas.restoreState()


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────
def main():
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
        title="Microservice Failure Analysis — Sections 2 & 3",
        author="VIT University — BCSE497J Project-I",
    )

    S = build_styles()
    story = []

    section2(story, S)
    section3(story, S)

    doc.build(story,
              onFirstPage=_add_page_number,
              onLaterPages=_add_page_number)

    print(f"\n[OK] PDF generated successfully:")
    print(f"     {OUTPUT}")
    print(f"     Size: {OUTPUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
