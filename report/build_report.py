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
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "paper"))
from build_docx import add_runs, load_refs  # noqa: E402

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
            return ("Fig. %d" if kind == "fig" else "Table %d") % n

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

    def field(self, par, instr):
        for kind, text in (("begin", None), (None, instr), ("separate", None),
                           (None, "Right-click and choose Update Field"), ("end", None)):
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

    def page_numbers(self, section, fmt):
        section.footer.is_linked_to_previous = False
        p = section.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self.field(p, "PAGE")
        pg = OxmlElement("w:pgNumType")
        pg.set(qn("w:fmt"), fmt)
        pg.set(qn("w:start"), "1")
        section._sectPr.append(pg)

    def table(self, rows, caption, widths=None, size=9):
        n = self.labels_add("tbl", caption[0])
        cap = self.doc.add_paragraph(style="Table Caption")
        add_runs(cap, "Table %d. %s" % (n, self.resolve(caption[1], "caption")))
        t = self.doc.add_table(rows=len(rows), cols=len(rows[0]))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                c = t.cell(i, j)
                c.paragraphs[0].paragraph_format.space_after = Pt(0)
                c.paragraphs[0].paragraph_format.line_spacing = 1.0
                add_runs(c.paragraphs[0], val)
                for r in c.paragraphs[0].runs:
                    r.font.size = Pt(size)
                    r.bold = r.bold or i == 0
                if widths:
                    c.width = Cm(widths[j])
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def labels_add(self, kind, name):
        if name not in self.labels:
            self.labels[name] = (kind, 1 + sum(1 for k, _ in self.labels.values() if k == kind))
        return self.labels[name][1]

    def figure(self, path, caption, name, width=15.5):
        full = os.path.join(REPO, path)
        if not os.path.isfile(full):
            self.problems.append("missing figure %s" % path)
            return
        n = self.labels_add("fig", name)
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(full, width=Cm(width))
        cap = self.doc.add_paragraph(style="Figure Caption")
        add_runs(cap, "Fig. %d. %s" % (n, self.resolve(caption, "caption")))

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
        self.centred(m["guide"], 13, True, space=0)
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
            ["", "Signature of the Guide", "", "Examiner(s)", "",
             m["head_of_department"], m["programme"]])
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        self.centred("ACKNOWLEDGEMENTS", 16, True, space=18)
        with open(os.path.join(HERE, "text", "acknowledgements.md"), encoding="utf-8") as fh:
            for block in re.split(r"\n\s*\n", fh.read().strip()):
                self.para(" ".join(block.split()))
        self.para(m["students"][0][1], align=WD_ALIGN_PARAGRAPH.RIGHT)
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def abbreviations(self, block):
        self.centred("LIST OF ABBREVIATIONS", 14, True)
        rows = [l.split("|", 1) for l in block.splitlines()[1:] if "|" in l]
        rows.sort(key=lambda r: r[0].strip().lower())
        t = self.doc.add_table(rows=len(rows), cols=2)
        for i, (a, b) in enumerate(rows):
            t.cell(i, 0).paragraphs[0].add_run(a.strip()).bold = True
            t.cell(i, 1).paragraphs[0].add_run(b.strip())
            t.cell(i, 0).width, t.cell(i, 1).width = Cm(3), Cm(12)
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
        for heading, instr in (("TABLE OF CONTENTS", 'TOC \\o "1-3" \\h \\z \\u'),
                               ("LIST OF FIGURES", 'TOC \\h \\z \\t "Figure Caption,1"'),
                               ("LIST OF TABLES", 'TOC \\h \\z \\t "Table Caption,1"')):
            self.centred(heading, 14, True)
            self.field(self.doc.add_paragraph(), instr)
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
    def number_floats(self, text):
        """Assign figure and table numbers before the text is rendered, so that a
        cross-reference may precede its figure or table."""
        for block in re.split(r"\n\s*\n", text.strip()):
            block = block.strip()
            if block.startswith("::figure"):
                path = block[len("::figure"):].split("|", 1)[0].strip()
                self.labels_add("fig", os.path.splitext(os.path.basename(path))[0])
            elif block.startswith("::table"):
                self.labels_add("tbl", table_label(block))

    def body(self, text):
        self.number_floats(text)
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
                self.centred("ABSTRACT", 14, True)
                continue
            if block.startswith("::lists"):
                close_limit()
                heading = None
                self.lists()
                continue
            if block.startswith("::body"):
                sec = self.doc.add_section(WD_SECTION.NEW_PAGE)
                self.page_numbers(sec, "decimal")
                continue
            if block.startswith("::references"):
                self.references()
                continue
            if block.startswith("::abbreviations"):
                self.abbreviations(block)
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
                chap = re.match(r"^(\d+)\. ", m.group(2))
                if level == 1:
                    self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
                    if chap:
                        self.centred("CHAPTER %s" % chap.group(1), 14, True, space=0)
                self.doc.add_heading(m.group(2), level=level)
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
        self.title_page()
        sec = self.doc.add_section(WD_SECTION.NEW_PAGE)
        self.page_numbers(sec, "lowerRoman")
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
