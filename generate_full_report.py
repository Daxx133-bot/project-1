# -*- coding: utf-8 -*-
"""
generate_full_report.py
Generates the complete VIT BCSE497J Project-I report as a .docx Word file.
Project: Identifying Failure-Prone Microservices Using Graph Centrality Metrics

Formatting matches the VIT BCSE497J template:
  Section Header : TNR 14 Bold, ALL CAPS, Centred, 1.5 line spacing
  Sub-section    : TNR 13 Bold, Title Case, Left, 1.5 line spacing
  Sub-sub-section: TNR 12 Bold Italic, Title Case, Left, 1.5 line spacing
  Body text      : TNR 12, Justified, 1.15 line spacing, 0.5in first-line indent
  Page size      : A4, 1-inch margins all sides
"""

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent / "BCSE497J_Microservice_Failure_Analysis_Report.docx"
TNR = "Times New Roman"

# ---------------------------------------------------------------------------
# Low-level XML helpers
# ---------------------------------------------------------------------------

def set_cell_bg(cell, hex_color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def set_cell_borders(cell, color="000000"):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        el = OxmlElement("w:" + side)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        tcBorders.append(el)
    tcPr.append(tcBorders)


def remove_table_borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    tblBorders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + side)
        el.set(qn("w:val"), "none")
        tblBorders.append(el)
    tblPr.append(tblBorders)


def add_box_border(para, color="4472C4"):
    pPr = para._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    for side in ("top", "left", "bottom", "right"):
        el = OxmlElement("w:" + side)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "6")
        el.set(qn("w:space"), "4")
        el.set(qn("w:color"), color)
        pBdr.append(el)
    pPr.append(pBdr)


# ---------------------------------------------------------------------------
# Paragraph / run helpers
# ---------------------------------------------------------------------------

def fmt_run(run, size=12, bold=False, italic=False):
    run.font.name = TNR
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic


def fmt_para(para, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
             line_spacing=1.15, before_pt=0, after_pt=6,
             first_indent_in=None, left_indent_in=None):
    pf = para.paragraph_format
    pf.alignment = align
    pf.line_spacing = line_spacing
    pf.space_before = Pt(before_pt)
    pf.space_after = Pt(after_pt)
    if first_indent_in is not None:
        pf.first_line_indent = Inches(first_indent_in)
    if left_indent_in is not None:
        pf.left_indent = Inches(left_indent_in)


def sec_hdr(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text.upper())
    fmt_run(r, size=14, bold=True)
    fmt_para(p, align=WD_ALIGN_PARAGRAPH.CENTER,
             line_spacing=1.5, before_pt=6, after_pt=8)
    return p


