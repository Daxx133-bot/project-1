"""
build_report.py -- build the BCSE497J project report (Word) from report/text/report.md.

Inputs
  report/text/report.md        the report prose (written for the report, not copied from
                               the paper); markup described below
  report/meta.json             title page particulars
  paper/numbers.json           every number; written {{claim_id}} or {{claim_id|word}}
  paper/references.csv         VERIFIED rows only; cited as [@key] or [@a; @b], numbered
                               in order of first citation (IEEE style)
  paper/tables/*.csv           tables, written ::table name | caption [| row filter]
  paper/figures/, report/figures/   figures, written ::figure path | caption
  report/out/pytest_offline.txt     test summary, read into {{pytest_passed}} and
                                    {{pytest_deselected}}

Markup: "# " chapter, "## " section, "### " subsection, "- " bullet, [[name]] cross-reference
to a figure or table (renders "Fig. N" / "Table N"), ::pagebreak, *italic*, **bold**,
<sub>..</sub>.

The build fails if a digit in the prose did not come from a {{token}}, a citation, a
cross-reference or a whitelisted label (H1, H2, p95, p99, Deviation N, Level 0/1, WSL2,
section numbers in headings), if a citation key is not VERIFIED, or if a template word
limit is exceeded (abstract 300; Background, Motivation, Scope 200 each).

Output: report/out/Project_Report.docx. Then run report/finalize_word.ps1 to update the
table of contents and page numbers in Word and export a PDF.

Run: python report/build_report.py
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "paper"))
from build_docx import add_runs, author_label, load_refs  # noqa: E402

FONT = "Times New Roman"
OUT = os.path.join(HERE, "out", "Project_Report.docx")
LIMITS = {"ABSTRACT": (300, 500)}
WORDS = "zero one two three four five six seven eight nine ten eleven twelve".split()

TOKEN = re.compile(r"\{\{([a-z0-9_]+)(\|word)?\}\}")
CITE = re.compile(r"\[(@[^\]\[]+)\]")
XREF = re.compile(r"\[\[([A-Za-z0-9_]+)\]\]")
ALLOWED = re.compile(r"\bH1b?\b|\bH2\b|\bp9[59]\b|\bp99\b|Deviations? \d+(?:, \d+)*(?: and \d+)?"
                     r"|\bLevel [01]\b|\bWSL2\b|\bBCSE497J\b|\bD[1-6]\b|\b[1-6]\.0\b"
                     r"|\bIEEE\b|\bReview[- ]2\b|\bChapter \d\b|\bSection \d+(?:\.\d+)*")


def load_values():
    with open(os.path.join(REPO, "paper", "numbers.json"), encoding="utf-8") as fh:
        vals = dict(json.load(fh)["values"])
    with open(os.path.join(HERE, "out", "pytest_offline.txt"), encoding="utf-8") as fh:
        summary = fh.read()
    m = re.search(r"(\d+) passed(?:, (\d+) failed)?, (\d+) deselected", summary)
    if not m:
        sys.exit("report/out/pytest_offline.txt has no pytest summary line")
    vals["pytest_passed"] = m.group(1)
    vals["pytest_failed"] = m.group(2) or "0"
    vals["pytest_deselected"] = m.group(3)
    return vals


def table_label(block):
    if block.startswith("::grid"):
        return block[len("::grid"):].split("|")[0].strip()
    parts = [s.strip() for s in block[len("::table"):].split("|")]
    return parts[0] + (parts[2][:12] if len(parts) > 2 and parts[2] else "")


class Report:
    def __init__(self):
        self.vals = load_values()
        self.refs = load_refs(os.path.join(REPO, "paper", "references.csv"))
        self.cited = []
        self.labels = {}
        self.problems = []
        with open(os.path.join(HERE, "meta.json"), encoding="utf-8") as fh:
            self.meta = json.load(fh)
        self.counts = {}                 # floats per (kind, chapter)
        self.toc, self.figlist, self.tbllist = [], [], []
        self.made = {"toc": 0, "fig": 0, "tbl": 0}
        self.bm = 0
        self.doc = Document()
        self.style()

    # ── text processing ──
    def check_digits(self, raw, where):
        s = TOKEN.sub("", raw)
        s = CITE.sub("", s)
        s = XREF.sub("", s)
        s = ALLOWED.sub("", s)
        s = re.sub(r"`[^`]*`", "", s)            # file names and commands in code font
        if re.search(r"\d", s):
            self.problems.append("untokenised digit in %s: %r" % (where, raw[:90]))

    def resolve(self, text, where="prose"):
        self.check_digits(text, where)

        def tok(m):
            key, word = m.group(1), m.group(2)
            if key not in self.vals:
                self.problems.append("unknown claim id %s" % key)
                return "[SOURCE NOT FOUND: %s]" % key
            v = self.vals[key]
            if word and v.isdigit() and int(v) < len(WORDS):
                return WORDS[int(v)]
            return v

        def cite(m):
            keys = [k.strip().lstrip("@") for k in m.group(1).split(";")]
            nums = []
            for k in keys:
                if k not in self.refs:
                    self.problems.append("citation %s is not VERIFIED" % k)
                    return m.group(0)
                if k not in self.cited:
                    self.cited.append(k)
                nums.append(self.cited.index(k) + 1)
            return "[%s]" % ", ".join(str(n) for n in sorted(nums))

        def xref(m):
            name = m.group(1)
            if name not in self.labels:
                self.problems.append("unknown cross-reference %s" % name)
                return name
            kind, n = self.labels[name]
            return ("Fig. %s" if kind == "fig" else "Table %s") % n

        text = TOKEN.sub(tok, text)
        text = CITE.sub(cite, text)
        return XREF.sub(xref, text)

    # ── formatting ──
    def style(self):
        st = self.doc.styles["Normal"]
        st.font.name = FONT
        st.font.size = Pt(12)
        st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        st.paragraph_format.line_spacing = 1.15
        st.paragraph_format.space_after = Pt(6)
        for name, size, italic, caps in (("Heading 1", 14, False, True),
                                         ("Heading 2", 13, False, False),
                                         ("Heading 3", 12, True, False)):
            h = self.doc.styles[name]
            h.font.name, h.font.size, h.font.bold = FONT, Pt(size), True
            h.font.italic, h.font.all_caps = italic, caps
            h.font.color.rgb = RGBColor(0, 0, 0)
            rf = h.element.rPr.rFonts
            for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
                rf.attrib.pop(qn(a), None)
            for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                rf.set(qn(a), FONT)
            h.paragraph_format.line_spacing = 1.5
            h.paragraph_format.space_before = Pt(12)
            h.paragraph_format.space_after = Pt(6)
        for name in ("Figure Caption", "Table Caption"):
            s = self.doc.styles.add_style(name, 1)
            s.base_style = st
            s.font.size = Pt(10)
            s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sec = self.doc.sections[0]
        sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        sec.left_margin, sec.right_margin = Cm(3.0), Cm(2.5)
        sec.top_margin, sec.bottom_margin = Cm(2.5), Cm(2.5)

    def para(self, text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, style=None):
        p = self.doc.add_paragraph(style=style)
        p.alignment = align
        add_runs(p, text)
        return p

    def centred(self, text, size=12, bold=False, caps=False, space=6):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(space)
        r = p.add_run(text.upper() if caps else text)
        r.font.size, r.bold = Pt(size), bold
        return p

    def field(self, par, instr, shown="Right-click and choose Update Field"):
        for kind, text in (("begin", None), (None, instr), ("separate", None),
                           (None, shown), ("end", None)):
            r = par.add_run()
            if kind:
                el = OxmlElement("w:fldChar")
                el.set(qn("w:fldCharType"), kind)
            elif text == instr:
                el = OxmlElement("w:instrText")
                el.set(qn("xml:space"), "preserve")
                el.text = instr
            else:
                el = OxmlElement("w:t")
                el.text = text
            r._r.append(el)

    def page_header(self, section):
        """'N | Page' at the top right of every page, counted from the title page, as in the
        sample final report."""
        p = section.header.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        self.field(p, "PAGE", "1")
        p.add_run(" | ")
        r = p.add_run("Page")
        r.font.color.rgb = RGBColor(0x7F, 0x7F, 0x7F)
        sp = OxmlElement("w:spacing")
        sp.set(qn("w:val"), "60")
        r._r.get_or_add_rPr().append(sp)

    def bookmark(self, par, name):
        self.bm += 1
        start = OxmlElement("w:bookmarkStart")
        start.set(qn("w:id"), str(self.bm))
        start.set(qn("w:name"), name)
        end = OxmlElement("w:bookmarkEnd")
        end.set(qn("w:id"), str(self.bm))
        par._p.insert(1 if par._p.pPr is not None else 0, start)
        par._p.append(end)

    def mark(self, par, kind):
        """Bookmark the next heading or caption of this kind for its PAGEREF in the lists."""
        self.made[kind] += 1
        self.bookmark(par, "_%s%03d" % (kind, self.made[kind]))

    def grid(self, rows, widths=None, size=10, header=True, borders=True):
        t = self.doc.add_table(rows=len(rows), cols=len(rows[0]))
        if borders:
            t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                c = t.cell(i, j)
                c.paragraphs[0].paragraph_format.space_after = Pt(0)
                c.paragraphs[0].paragraph_format.line_spacing = 1.0
                if callable(val):
                    val(c.paragraphs[0])
                else:
                    add_runs(c.paragraphs[0], val)
                for r in c.paragraphs[0].runs:
                    r.font.size = Pt(size)
                    r.bold = r.bold or (header and i == 0)
                if widths:
                    c.width = Cm(widths[j])
        return t

    def table(self, rows, caption, widths=None, size=9):
        n = self.labels[caption[0]][1]
        cap = self.doc.add_paragraph(style="Table Caption")
        add_runs(cap, "Table %s: %s" % (n, self.resolve(caption[1], "caption")))
        cap.paragraph_format.keep_with_next = True
        self.mark(cap, "tbl")
        self.grid(rows, widths, size)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def labels_add(self, kind, name, chapter):
        """Floats are numbered within their chapter (Fig. 4.2, Table 7.1)."""
        if name not in self.labels:
            k = self.counts[(kind, chapter)] = self.counts.get((kind, chapter), 0) + 1
            self.labels[name] = (kind, "%s.%d" % (chapter, k))
        return self.labels[name][1]

    def figure(self, path, caption, name, width=15.5):
        full = os.path.join(REPO, path)
        if not os.path.isfile(full):
            self.problems.append("missing figure %s" % path)
            return
        n = self.labels[name][1]
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(full, width=Cm(width))
        cap = self.doc.add_paragraph(style="Figure Caption")
        add_runs(cap, "Fig. %s: %s" % (n, self.resolve(caption, "caption")))
        self.mark(cap, "fig")

    # ── pages ──
    def title_page(self):
        """Layout of the final BCSE497J template (report/template/..._FINAL.docx)."""
        m = self.meta
        self.centred("B.Tech. BCSE497J - Project-I", 14, True, space=18)
        self.centred(m["title"], 18, True, True, space=18)
        self.centred("Submitted in partial fulfillment of the requirements for the degree of",
                     12, space=0)
        self.centred("Bachelor of Technology", 13, True, space=0)
        self.centred("in", 12, space=0)
        self.centred(m["programme"], 13, True, space=6)
        self.centred("by", 12, space=6)
        t = self.doc.add_table(rows=len(m["students"]), cols=2)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, (reg, name) in enumerate(m["students"]):
            for j, v in enumerate((reg, name)):
                r = t.cell(i, j).paragraphs[0].add_run(v.upper())
                r.bold, r.font.size = True, Pt(13)
        self.centred("", space=12)
        self.centred("Under the Supervision of", 12, True, space=6)
        self.centred(re.sub(r"^(Dr\.\s*)?(.*)$", lambda g: (g.group(1) or "") + g.group(2).upper(),
                            m["guide"]), 13, True, space=0)
        self.centred(m["guide_designation"], 12, space=0)
        self.centred("School of Computer Science and Engineering (SCOPE)", 12, space=24)
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(os.path.join(HERE, "assets", "vit_logo.jpg"), width=Cm(8.77))
        self.centred(dt.date.today().strftime("%B %Y"), 12, True, space=0)

    def signed_page(self, heading, paragraphs, signature):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        self.centred(heading, 16, True, space=18)
        for text in paragraphs:
            p = self.para(text)
            p.paragraph_format.line_spacing = 1.5
        self.doc.add_paragraph()
        for line in ("Place : Vellore", "Date :"):
            self.para(line, align=WD_ALIGN_PARAGRAPH.LEFT)
        for line in signature:
            self.para(line, align=WD_ALIGN_PARAGRAPH.RIGHT)

    def front_matter(self):
        """Declaration and certificate use the template's wording; acknowledgements are
        the author's own (report/text/acknowledgements.md)."""
        m = self.meta
        title = "**%s**" % m["title"]
        self.signed_page("DECLARATION", [
            "I hereby declare that the project entitled %s submitted by me, for the award of "
            "the degree of Bachelor of Technology in %s to VIT is a record of bonafide work "
            "carried out by me under the supervision of %s." % (title, m["programme"], m["guide"]),
            "I further declare that the work reported in this project has not been submitted "
            "and will not be submitted, either in part or in full, for the award of any other "
            "degree or diploma in this institute or any other institute or university."],
            ["", "Signature of the Candidate"])
        who = ", ".join("%s (%s)" % (n, r) for r, n in m["students"])
        self.signed_page("CERTIFICATE", [
            "This is to certify that the project entitled %s submitted by %s, School of "
            "Computer Science and Engineering, VIT, for the award of the degree of Bachelor of "
            "Technology in %s, is a record of bonafide work carried out by him under my "
            "supervision during %s, as per the VIT code of academic and research ethics."
            % (title, who, m["programme"], m["semester"]),
            "The contents of this report have not been submitted and will not be submitted "
            "either in part or in full, for the award of any other degree or diploma in this "
            "institute or any other institute or university. The project fulfills the "
            "requirements and regulations of the University and in my opinion meets the "
            "necessary standards for submission."],
            ["", "Signature of the Guide", "", "Signature of Examiner(s)"])
        for line in ("", m["head_of_department"], m["department"]):
            self.para(line, align=WD_ALIGN_PARAGRAPH.LEFT)
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        self.centred("ACKNOWLEDGEMENTS", 16, True, space=18)
        with open(os.path.join(HERE, "text", "acknowledgements.md"), encoding="utf-8") as fh:
            for block in re.split(r"\n\s*\n", fh.read().strip()):
                self.para(" ".join(block.split()))
        self.para(m["students"][0][1], align=WD_ALIGN_PARAGRAPH.RIGHT)
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def two_column_page(self, heading, block, sort):
        """LIST OF ABBREVIATIONS and SYMBOLS AND NOTATIONS: a heading line 'A | B' names the
        columns, then one row per line."""
        self.centred(heading, 14, True)
        lines = [l.split("|", 1) for l in block.splitlines()[1:] if "|" in l]
        head, rows = [s.strip() for s in lines[0]], [[s.strip() for s in r] for r in lines[1:]]
        if sort:
            rows.sort(key=lambda r: r[0].lower())
        self.grid([head] + rows, widths=[3.5, 11.5], size=11)
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def code(self, path, func):
        """Appendix code: the function's source, read from the repository at build time."""
        import ast
        full = os.path.join(REPO, path)
        src = open(full, encoding="utf-8").read()
        node = next(n for n in ast.walk(ast.parse(src))
                    if isinstance(n, ast.FunctionDef) and n.name == func)
        lines = src.splitlines()[node.lineno - 1:node.end_lineno]
        self.para("`%s`, function `%s`:" % (path, func), align=WD_ALIGN_PARAGRAPH.LEFT)
        for line in lines:
            p = self.doc.add_paragraph()
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            r = p.add_run(line if line else " ")
            r.font.name, r.font.size = "Courier New", Pt(8.5)

    def lists(self):
        """Contents, figures and tables as three-column tables, as in the sample final report.
        Page numbers are PAGEREF fields to bookmarks on the headings and captions; Word fills
        them when it updates fields on opening."""
        def page(kind, i):
            return lambda par: self.field(par, "PAGEREF _%s%03d \\h" % (kind, i), "")

        def plain(text):
            return re.sub(r"[*`]", "", text)
        pages = (
            ("TABLE OF CONTENTS", ["Sl.No", "Contents", "Page No."],
             [[n, ("**%s**" % plain(t)) if lvl <= 1 else plain(t), page("toc", i)]
              for i, (n, t, lvl) in enumerate(self.toc, 1)]),
            ("LIST OF FIGURES", ["Figure No.", "Title", "Page No."],
             [[n, plain(t), page("fig", i)] for i, (n, t) in enumerate(self.figlist, 1)]),
            ("LIST OF TABLES", ["Table No.", "Title", "Page No."],
             [[n, plain(t), page("tbl", i)] for i, (n, t) in enumerate(self.tbllist, 1)]))
        for heading, head, rows in pages:
            self.centred(heading, 14, True)
            t = self.grid([head] + rows, widths=[2.2, 11.3, 2.0], size=11, borders=False)
            for row in t.rows:
                row.cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
            self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def references(self):
        for i, k in enumerate(self.cited, 1):
            e = self.refs[k]
            names = [a.strip() for a in e["authors"].split(";") if a.strip()]

            def short(a):
                sur, _, ini = a.partition(",")
                return ("%s %s" % (ini.strip(), sur.strip())).strip()
            au = [short(a) for a in names]
            if len(au) > 6:
                who = au[0] + " et al."
            elif len(au) > 1:
                who = ", ".join(au[:-1]) + ", and " + au[-1]
            else:
                who = au[0] if au else ""
            venue = e["venue"]
            bits = ["*%s*" % venue]
            if e["volume"]:
                bits.append("vol. %s" % e["volume"])
            if e["issue"]:
                bits.append("no. %s" % e["issue"])
            if e["pages"]:
                bits.append("pp. %s" % e["pages"].replace("-", "–"))
            bits.append(e["year"])
            proc = re.search(r"Proceedings|Conference|Symposium|Workshop|NOMS|Notes", venue)
            text = '[%d] %s, "%s," %s%s.' % (i, who, e["title"], "in " if proc else "",
                                             ", ".join(bits))
            if e["doi"]:
                text += " doi: %s." % e["doi"]
            elif e["url"]:
                text += " [Online]. Available: %s" % e["url"]
            p = self.para(text, align=WD_ALIGN_PARAGRAPH.LEFT)
            p.paragraph_format.left_indent = Cm(0.9)
            p.paragraph_format.first_line_indent = Cm(-0.9)

    # ── body ──
    def scan(self, text):
        """Number figures and tables within chapters and collect the contents entries before
        the text is rendered, so that cross-references and the lists at the front can point
        forward."""
        def caption(s):
            return TOKEN.sub(lambda m: self.vals.get(m.group(1), m.group(0)), s)
        chapter = None
        for block in re.split(r"\n\s*\n", text.strip()):
            block = block.strip()
            if block.startswith("::abstract"):
                self.toc.append(("", "ABSTRACT", 1))
                continue
            m = re.match(r"^(#{1,3}) (.+)$", block)
            if m:
                level, title = len(m.group(1)), m.group(2)
                num = re.match(r"^(\d+(?:\.\d+)*)\.? (.+)$", title)
                if level == 1:
                    chapter = num.group(1) if num else "A"
                if num:
                    self.toc.append((num.group(1) + ("." if level == 1 else ""), num.group(2),
                                     level))
                else:
                    self.toc.append(("", title, level))
                continue
            if block.startswith("::figure"):
                path, cap = [s.strip() for s in block[len("::figure"):].split("|", 1)]
                n = self.labels_add("fig", os.path.splitext(os.path.basename(path))[0], chapter)
                self.figlist.append((n, caption(cap)))
            elif block.startswith("::table") or block.startswith("::grid"):
                name = table_label(block.splitlines()[0])
                cap = block.splitlines()[0].split("|")[1].strip()
                self.tbllist.append((self.labels_add("tbl", name, chapter), caption(cap)))

    def paper_cell(self, key):
        """Literature-table cell for one work: authors (year), title [n], from
        paper/references.csv."""
        if key not in self.refs:
            self.problems.append("citation %s is not VERIFIED" % key)
            return key
        e = self.refs[key]
        return "%s (%s), %s %s" % (author_label(e).replace(" & ", " and "), e["year"],
                                   e["title"], self.resolve("[@%s]" % key, "table"))

    def grid_block(self, block):
        """::grid name | caption | widths, then a header line and rows, cells split by ' | '.
        A cell holding only @key renders the cited work."""
        lines = block.splitlines()
        parts = [s.strip() for s in lines[0][len("::grid"):].split("|")]
        name, cap = parts[0], parts[1]
        widths = [float(w) for w in parts[2].split(",")] if len(parts) > 2 and parts[2] else None
        rows = [[c.strip() for c in l.split(" | ")] for l in lines[1:]]

        def cell(c, i):
            if c == "#":                                 # serial number of the row
                return "%d." % i
            if re.fullmatch(r"@[a-z0-9]+", c):
                return self.paper_cell(c[1:])
            return self.resolve(c, "table " + name)
        rows = [rows[0]] + [[cell(c, i) for c in r] for i, r in enumerate(rows[1:], 1)]
        self.table(rows, (name, cap), widths, size=9)

    def body(self, text):
        self.scan(text)
        heading, words = None, 0
        bullets = []

        def close_limit():
            if heading in LIMITS and not LIMITS[heading][0] <= words <= LIMITS[heading][1]:
                self.problems.append("%s has %d words (allowed %d to %d)" % (
                    heading, words, *LIMITS[heading]))

        for block in re.split(r"\n\s*\n", text.strip()):
            block = block.strip()
            if block.startswith("::pagebreak"):
                self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
                continue
            if block.startswith("::abstract"):
                close_limit()
                heading, words = "ABSTRACT", 0
                self.mark(self.centred("ABSTRACT", 14, True), "toc")
                continue
            if block.startswith("::lists"):
                close_limit()
                heading = None
                self.lists()
                continue
            if block.startswith("::body"):
                continue
            if block.startswith("::references"):
                self.references()
                continue
            if block.startswith("::abbreviations"):
                self.two_column_page("LIST OF ABBREVIATIONS", block, sort=True)
                continue
            if block.startswith("::symbols"):
                self.two_column_page("SYMBOLS AND NOTATIONS", block, sort=False)
                continue
            if block.startswith("::grid"):
                self.grid_block(block)
                continue
            if block.startswith("::code"):
                path, func = [s.strip() for s in block[len("::code"):].split("|")]
                self.code(path, func)
                continue
            if block.startswith("::figure"):
                path, cap = [s.strip() for s in block[len("::figure"):].split("|", 1)]
                name = os.path.splitext(os.path.basename(path))[0]
                self.figure(path, cap, name)
                continue
            if block.startswith("::table"):
                parts = [s.strip() for s in block[len("::table"):].split("|")]
                name, cap = parts[0], parts[1]
                with open(os.path.join(REPO, "paper", "tables", name + ".csv"),
                          encoding="utf-8", newline="") as fh:
                    rows = list(csv.reader(fh))
                if len(parts) > 2 and parts[2]:
                    keep = [s.strip() for s in parts[2].split(";")]
                    rows = [rows[0]] + [r for r in rows[1:] if r[0] in keep]
                if len(parts) > 3 and parts[3]:
                    cols = [int(c) for c in parts[3].split(",")]
                    rows = [[r[c] for c in cols] for r in rows]
                self.table(rows, (table_label(block), cap),
                           size=8 if len(rows[0]) > 8 else 9)
                continue
            m = re.match(r"^(#{1,3}) (.+)$", block)
            if m:
                close_limit()
                level = len(m.group(1))
                heading, words = m.group(2).split(" ", 1)[-1], 0
                chap = re.match(r"^\d+\. ", m.group(2))
                if level == 1:
                    self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
                h = self.doc.add_heading(("CHAPTER " if level == 1 and chap else "") + m.group(2),
                                         level=level)
                self.mark(h, "toc")
                continue
            lines = block.splitlines()
            if all(l.startswith("- ") for l in lines):
                for l in lines:
                    t = self.resolve(l[2:].strip())
                    words += len(t.split())
                    self.para(t, style="List Bullet")
                continue
            t = self.resolve(" ".join(l.strip() for l in lines))
            words += len(re.sub(r"[*`]", "", t).split())
            self.para(t)
        close_limit()
        del bullets

    def build(self):
        self.page_header(self.doc.sections[0])
        self.title_page()
        self.front_matter()
        with open(os.path.join(HERE, "text", "report.md"), encoding="utf-8") as fh:
            self.body(fh.read())
        if self.problems:
            print("\n".join(self.problems))
            return 1
        # Ask Word to fill the table of contents, the lists and the page numbers on opening.
        upd = OxmlElement("w:updateFields")
        upd.set(qn("w:val"), "true")
        self.doc.settings.element.append(upd)
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        self.doc.save(OUT)
        print("wrote %s (%d references cited, %d figures, %d tables)" % (
            os.path.relpath(OUT, REPO), len(self.cited),
            sum(1 for k, _ in self.labels.values() if k == "fig"),
            sum(1 for k, _ in self.labels.values() if k == "tbl")))
        return 0


if __name__ == "__main__":
    sys.exit(Report().build())