def sub_hdr(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    fmt_run(r, size=13, bold=True)
    fmt_para(p, align=WD_ALIGN_PARAGRAPH.LEFT,
             line_spacing=1.5, before_pt=10, after_pt=4)
    return p


def subsub_hdr(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    fmt_run(r, size=12, bold=True, italic=True)
    fmt_para(p, align=WD_ALIGN_PARAGRAPH.LEFT,
             line_spacing=1.5, before_pt=7, after_pt=3)
    return p


def body(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    fmt_run(r, size=12)
    fmt_para(p, first_indent_in=0.5, after_pt=6)
    return p


def blt(doc, parts):
    """
    Bullet paragraph.
    parts: plain string  OR  list of (text, bold) tuples
    """
    p = doc.add_paragraph()
    br = p.add_run("- ")
    fmt_run(br, size=12)
    if isinstance(parts, str):
        r = p.add_run(parts)
        fmt_run(r, size=12)
    else:
        for txt, bd in parts:
            r = p.add_run(txt)
            fmt_run(r, size=12, bold=bd)
    fmt_para(p, left_indent_in=0.3, first_indent_in=0, after_pt=4)
    return p


def centre(doc, text, size=12, bold=False, italic=False,
           before_pt=0, after_pt=6, spacing=1.5):
    p = doc.add_paragraph()
    r = p.add_run(text)
    fmt_run(r, size=size, bold=bold, italic=italic)
    fmt_para(p, align=WD_ALIGN_PARAGRAPH.CENTER,
             line_spacing=spacing, before_pt=before_pt, after_pt=after_pt)
    return p


def fig_caption(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    fmt_run(r, size=11, italic=True)
    fmt_para(p, align=WD_ALIGN_PARAGRAPH.CENTER,
             line_spacing=1.15, before_pt=2, after_pt=8)
    return p


def placeholder_box(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    fmt_run(r, size=11, italic=True)
    fmt_para(p, align=WD_ALIGN_PARAGRAPH.CENTER,
             line_spacing=1.0, before_pt=8, after_pt=4)
    add_box_border(p)
    return p


def set_page_a4(doc):
    for sec in doc.sections:
        sec.page_width  = Inches(8.27)
        sec.page_height = Inches(11.69)
        sec.left_margin   = Inches(1)
        sec.right_margin  = Inches(1)
        sec.top_margin    = Inches(1)
        sec.bottom_margin = Inches(1)


# ---------------------------------------------------------------------------
# Page number footer
# ---------------------------------------------------------------------------

def add_page_number_footer(doc):
    for section in doc.sections:
        footer = section.footer
        para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        para.clear()
        fmt_para(para, align=WD_ALIGN_PARAGRAPH.CENTER,
                 line_spacing=1.0, before_pt=0, after_pt=0)
        run = para.add_run()
        fmt_run(run, size=10)
        for tag, text in [("begin", ""), ("separate", ""), ("end", "")]:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), tag)
            run._r.append(fc)
            if tag == "begin":
                instr = OxmlElement("w:instrText")
                instr.text = "PAGE"
                instr.set(qn("xml:space"), "preserve")
                run._r.append(instr)


# ===========================================================================
# COVER PAGE
# ===========================================================================

def build_cover(doc):
    doc.add_paragraph()
    centre(doc, "BCSE497J - Project-I", size=14, bold=True, before_pt=20, after_pt=12)
    centre(doc,
           "IDENTIFYING FAILURE-PRONE MICROSERVICES\nUSING GRAPH CENTRALITY METRICS",
           size=16, bold=True, before_pt=12, after_pt=24)

    tbl = doc.add_table(rows=3, cols=2)
    remove_table_borders(tbl)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    students = [
        ("[Reg. No. 1]", "[STUDENT NAME 1]"),
        ("[Reg. No. 2]", "[STUDENT NAME 2]"),
        ("[Reg. No. 3]", "[STUDENT NAME 3]"),
    ]
    for i, (reg, name) in enumerate(students):
        for ci, txt in enumerate([reg, name]):
            c = tbl.rows[i].cells[ci]
            p = c.paragraphs[0]
            p.clear()
            r = p.add_run(txt)
            fmt_run(r, size=13, bold=True)
            fmt_para(p, align=WD_ALIGN_PARAGRAPH.CENTER,
                     line_spacing=1.5, before_pt=0, after_pt=0)

    doc.add_paragraph()
    centre(doc, "(Mention the particulars sorted on Register Number)",
           size=13, bold=True, italic=True, before_pt=4, after_pt=20)
    centre(doc, "Under the Supervision of", size=12, before_pt=8, after_pt=4)
    centre(doc, "[PROJECT GUIDE NAME]", size=12, bold=True, before_pt=0, after_pt=0)
    centre(doc, "[Designation]", size=12, before_pt=0, after_pt=0)
    centre(doc, "School of Computer Science and Engineering (SCOPE)",
           size=12, before_pt=0, after_pt=20)
    centre(doc, "B.Tech.", size=12, bold=True, before_pt=0, after_pt=0)
    centre(doc, "in", size=12, italic=True, before_pt=0, after_pt=0)
    centre(doc, "Computer Science and Engineering", size=12, bold=True, before_pt=0, after_pt=0)
    centre(doc, "[Specialization if any]", size=12, bold=True, italic=True,
           before_pt=0, after_pt=12)
    centre(doc, "School of Computer Science and Engineering",
           size=14, bold=True, before_pt=6, after_pt=16)
    centre(doc, "[ Insert VIT Logo Here ]", size=11, italic=True,
           before_pt=0, after_pt=12)
    centre(doc, "Vellore Institute of Technology", size=14, bold=True,
           before_pt=0, after_pt=2)
    centre(doc,
           "(Deemed to be University under section 3 of UGC Act, 1956)",
           size=10, italic=True, before_pt=0, after_pt=20)
    centre(doc, "September 2026", size=12, before_pt=8, after_pt=0)
    doc.add_page_break()


# ===========================================================================
# ABSTRACT
# ===========================================================================

def build_abstract(doc):
    sec_hdr(doc, "ABSTRACT")

    body(doc,
         "The rapid growth of cloud-native microservice architectures has introduced "
         "significant challenges in ensuring system resilience, as a single service failure "
         "can cascade through dependency chains and cause widespread outages. Traditional "
         "approaches to identifying failure-prone services rely on manual architectural "
         "reviews and post-incident analysis, which are both subjective and reactive. "
         "This project proposes and validates a data-driven, proactive methodology that "
         "leverages graph-theoretic centrality metrics to predict the blast radius of "
         "service failures before they occur in production.")

    body(doc,
         "The experimental platform is the DeathStarBench Social Network application, "
         "a peer-reviewed industry-representative benchmark comprising 12 interdependent "
         "microservices deployed on Docker Compose. A dynamic Service Dependency Graph "
         "(SDG) is automatically constructed from live Jaeger distributed traces, "
         "capturing all inter-service RPC relationships. Seven graph centrality metrics "
         "are computed on the SDG using the NetworkX library: Degree, In-Degree, "
         "Out-Degree, Betweenness, Closeness, Eigenvector, and PageRank centrality.")

    body(doc,
         "Chaos fault injection experiments are conducted using the Pumba tool, injecting "
         "container kill (SIGKILL) and network latency (100 ms via tc netem) faults "
         "across all 12 microservices with two repetitions each, totalling 48 controlled "
         "experiment runs. Blast radius is quantified across five dimensions: tail latency "
         "degradation (p95 and p99), error rate increase, downstream services affected "
         "count, and system recovery time.")

    body(doc,
         "Spearman rank correlation analysis reveals that In-Degree Centrality is the "
         "strongest single predictor of error rate spikes (rho = 0.82, p = 0.0011), "
         "while Betweenness Centrality best predicts the downstream blast radius "
         "(rho = 0.73, p = 0.0075). The composite centrality score achieves exceptional "
         "correlation with all failure dimensions (rho = -0.92 for error rate, p < 0.0001). "
         "Outlier analysis identifies compose-post-service as a critical False Negative: "
         "its structural rank (7th) substantially underestimates its empirical blast rank "
         "(2nd), revealing a fundamental limitation of inward-looking centrality metrics "
         "for synchronous fan-out orchestrators.")

    p = doc.add_paragraph()
    r1 = p.add_run("Keywords")
    fmt_run(r1, size=12, bold=True, italic=True)
    r2 = p.add_run(
        " - Microservices, Graph Centrality, Chaos Engineering, Fault Injection, "
        "Distributed Tracing, Blast Radius, Spearman Correlation, Jaeger, "
        "DeathStarBench, Service Dependency Graph.")
    fmt_run(r2, size=12, italic=True)
    fmt_para(p, first_indent_in=0, before_pt=8, after_pt=0)

    doc.add_page_break()


# ===========================================================================
# TABLE OF CONTENTS
# ===========================================================================

def build_toc(doc):
    sec_hdr(doc, "TABLE OF CONTENTS")

    rows = [
        ("Sl.No", "Contents", "Page No."),
        ("",      "Abstract",                                    "i"),
        ("1.",    "INTRODUCTION",                                "1"),
        ("",      "    1.1  Background",                         "1"),
        ("",      "    1.2  Motivation",                         "1"),
        ("",      "    1.3  Scope of the Project",               "1"),
        ("2.",    "PROJECT DESCRIPTION AND GOALS",               ""),
        ("",      "    2.1  Literature Review",                  ""),
        ("",      "    2.2  Research Gap",                       ""),
        ("",      "    2.3  Objectives",                         ""),
        ("",      "    2.4  Problem Statement",                  ""),
        ("",      "    2.5  Project Plan",                       ""),
        ("3.",    "TECHNICAL SPECIFICATION",                     ""),
        ("",      "    3.1  Requirements",                       ""),
        ("",      "         3.1.1  Functional",                  ""),
        ("",      "         3.1.2  Non-Functional",              ""),
        ("",      "    3.2  Feasibility Study",                  ""),
        ("",      "         3.2.1  Technical Feasibility",       ""),
        ("",      "         3.2.2  Economic Feasibility",        ""),
        ("",      "         3.2.3  Social Feasibility",          ""),
        ("",      "    3.3  System Specification",               ""),
        ("",      "         3.3.1  Hardware Specification",      ""),
        ("",      "         3.3.2  Software Specification",      ""),
        ("4.",    "DESIGN APPROACH AND DETAILS",                 ""),
        ("",      "    4.1  System Architecture",                ""),
        ("",      "    4.2  Design",                             ""),
        ("",      "         4.2.1  Data Flow Diagram",           ""),
        ("",      "         4.2.2  Use Case Diagram",            ""),
        ("",      "         4.2.3  Class Diagram",               ""),
        ("",      "         4.2.4  Sequence Diagram",            ""),
        ("5.",    "REFERENCES",                                  ""),
    ]

    tbl = doc.add_table(rows=len(rows), cols=3)
    remove_table_borders(tbl)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    col_widths = [Inches(0.7), Inches(4.8), Inches(0.8)]

    for i, (num, content, page) in enumerate(rows):
        row = tbl.rows[i]
        for j, txt in enumerate([num, content, page]):
            c = row.cells[j]
            c.width = col_widths[j]
            p = c.paragraphs[0]
            p.clear()
            is_hdr = (i == 0)
            is_sec = (txt.isupper() and txt.strip() and i > 0)
            r = p.add_run(txt)
            fmt_run(r, size=12, bold=(is_hdr or is_sec))
            align = (WD_ALIGN_PARAGRAPH.CENTER if j in (0, 2)
                     else WD_ALIGN_PARAGRAPH.LEFT)
            fmt_para(p, align=align, line_spacing=1.5,
                     before_pt=0, after_pt=0)
            if is_hdr:
                set_cell_bg(c, "D9D9D9")
            set_cell_borders(c)

    doc.add_page_break()


# ===========================================================================
# SECTION 1 - INTRODUCTION
# ===========================================================================

def build_section1(doc):
    sec_hdr(doc, "1. INTRODUCTION")

    sub_hdr(doc, "1.1 Background")
    body(doc,
         "The rapid digitisation of global industries has led to the widespread adoption "
         "of cloud-native software architectures, with microservices emerging as the "
         "dominant paradigm for building scalable, independently deployable applications. "
         "In a microservice architecture, a complex application is decomposed into small, "
         "focused services, each responsible for a specific business capability, that "
         "communicate over the network via Remote Procedure Calls (RPC) or HTTP APIs. "
         "While this decomposition offers advantages in modularity, independent scaling, "
         "and continuous deployment, it introduces a critical challenge centred on "
         "inter-service dependency management.")
    body(doc,
         "A fundamental challenge in operating microservice systems at scale is the "
         "cascading failure problem. When a service experiences degradation, upstream "
         "services that synchronously depend on it begin accumulating unresolved requests, "
         "exhausting thread pools and connection buffers. This backpressure propagates "
         "upward through the call graph, potentially triggering a system-wide outage from "
         "a failure that originated in a single, seemingly minor component. The opacity "
         "of these dependency chains makes it exceedingly difficult for Site Reliability "
         "Engineers (SREs) to anticipate which service failures will have the most severe "
         "system-wide impact.")
    body(doc,
         "Graph theory offers a principled mathematical framework for analysing the "
         "structural properties of networked systems. By modelling the microservice "
         "architecture as a directed graph where nodes represent services and edges "
         "represent RPC dependencies, standard graph centrality metrics can quantify "
         "each service's structural importance. This project explores whether such "
         "metrics, derived from dynamic runtime distributed traces, can serve as "
         "statistically reliable predictors of real-world failure impact in a "
         "representative microservice benchmark.")

    sub_hdr(doc, "1.2 Motivation")
    body(doc,
         "The motivation for this research arises from a critical gap between the "
         "theoretical maturity of graph analysis and its practical adoption in cloud "
         "operations. Despite the widespread availability of distributed tracing "
         "infrastructure (Jaeger, Zipkin, AWS X-Ray), most organisations use trace data "
         "purely for post-incident debugging rather than proactive structural risk "
         "analysis. SREs at major cloud providers invest heavily in chaos engineering "
         "programmes to discover resilience weaknesses, but these programmes are typically "
         "executed without a principled ranking of which services are most likely to "
         "cause widespread damage when they fail.")
    body(doc,
         "The economic consequences of this knowledge gap are severe. Unplanned "
         "microservice outages at enterprise scale carry an average direct cost of "
         "$300,000 per hour in lost revenue and remediation effort (Gartner, 2022). "
         "A methodology that can automatically rank microservices by predicted blast "
         "radius would allow engineering teams to prioritise redundancy, autoscaling, "
         "circuit breaker placement, and chaos experiment targeting based on objective "
         "structural evidence rather than subjective intuition.")
    body(doc,
         "This project is motivated by the hypothesis that graph centrality metrics "
         "computed from runtime Service Dependency Graphs carry statistically significant "
         "predictive power for failure impact, providing a fast, low-cost, automated "
         "signal to guide resilience engineering decisions.")

    sub_hdr(doc, "1.3 Scope of the Project")
    body(doc,
         "The scope of this project encompasses the complete experimental pipeline "
         "from dynamic Service Dependency Graph construction to statistical correlation "
         "analysis. The study targets the DeathStarBench Social Network application, "
         "a peer-reviewed academic benchmark representing a social platform composed "
         "of 12 interconnected microservices deployed via Docker Compose. The choice "
         "of DeathStarBench ensures reproducibility and comparability with prior "
         "academic work in the distributed systems community.")
    body(doc,
         "The project covers the following in-scope areas: (1) automated SDG extraction "
         "from Jaeger distributed traces; (2) computation of seven graph centrality "
         "metrics using the NetworkX Python library; (3) controlled chaos fault injection "
         "using the Pumba tool with two fault types (container kill and network latency "
         "injection); (4) measurement of five blast radius dimensions (tail latency, "
         "error rate, downstream service count, recovery time); and (5) Spearman rank "
         "correlation analysis and outlier identification.")
    body(doc,
         "The following aspects are explicitly out of scope: microservice architectures "
         "employing asynchronous message passing, Kubernetes-based orchestration with "
         "self-healing autoscalers, multi-node distributed deployments, and Byzantine "
         "or data-corruption fault types. All experiments are conducted in an isolated "
         "local Docker environment; no production systems or real user data are involved.")

    doc.add_page_break()


# ===========================================================================
# SECTION 2 - PROJECT DESCRIPTION AND GOALS
# ===========================================================================

def build_section2(doc):
    sec_hdr(doc, "2. PROJECT DESCRIPTION AND GOALS")

    sub_hdr(doc, "2.1 Literature Review")
    body(doc,
         "Barabasi and Albert (1999) demonstrated that real-world complex networks "
         "exhibit scale-free degree distributions, where a small number of hub nodes "
         "dominate structural connectivity. This foundational result motivates the "
         "application of degree-based centrality metrics to microservice dependency "
         "graphs, where analogous hub services are expected to exhibit disproportionate "
         "failure influence.")
    body(doc,
         "Newman (2010) provided a rigorous treatment of betweenness centrality, "
         "defining it as the fraction of shortest inter-node paths that pass through "
         "a given vertex. In communication networks, high betweenness indicates "
         "bottleneck nodes through which information and failure propagation must "
         "necessarily flow. This definition maps naturally to microservice intermediaries "
         "that mediate calls between subsystems.")
    body(doc,
         "Page et al. (1999) introduced PageRank as a stationary random-walk probability "
         "distribution over directed link graphs. Adapted to service dependency graphs, "
         "PageRank assigns higher importance to services reached frequently by random "
         "call-chain traversals, providing a flow-aware centrality measure that "
         "complements simpler degree-based metrics.")
    body(doc,
         "Gan et al. (2019) presented DeathStarBench, a suite of end-to-end microservice "
         "benchmarks representing realistic industry workloads including social networks, "
         "media streaming services, and hotel reservation systems. Their work provides "
         "the reproducible experimental substrate used in this project, enabling direct "
         "comparison with future academic studies.")
    body(doc,
         "Sigelman et al. (2010) introduced Dapper, Google's distributed systems "
         "tracing infrastructure, establishing the span-based tracing model in which "
         "every RPC is annotated with a traceID and parentSpanID. Jaeger, the "
         "open-source implementation adopted here, implements this model, enabling "
         "programmatic SDG extraction from raw trace JSON.")
    body(doc,
         "Basiri et al. (2016) formalised Chaos Engineering through Netflix's Chaos "
         "Monkey programme, advocating for deliberate, controlled fault injection to "
         "uncover resilience weaknesses proactively. Their principle of injecting "
         "production-representative failures into isolated test environments is the "
         "philosophical foundation of this project's fault injection methodology.")
    body(doc,
         "Beyer et al. (2016) articulated site reliability engineering practices at "
         "Google, including error budget management and Service Level Objective (SLO) "
         "frameworks. Their treatment of blast radius as a key concern in capacity "
         "planning directly motivates our quantitative blast-radius measurement "
         "methodology across five independent dimensions.")
    body(doc,
         "Nedelkoski et al. (2019) investigated automated fault localisation in "
         "microservice architectures using service dependency metric correlation. "
         "While demonstrating the relevance of inter-service relationships for "
         "root-cause identification, their reactive approach required post-failure "
         "data. This project extends their work to the proactive domain.")
    body(doc,
         "Ma et al. (2020) applied PageRank-inspired walk algorithms to service "
         "dependency graphs for anomaly detection, observing that high-pagerank "
         "services tended to exhibit elevated error propagation. This empirical "
         "observation provides additional prior motivation for including PageRank "
         "as a centrality predictor in the present study.")
    body(doc,
         "Meng et al. (2020) proposed localisation of microservice failures using "
         "graph-based analysis of call traces, showing that combining trace-derived "
         "graph structure with statistical anomaly scores improves root-cause precision. "
         "Their graph-plus-metrics fusion approach inspired the correlation framework "
         "used here to connect structural scores with empirical blast radius measurements.")
    body(doc,
         "Chaos engineering platforms such as Gremlin (Reinhardt and Robbins, 2021) "
         "and LitmusChaos (CNCF, 2022) have industrialised fault injection into "
         "Kubernetes-based microservice clusters, offering rich fault-type catalogues "
         "including CPU stress, memory pressure, pod eviction, and network partition. "
         "This work contributes to this ecosystem by providing a principled, "
         "graph-theoretic method for prioritising which services to target with "
         "such tools.")

    sub_hdr(doc, "2.2 Research Gap")
    body(doc,
         "Although graph centrality theory is mathematically mature and distributed "
         "tracing infrastructure is now ubiquitous in production microservice deployments, "
         "a critical research gap exists at their intersection. No prior work has "
         "systematically and empirically validated whether static structural centrality "
         "metrics derived from runtime trace-based SDGs can predict the real-world "
         "blast radius of chaos fault-injection events across multiple independent "
         "failure dimensions.")
    body(doc,
         "Existing fault localisation literature focuses primarily on reactive root cause "
         "analysis, identifying the source of a failure after it has occurred. The "
         "orthogonal proactive dimension, whether graph analysis can rank services by "
         "failure risk before any incidents occur, remains underexplored. Furthermore, "
         "prior art typically employs either static architecture diagrams or single-metric "
         "evaluations testing only one centrality measure against one failure indicator.")
    body(doc,
         "This project addresses the gap by contributing: (1) an automated pipeline "
         "for dynamic SDG construction from live traces; (2) a seven-metric comparative "
         "centrality study evaluated across five blast radius dimensions; and (3) a "
         "systematic outlier analysis exposing the limits of structural metrics for "
         "services with high out-degree fan-out but low in-degree, such as synchronous "
         "write orchestrators like compose-post-service.")

    sub_hdr(doc, "2.3 Objectives")
    body(doc,
         "The following SMART (Specific, Measurable, Achievable, Relevant, "
         "Time-Bound) objectives define the scope of this project:")

    blt(doc, [("SDG Extraction: ", True),
              ("To dynamically construct a directed, weighted Service Dependency Graph "
               "from live Jaeger distributed traces of the DeathStarBench Social Network "
               "application, capturing all inter-service RPC dependencies and associated "
               "latency metadata.", False)])
    blt(doc, [("Centrality Computation: ", True),
              ("To compute seven normalised graph centrality metrics - Degree, In-Degree, "
               "Out-Degree, Betweenness, Closeness, Eigenvector, and PageRank - for each "
               "of the 12 microservice nodes using the NetworkX Python library.", False)])
    blt(doc, [("Composite Ranking: ", True),
              ("To derive a composite centrality score as the mean of normalised "
               "per-metric ranks, providing an aggregate structural importance ranking "
               "across all seven dimensions.", False)])
    blt(doc, [("Chaos Fault Injection: ", True),
              ("To inject container kill (SIGKILL) and 100 ms network-latency (tc netem) "
               "faults via Pumba into each of the 12 microservices, with two experimental "
               "repetitions per (service, fault-type) combination, yielding 48 controlled "
               "experiment runs.", False)])
    blt(doc, [("Blast Radius Measurement: ", True),
              ("To quantify fault impact across five dimensions: p95 latency delta, "
               "p99 latency delta, error rate delta, downstream services affected count, "
               "and recovery time, collected from Jaeger traces during active fault windows.",
               False)])
    blt(doc, [("Statistical Correlation: ", True),
              ("To compute Spearman rank correlation coefficient (rho) and p-values "
               "between all centrality-blast radius pairs, identifying structural "
               "properties that most reliably predict failure impact at p < 0.05.", False)])
    blt(doc, [("Outlier Analysis: ", True),
              ("To identify and qualitatively explain services where centrality rank "
               "and empirical blast-radius rank diverge by more than N/3 positions, "
               "exposing the limits of static graph-theoretic risk prediction.", False)])
    blt(doc, [("Visualisation: ", True),
              ("To produce Spearman correlation heatmaps, scatter plots for each "
               "centrality-blast radius pair, and composite score bar charts for "
               "communication of findings to SRE practitioners.", False)])

    sub_hdr(doc, "2.4 Problem Statement")
    body(doc,
         "In modern cloud-native architectures, the failure of a single microservice "
         "can cascade through dependency chains and produce system-wide outages. Site "
         "Reliability Engineers currently lack a principled, data-driven methodology "
         "to proactively identify which microservices pose the greatest systemic risk, "
         "forcing reliance on subjective expertise or post-incident analysis.")
    body(doc,
         "This project addresses the following research problem: Can graph-theoretic "
         "centrality metrics, derived from dynamically extracted runtime Service "
         "Dependency Graphs, serve as statistically significant and practically useful "
         "predictors of the blast radius caused by fault injection in a representative "
         "microservice architecture?")
    body(doc,
         "The problem encompasses three sub-challenges: (1) dynamic, automated "
         "construction of accurate SDGs from distributed trace data; (2) empirical "
         "blast-radius quantification across multiple orthogonal dimensions via controlled "
         "chaos experiments; and (3) rigorous statistical validation of the structural-to-"
         "operational centrality correspondence hypothesis. Solving this enables a shift "
         "from reactive incident response to proactive, evidence-based resilience "
         "engineering.")

    sub_hdr(doc, "2.5 Project Plan")
    body(doc,
         "The project is executed over an eight-month timeline, organised into eight "
         "sequential phases aligned with the six-stage experimental pipeline. Each "
         "phase produces a concrete deliverable that feeds directly into the subsequent "
         "stage. The Gantt chart below illustrates task durations, sequencing, and "
         "overlapping phases across the project timeline.")

    # Gantt chart table
    months = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"]
    tasks = [
        ("Task 1", "Literature Survey",               [1,1,0,0,0,0,0,0]),
        ("Task 2", "Environment Setup & Deployment",  [1,1,1,0,0,0,0,0]),
        ("Task 3", "SDG Extraction Pipeline",         [0,1,1,1,0,0,0,0]),
        ("Task 4", "Centrality Computation Module",   [0,0,1,1,0,0,0,0]),
        ("Task 5", "Fault Injection & Measurement",   [0,0,0,1,1,1,0,0]),
        ("Task 6", "Statistical Analysis & Plots",    [0,0,0,0,1,1,0,0]),
        ("Task 7", "Testing & Validation",            [0,0,0,0,0,1,1,0]),
        ("Task 8", "Documentation & Report Writing",  [0,0,0,0,0,0,1,1]),
    ]
    header = ["Task", "Activity"] + months
    n_rows = 1 + len(tasks)
    n_cols = 2 + len(months)

    gtbl = doc.add_table(rows=n_rows, cols=n_cols)
    gtbl.alignment = WD_TABLE_ALIGNMENT.CENTER

    for ci, txt in enumerate(header):
        c = gtbl.rows[0].cells[ci]
        p = c.paragraphs[0]; p.clear()
        r = p.add_run(txt); fmt_run(r, size=9, bold=True)
        fmt_para(p, align=WD_ALIGN_PARAGRAPH.CENTER,
                 line_spacing=1.0, before_pt=1, after_pt=1)
        set_cell_bg(c, "D9D9D9"); set_cell_borders(c)

    for ri, (tnum, tname, sched) in enumerate(tasks):
        row = gtbl.rows[ri + 1]
        bg = "EEF2FA" if ri % 2 == 0 else "FFFFFF"
        for ci, txt in enumerate([tnum, tname]):
            c = row.cells[ci]; p = c.paragraphs[0]; p.clear()
            r = p.add_run(txt); fmt_run(r, size=9)
            align = (WD_ALIGN_PARAGRAPH.CENTER if ci == 0
                     else WD_ALIGN_PARAGRAPH.LEFT)
            fmt_para(p, align=align, line_spacing=1.0, before_pt=1, after_pt=1)
            set_cell_bg(c, bg); set_cell_borders(c)
        for ci, active in enumerate(sched):
            c = row.cells[ci + 2]; p = c.paragraphs[0]; p.clear()
            p.add_run("")
            fmt_para(p, align=WD_ALIGN_PARAGRAPH.CENTER,
                     line_spacing=1.0, before_pt=1, after_pt=1)
            set_cell_bg(c, "4472C4" if active else bg)
            set_cell_borders(c)

    for row in gtbl.rows:
        row.cells[0].width = Inches(0.55)
        row.cells[1].width = Inches(2.20)
        for ci in range(2, n_cols):
            row.cells[ci].width = Inches(0.53)

    fig_caption(doc, "Fig. 1. Project Gantt Chart - Eight-Month Experiment Timeline")
    doc.add_page_break()


# ===========================================================================
# SECTION 3 - TECHNICAL SPECIFICATION
# ===========================================================================

def build_section3(doc):
    sec_hdr(doc, "3. TECHNICAL SPECIFICATION")

    sub_hdr(doc, "3.1 Requirements")

    subsub_hdr(doc, "3.1.1   Functional")
    func = [
        [("Trace Collection: ", True),
         ("The system shall query the Jaeger REST API (/api/traces) to collect "
          "distributed trace data within a configurable lookback window and "
          "trace-count limit, exporting raw spans as structured JSON.", False)],
        [("SDG Construction: ", True),
         ("The system shall parse Jaeger trace JSON to resolve parentSpanID to "
          "spanID relationships and map processID to service name, constructing a "
          "directed weighted NetworkX DiGraph annotated with call count and average "
          "latency.", False)],
        [("Graph Export: ", True),
         ("The system shall export the SDG to GraphML format for Gephi and JSON "
          "node-link format for downstream programmatic analysis.", False)],
        [("Centrality Computation: ", True),
         ("The system shall compute seven normalised centrality metrics per node: "
          "Degree, In-Degree, Out-Degree, Betweenness, Closeness, Eigenvector, "
          "and PageRank (damping = 0.85) using NetworkX.", False)],
        [("Composite Scoring: ", True),
         ("The system shall compute a composite centrality score as the mean of "
          "normalised per-metric ranks and produce a final composite rank for each "
          "service.", False)],
        [("Fault Injection: ", True),
         ("The system shall orchestrate chaos cycles using Pumba, supporting "
          "Container Kill (SIGKILL) and Network Latency (tc netem) fault types "
          "with configurable duration, jitter, and repetition count.", False)],
        [("Blast Radius Measurement: ", True),
         ("During each fault window the system shall query Jaeger to compute p95 "
          "and p99 tail latency deltas, error rate deltas, downstream affected "
          "service count, and container recovery time in seconds.", False)],
        [("Statistical Correlation: ", True),
         ("The system shall compute Spearman rank correlation and p-values for all "
          "40 centrality-blast radius metric pairs using scipy.stats.spearmanr.", False)],
        [("Visualisation: ", True),
         ("The system shall produce correlation heatmaps, per-pair scatter plots, "
          "and composite score bar charts using Matplotlib and Seaborn.", False)],
        [("Outlier Detection: ", True),
         ("The system shall identify False Positives and False Negatives based on "
          "absolute rank discrepancy between centrality rank and blast-radius rank "
          "exceeding a configurable fraction threshold (default N/3).", False)],
        [("Integration Testing: ", True),
         ("After each fault recovery cycle the system shall execute pytest "
          "integration tests verifying core user flows to confirm functional "
          "system correctness.", False)],
        [("Experiment Logging: ", True),
         ("The system shall append all run records to a persistent CSV log file "
          "for full reproducibility and audit traceability.", False)],
    ]
    for f in func:
        blt(doc, f)

    subsub_hdr(doc, "3.1.2   Non-Functional")
    nfr = [
        [("Performance: ", True),
         ("Trace collection and SDG construction shall complete within 5 minutes "
          "for a 2-hour lookback with 2,000 traces. Centrality computation shall "
          "complete within 30 seconds for graphs of up to 100 nodes.", False)],
        [("Scalability: ", True),
         ("The pipeline shall support applications with up to 100 microservice "
          "nodes without architectural modification.", False)],
        [("Reliability: ", True),
         ("The fault injection module shall guarantee container restart and service "
          "recovery verification before initiating the next experiment run.", False)],
        [("Reproducibility: ", True),
         ("All stochastic components shall use a fixed random seed (seed = 42). "
          "Experiment parameters and Pumba command arguments shall be fully logged.", False)],
        [("Portability: ", True),
         ("The system shall operate on Windows 11 (WSL2), macOS 13+, and Ubuntu "
          "22.04 LTS on any platform supporting Docker Desktop 4.0+ and Python 3.11+.",
          False)],
        [("Maintainability: ", True),
         ("The codebase shall be organised into single-responsibility modules with "
          "docstrings, type annotations, and pytest coverage.", False)],
        [("Security: ", True),
         ("Fault injection shall operate only within the isolated Docker bridge "
          "network. No production systems shall be targeted.", False)],
        [("Usability: ", True),
         ("All phases shall be executable via a single orchestrator script "
          "(run_full_experiment.py) with a --dry-run mode for plan inspection.",
          False)],
    ]
    for n in nfr:
        blt(doc, n)

    sub_hdr(doc, "3.2 Feasibility Study")

    subsub_hdr(doc, "3.2.1   Technical Feasibility")
    blt(doc, [("Technology Availability: ", True),
              ("All core components - Docker, Python 3.11, Jaeger, NetworkX, SciPy, "
               "and Pumba - are mature, open-source, and actively maintained with "
               "extensive community documentation.", False)])
    blt(doc, [("Algorithm Availability: ", True),
              ("All seven centrality metrics are single-call functions in NetworkX. "
               "Spearman correlation is provided by scipy.stats. No novel algorithm "
               "development is required.", False)])
    blt(doc, [("Benchmark Availability: ", True),
              ("DeathStarBench is a peer-reviewed, publicly available benchmark "
               "deployable via Docker Compose on commodity hardware.", False)])
    blt(doc, [("Hardware Accessibility: ", True),
              ("The full experiment stack runs on a single workstation with 16 GB RAM "
               "and 8 CPU cores - standard equipment in any university CS laboratory.",
               False)])
    blt(doc, [("Integration Feasibility: ", True),
              ("All components communicate through standard interfaces: HTTP REST "
               "(Jaeger API), Docker SDK for Python (container management), and Linux "
               "network namespaces (Pumba tc netem injection).", False)])

    subsub_hdr(doc, "3.2.2   Economic Feasibility")
    blt(doc, [("Zero Licensing Cost: ", True),
              ("All software components are open-source under permissive licences "
               "(Apache 2.0, MIT, BSD). No commercial licensing fees are incurred.",
               False)])
    blt(doc, [("Infrastructure Cost: ", True),
              ("Experiments run entirely on existing hardware. Optional cloud "
               "deployment on an AWS EC2 spot instance costs under Rs. 500 for a "
               "complete experiment run.", False)])
    blt(doc, [("Return on Investment: ", True),
              ("A single prevented enterprise production outage costs an average of "
               "$300,000/hour (Gartner, 2022), providing overwhelming ROI for targeted "
               "resilience investment guided by this methodology.", False)])
    blt(doc, [("Maintenance Cost: ", True),
              ("The open-source toolchain requires no licence renewals. Quarterly "
               "dependency updates require less than one engineering day.", False)])

    subsub_hdr(doc, "3.2.3   Social Feasibility")
    blt(doc, [("Industry Relevance: ", True),
              ("The methodology directly addresses a pain point experienced by SRE "
               "teams. The output - a ranked risk table - is immediately actionable "
               "without graph theory expertise.", False)])
    blt(doc, [("User Acceptance: ", True),
              ("SREs are already familiar with distributed tracing tools and container "
               "orchestration. The system builds on existing tooling, minimising "
               "adoption friction.", False)])
    blt(doc, [("Ethical Considerations: ", True),
              ("All fault injection experiments run in an isolated Docker environment "
               "using a benchmark application. No real user data or production systems "
               "are involved.", False)])
    blt(doc, [("Impact on Workforce: ", True),
              ("Automated risk ranking augments SRE capabilities rather than replacing "
               "human judgement, freeing engineers from manual dependency audits.",
               False)])
    blt(doc, [("Knowledge Dissemination: ", True),
              ("Findings are documented in this project report. The full experimental "
               "pipeline is made publicly available for academic replication.", False)])

    sub_hdr(doc, "3.3 System Specification")

    subsub_hdr(doc, "3.3.1   Hardware Specification")
    body(doc,
         "The following hardware is required to deploy the complete DeathStarBench "
         "microservice stack alongside the fault injection orchestrator and analysis "
         "pipeline:")

    hw_rows = [
        ["Component",    "Minimum Specification",                     "Recommended Specification"],
        ["Processor",    "Intel Core i5 / AMD Ryzen 5\n(4 cores, 2.0 GHz)", "Intel Core i7 / AMD Ryzen 7\n(8 cores, 3.0 GHz)"],
        ["Memory (RAM)", "8 GB DDR4",                                 "16 - 32 GB DDR4"],
        ["Storage",      "30 GB free SSD / HDD",                      "50 GB free NVMe SSD"],
        ["GPU",          "Not required",                              "Not required (CPU-only)"],
        ["Network",      "Local Docker bridge",                       "Gigabit LAN"],
        ["Monitor",      "1920 x 1080 (Full HD)",                     "Full HD or higher"],
    ]
    htbl = doc.add_table(rows=len(hw_rows), cols=3)
    htbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cw = [Inches(1.2), Inches(2.5), Inches(2.6)]
    for ri, row_d in enumerate(hw_rows):
        row = htbl.rows[ri]
        for ci, txt in enumerate(row_d):
            c = row.cells[ci]; c.width = cw[ci]
            p = c.paragraphs[0]; p.clear()
            r = p.add_run(txt); fmt_run(r, size=10, bold=(ri == 0))
            fmt_para(p, align=WD_ALIGN_PARAGRAPH.LEFT,
                     line_spacing=1.0, before_pt=2, after_pt=2)
            bg = ("D9D9D9" if ri == 0 else
                  "F5F5F5" if ri % 2 == 0 else "FFFFFF")
            set_cell_bg(c, bg); set_cell_borders(c)
    fig_caption(doc, "Table 1. Hardware Specification")

    subsub_hdr(doc, "3.3.2   Software Specification")
    body(doc,
         "All software components used in this project are open-source and "
         "cross-platform compatible. The complete software ecosystem required to "
         "execute the six-phase experiment pipeline is listed in Table 2:")

    sw_rows = [
        ["Category",             "Tool / Version",                       "Purpose"],
        ["Operating System",     "Windows 11 + WSL2 / Ubuntu 22.04 / macOS 13+", "Host environment for Docker and Python"],
        ["Programming Language", "Python 3.11+",                         "All pipeline scripts and orchestration"],
        ["Development Env.",     "VS Code / PyCharm",                    "Code editing, debugging, project management"],
        ["Graph Library",        "NetworkX 3.1",                         "SDG construction and 7 centrality metrics"],
        ["Data Analysis",        "Pandas 2.0, NumPy 1.24, SciPy 1.11", "Aggregation, ranking, Spearman correlation"],
        ["Visualisation",        "Matplotlib 3.7, Seaborn 0.12",        "Heatmaps, scatter plots, bar charts"],
        ["Container Platform",   "Docker Desktop 4.0+ (WSL2 backend)",   "Multi-container microservice deployment"],
        ["Distributed Tracing",  "Jaeger All-in-One v1.62.0",           "Trace collection, span storage, REST API"],
        ["Load Generation",      "Locust 2.15 / wrk2 (Docker)",         "Synthetic HTTP traffic at 50 req/s"],
        ["Chaos Engineering",    "Pumba (alexei-led/pumba)",             "Container SIGKILL and tc netem latency"],
        ["HTTP Client",          "Requests 2.31",                        "Jaeger API and DeathStarBench API calls"],
        ["Testing Framework",    "pytest 7.4",                           "Post-fault recovery integration tests"],
        ["Build System",         "setuptools 68.0, pip",                 "Package management and dependency install"],
    ]
    stbl = doc.add_table(rows=len(sw_rows), cols=3)
    stbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    scw = [Inches(1.4), Inches(2.2), Inches(2.7)]
    for ri, row_d in enumerate(sw_rows):
        row = stbl.rows[ri]
        for ci, txt in enumerate(row_d):
            c = row.cells[ci]; c.width = scw[ci]
            p = c.paragraphs[0]; p.clear()
            r = p.add_run(txt); fmt_run(r, size=9, bold=(ri == 0))
            fmt_para(p, align=WD_ALIGN_PARAGRAPH.LEFT,
                     line_spacing=1.0, before_pt=2, after_pt=2)
            bg = ("D9D9D9" if ri == 0 else
                  "F5F5F5" if ri % 2 == 0 else "FFFFFF")
            set_cell_bg(c, bg); set_cell_borders(c)
    fig_caption(doc, "Table 2. Software Specification")
    doc.add_page_break()


# ===========================================================================
# SECTION 4 - DESIGN APPROACH AND DETAILS
# ===========================================================================

def build_section4(doc):
    sec_hdr(doc, "4. DESIGN APPROACH AND DETAILS")

    sub_hdr(doc, "4.1 System Architecture")
    body(doc,
         "The system is structured as a six-phase sequential pipeline in which each "
         "phase produces a concrete artefact consumed by the next. The pipeline begins "
         "with environment deployment, proceeds through data collection and graph "
         "construction, executes chaos experiments, and concludes with statistical "
         "analysis and visualisation. The master orchestrator script "
         "run_full_experiment.py chains all phases via subprocess calls, supporting "
         "selective phase skipping via CLI flags.")
    body(doc,
         "Phase 1 (Infrastructure) deploys the DeathStarBench Social Network application "
         "via Docker Compose, initialises a synthetic social graph, and generates "
         "baseline traffic at 50 req/s. Phase 2 (SDG Construction) queries the Jaeger "
         "REST API to fetch raw traces, then parses span parent-child relationships "
         "to build the directed Service Dependency Graph exported as sdg.json and "
         "sdg.graphml.")
    body(doc,
         "Phase 3 (Centrality) runs compute_centrality.py to calculate all seven metrics "
         "via NetworkX, producing centrality_table.csv. Phase 4 (Fault Injection) "
         "iterates over all 12 services, executing warm-up, baseline measurement, fault "
         "injection via Pumba, fault-window measurement, container restart, and cooldown "
         "for each (service, fault-type, repetition) triple. Phase 5 (Verification) "
         "executes pytest integration tests. Phase 6 (Analysis) runs Spearman "
         "correlation, outlier detection, and plot generation scripts.")

    placeholder_box(doc,
        "[ INSERT SYSTEM ARCHITECTURE DIAGRAM HERE ]\n"
        "Recommended: Six-phase flowchart\n"
        "Phase 1 (Docker Deploy) -> Phase 2 (Jaeger Traces -> SDG) -> "
        "Phase 3 (Centrality) -> Phase 4 (Pumba Fault Injection) -> "
        "Phase 5 (pytest) -> Phase 6 (Spearman Analysis -> Plots)")
    fig_caption(doc, "Fig. 2. System Architecture - Six-Phase Experiment Pipeline")

    sub_hdr(doc, "4.2 Design")

    subsub_hdr(doc, "4.2.1   Data Flow Diagram")
    body(doc,
         "The Data Flow Diagram (DFD) at Level 0 (Context Diagram) shows the system "
         "as a single process receiving inputs from two external entities: the Jaeger "
         "Tracing Server (providing span data) and the Docker Daemon (providing container "
         "state). The system produces outputs to three sinks: the Experiment Log CSV, "
         "the Analysis Plots directory, and the Centrality Table.")
    body(doc,
         "At Level 1, the DFD decomposes into six major processes: (1) Trace Ingestion - "
         "queries Jaeger, normalises span JSON; (2) Graph Builder - extracts parent-child "
         "service edges, constructs NetworkX DiGraph; (3) Centrality Engine - computes "
         "seven metrics, writes centrality_table.csv; (4) Fault Orchestrator - dispatches "
         "Pumba commands, manages timing; (5) Blast Radius Collector - queries Jaeger "
         "during fault windows, appends to experiment_log.csv; (6) Statistical Analyser - "
         "runs Spearman correlation, generates plots, identifies outliers.")

    placeholder_box(doc,
        "[ INSERT DATA FLOW DIAGRAM HERE ]\n"
        "Level 0: External Entities (Jaeger Server, Docker Daemon) -> System -> "
        "Outputs (CSV logs, Plots)\n"
        "Level 1: Six process bubbles with data stores "
        "(raw_traces.json, sdg.json, centrality_table.csv, experiment_log.csv)")
    fig_caption(doc, "Fig. 3. Data Flow Diagram (Level 1)")

    subsub_hdr(doc, "4.2.2   Use Case Diagram")
    body(doc,
         "The Use Case Diagram identifies two primary actors: the Research Engineer "
         "(who configures and triggers the experiment pipeline) and the SRE Analyst "
         "(who consumes the results). The Research Engineer interacts with use cases "
         "including: Configure Experiment Parameters, Deploy DeathStarBench Stack, "
         "Execute Fault Injection Pipeline, and Review Correlation Results. The SRE "
         "Analyst interacts with: View Centrality Rankings, Inspect Blast Radius "
         "Measurements, Analyse Correlation Heatmap, and Identify High-Risk Services.")
    body(doc,
         "Secondary include relationships connect Execute Fault Injection Pipeline "
         "to Inject Container Kill Fault, Inject Network Latency Fault, Collect "
         "Jaeger Metrics, and Run Integration Tests. The Jaeger Server is modelled "
         "as an external system actor providing trace data to the pipeline.")

    placeholder_box(doc,
        "[ INSERT USE CASE DIAGRAM HERE ]\n"
        "Actors: Research Engineer, SRE Analyst, Jaeger Server (external)\n"
        "Use Cases: Configure Experiment, Deploy Stack, Execute Fault Injection, "
        "View Centrality Rankings, Analyse Correlations, Identify High-Risk Services")
    fig_caption(doc, "Fig. 4. Use Case Diagram")

    subsub_hdr(doc, "4.2.3   Class Diagram")
    body(doc,
         "The class diagram models the core Python modules as classes with attributes "
         "and methods. Key classes include: TraceCollector (attributes: jaeger_url, "
         "lookback, limit; methods: fetch_traces(), save_raw_json()); GraphBuilder "
         "(attributes: traces_path, output_dir; methods: extract_edges(), build_graph(), "
         "export_graphml(), export_json()); CentralityComputer (attributes: graph, "
         "output_dir; methods: compute_all(), add_ranks(), add_composite(), save_csv()); "
         "FaultSpec (attributes: fault_type, duration_seconds, latency_ms; methods: "
         "pumba_command()); ExperimentConfig (attributes: services, fault_types, "
         "repetitions; methods: total_runs(), estimated_time()); MetricsCollector "
         "(attributes: jaeger_url; methods: get_traces_in_window(), "
         "compute_latency_percentiles(), compute_error_rate()); CorrelationAnalyser "
         "(attributes: centrality_df, blast_df; methods: aggregate_by_service(), "
         "compute_spearman()); OutlierDetector (attributes: merged_df, threshold; "
         "methods: identify(), classify(), save()).")

    placeholder_box(doc,
        "[ INSERT CLASS DIAGRAM HERE ]\n"
        "Key Classes: TraceCollector, GraphBuilder, CentralityComputer, FaultSpec, "
        "ExperimentConfig, MetricsCollector, ResultsLogger, CorrelationAnalyser, "
        "OutlierDetector, PlotGenerator\n"
        "Show attributes, methods, and associations/dependencies between classes.")
    fig_caption(doc, "Fig. 5. Class Diagram")

    subsub_hdr(doc, "4.2.4   Sequence Diagram")
    body(doc,
         "The sequence diagram illustrates the message-passing interactions during "
         "a single fault injection experiment run. Participants include: FaultRunner, "
         "LoadGenerator, TargetContainer, Pumba, JaegerServer, MetricsCollector, and "
         "ResultsLogger. The sequence begins with FaultRunner instructing LoadGenerator "
         "to start warm-up traffic for 30 seconds. After warm-up, FaultRunner records "
         "the baseline window start timestamp and queries JaegerServer for baseline "
         "traces. FaultRunner then invokes Pumba to inject the fault into TargetContainer "
         "and continues traffic for 60 seconds. MetricsCollector queries JaegerServer "
         "for fault-window traces and computes all blast radius metrics. FaultRunner "
         "instructs Pumba to remove the fault and waits for TargetContainer to recover. "
         "ResultsLogger appends the run record to experiment_log.csv.")

    placeholder_box(doc,
        "[ INSERT SEQUENCE DIAGRAM HERE ]\n"
        "Participants: FaultRunner, LoadGenerator, TargetContainer, Pumba, "
        "JaegerServer, MetricsCollector, ResultsLogger\n"
        "Key interactions: Warm-up (30s) -> Baseline Measurement -> Inject Fault "
        "-> Fault Window (60s) -> Collect Metrics -> Remove Fault -> Recovery -> Log Results")
    fig_caption(doc, "Fig. 6. Sequence Diagram - Single Fault Injection Run")
    doc.add_page_break()


# ===========================================================================
# SECTION 5 - REFERENCES
# ===========================================================================

def build_section5(doc):
    sec_hdr(doc, "5. REFERENCES")

    def ref_cat(label):
        p = doc.add_paragraph()
        r = p.add_run(label)
        fmt_run(r, size=12, bold=True)
        fmt_para(p, align=WD_ALIGN_PARAGRAPH.LEFT,
                 line_spacing=1.15, before_pt=8, after_pt=4,
                 first_indent_in=0)

    def ref(num, parts):
        p = doc.add_paragraph()
        rn = p.add_run(str(num) + ".  ")
        fmt_run(rn, size=12)
        for txt, ital in parts:
            r = p.add_run(txt)
            fmt_run(r, size=12, italic=ital)
        fmt_para(p, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=1.15,
                 left_indent_in=0.35, first_indent_in=-0.35,
                 before_pt=0, after_pt=4)

    ref_cat("Web links:")
    ref(1, [("https://github.com/delimitrou/DeathStarBench - DeathStarBench benchmark "
             "suite source code repository. Accessed August 2026.", False)])
    ref(2, [("https://www.jaegertracing.io/docs - Jaeger Distributed Tracing official "
             "documentation. Accessed August 2026.", False)])
    ref(3, [("https://github.com/alexei-led/pumba - Pumba chaos testing and network "
             "emulation tool repository. Accessed August 2026.", False)])
    ref(4, [("https://networkx.org/documentation/stable - NetworkX graph library "
             "documentation. Accessed August 2026.", False)])
    ref(5, [("https://landing.google.com/sre/sre-book - Google Site Reliability "
             "Engineering Book, online edition. Accessed August 2026.", False)])

    ref_cat("Journals: <IEEE Format>")
    ref(1, [('A. L. Barabasi and R. Albert, "Emergence of scaling in random networks," ',
             False), ("Science,", True),
            (" vol. 286, no. 5439, pp. 509-512, Oct. 1999.", False)])

    ref(2, [('M. E. J. Newman, "The structure and function of complex networks," ',
             False), ("SIAM Review,", True),
            (" vol. 45, no. 2, pp. 167-256, 2003.", False)])

    ref(3, [('Y. Gan et al., "An open-source benchmark suite for microservices and '
             'their hardware-software implications for cloud and edge systems," in ',
             False), ("Proc. ASPLOS,", True), (" Apr. 2019, pp. 3-18.", False)])

    ref(4, [('B. H. Sigelman et al., "Dapper, a large-scale distributed systems '
             'tracing infrastructure," Google Technical Report, 2010.', False)])

    ref(5, [('S. Nedelkoski, J. Cardoso, and O. Kao, "Anomaly detection and '
             'classification using distributed tracing and deep learning for '
             'microservices," in ', False),
            ("Proc. IEEE/ACM CCGRID,", True), (" 2019, pp. 241-250.", False)])

    ref(6, [('X. Ma et al., "Diagnosing root causes of intermittent slow queries '
             'in cloud databases," ', False),
            ("Proc. VLDB Endowment,", True),
            (" vol. 13, no. 8, pp. 1176-1189, 2020.", False)])

    ref(7, [('H. Chen et al., "Outage prediction and diagnosis for cloud service '
             'systems," in ', False),
            ("Proc. WWW,", True), (" 2019, pp. 2659-2665.", False)])

    ref(8, [('S. Meng et al., "Localisation of operational faults in cloud applications '
             'by mining causal dependencies in logs through graph convolutional '
             'network," in ', False),
            ("Proc. ICSOC,", True), (" 2020.", False)])

    ref_cat("Conference: <IEEE Format>")
    ref(1, [('A. Basiri et al., "Chaos engineering," ', False),
            ("IEEE Software,", True),
            (" vol. 33, no. 3, pp. 35-41, May 2016.", False)])

    ref(2, [('P. Leitner and J. Cito, "Patterns in the chaos - a study of performance '
             'variation and predictability in public IaaS clouds," ', False),
            ("ACM TOIT,", True), (" vol. 16, no. 3, Apr. 2016.", False)])

    ref(3, [('Y. Xu et al., "POD-failure tolerance for Internet services," in ',
             False), ("Proc. USENIX ATC,", True), (" 2018.", False)])

    ref_cat("Books:")
    ref(1, [("M. E. J. Newman, ", False),
            ("Networks: An Introduction.", True),
            (" Oxford University Press, 2010.", False)])

    ref(2, [("B. Beyer, C. Jones, J. Petoff, and N. R. Murphy, Eds., ", False),
            ("Site Reliability Engineering: How Google Runs Production Systems.", True),
            (" O'Reilly Media, 2016.", False)])

    ref(3, [("S. Newman, ", False),
            ("Building Microservices: Designing Fine-Grained Systems,", True),
            (" 2nd ed. O'Reilly Media, 2021.", False)])

    ref(4, [('L. Page, S. Brin, R. Motwani, and T. Winograd, "The PageRank citation '
             'ranking: Bringing order to the web," Stanford InfoLab Tech. Report, 1999.',
             False)])


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    doc = Document()
    set_page_a4(doc)
    # Remove the default empty paragraph Word always adds
    for p in list(doc.paragraphs):
        p._element.getparent().remove(p._element)

    build_cover(doc)
    build_abstract(doc)
    build_toc(doc)
    build_section1(doc)
    build_section2(doc)
    build_section3(doc)
    build_section4(doc)
    build_section5(doc)
    add_page_number_footer(doc)

    doc.save(str(OUTPUT))
    size_kb = OUTPUT.stat().st_size / 1024
    print("\n[OK] Word document generated successfully!")
    print("     File : " + str(OUTPUT))
    print("     Size : " + str(round(size_kb, 1)) + " KB")
    print("")
    print("[NOTE] Open in Microsoft Word and:")
    print("  1. Replace all [PLACEHOLDER] text with your actual details")
    print("  2. Insert diagrams in the blue-bordered placeholder boxes")
    print("  3. Right-click TOC -> Update Field -> Update Page Numbers")


if __name__ == "__main__":
    main()
