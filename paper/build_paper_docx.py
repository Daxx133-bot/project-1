"""
build_paper_docx.py -- Word copy of the IEEE Access manuscript (paper/latex/main.tex), for
readers and similarity checks that need a .docx. Single column; the LaTeX PDF stays the
version of record.

Nothing is retyped. The LaTeX source is converted by pandoc after these substitutions:
  \\val{id}      value from paper/latex/generated/values.tex (the build fails on an unknown id)
  \\cite{..}     IEEE number from the order of paper/latex/build/main.bbl
  \\ref{..}      section, figure, table, algorithm or equation number, counted as LaTeX does
  figures       paper/figures/<name>.png in place of generated/figures/<name>.pdf
  references    formatted from the VERIFIED rows of paper/references.csv, in .bbl order

Needs pandoc: pip install pypandoc_binary. Run python paper/build_latex.py first, so that
generated/ and build/main.bbl are current.

Output: paper/latex/build/manuscript_ieee.docx
Run: python paper/build_paper_docx.py
"""
from __future__ import annotations

import os
import re
import sys

import pypandoc
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from build_docx import add_runs, load_refs

HERE = os.path.dirname(os.path.abspath(__file__))
LATEX = os.path.join(HERE, "latex")
OUT = os.path.join(LATEX, "build", "manuscript_ieee.docx")
FONT = "Times New Roman"
ROMAN = "I II III IV V VI VII VIII IX X XI XII XIII XIV XV".split()
REF_MARK = "REFERENCE-LIST-GOES-HERE"


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def strip_comments(text):
    """Drop comments; a line holding only a comment goes too, so it cannot split a paragraph."""
    return "\n".join(re.sub(r"(?<!\\)%.*", "", line) for line in text.splitlines()
                     if not line.lstrip().startswith("%"))


def group_end(text, i):
    """Index just past the brace group that opens at text[i] == '{'."""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{" and text[j - 1] != "\\":
            depth += 1
        elif text[j] == "}" and text[j - 1] != "\\":
            depth -= 1
            if depth == 0:
                return j + 1
    raise ValueError("unbalanced braces after %r" % text[i:i + 60])


def replace_command(text, name, fn, nargs=1):
    """Replace \\name[opt]{a}{b}.. (balanced braces) by fn(a, b, ..)."""
    pat = re.compile(r"\\%s(\[[^\]]*\])?(?=\{)" % name)
    while True:
        m = pat.search(text)
        if not m:
            return text
        args, j = [], m.end()
        for _ in range(nargs):
            k = group_end(text, j)
            args.append(text[j + 1:k - 1])
            j = k
        text = text[:m.start()] + fn(*args) + text[j:]


def unwrap_table(m):
    """A table float becomes its caption line followed by the bare tabular, which pandoc
    converts reliably; captions inside floats and \\resizebox wrappers are otherwise lost."""
    body = m.group(0)
    i = body.index("\\caption{") + len("\\caption")
    caption = body[i + 1:group_end(body, i) - 1]
    tabular = re.search(r"\\begin\{tabular\}.*?\\end\{tabular\}", body, re.S).group(0)
    return "\n\n\\noindent %s\n\n%s\n\n" % (caption, tabular)


def expand_inputs(text):
    def inc(m):
        name = m.group(1)
        if name.endswith("values"):
            return ""
        path = os.path.join(LATEX, name if name.endswith(".tex") else name + ".tex")
        return expand_inputs(strip_comments(read(path)))
    return re.sub(r"\\input\{([^}]+)\}", inc, text)


def load_values():
    vals = {}
    for m in re.finditer(r"\\@namedef\{val@([a-z0-9_]+)\}\{(.*)\}%",
                         read(os.path.join(LATEX, "generated", "values.tex"))):
        vals[m.group(1)] = m.group(2).replace("\\ensuremath{-}", "\u2212")
    return vals


def bbl_order():
    return re.findall(r"\\bibitem\{([^}]+)\}", read(os.path.join(LATEX, "build", "main.bbl")))


def compress(nums):
    """IEEE style, as the cite package prints it: [1], [3]–[5]."""
    nums, out, i = sorted(set(nums)), [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append("[%d]\u2013[%d]" % (nums[i], nums[j]) if j - i >= 2 else
                   ", ".join("[%d]" % n for n in nums[i:j + 1]))
        i = j + 1
    return ", ".join(out)


def number_labels(text):
    """Assign each \\label the number LaTeX would print for it, and number the headings,
    captions and equations in the text, since pandoc numbers none of them."""
    labels, counts, current = {}, {"sec": 0, "sub": 0, "fig": 0, "tab": 0, "alg": 0, "eq": 0}, None
    event = re.compile(r"\\(section|subsection)(\*?)\{|\\begin\{(figure|table|algorithm|equation)"
                       r"\*?\}|\\caption\{|\\label\{([^}]+)\}|\\appendices")
    out, pos, env, appendix = [], 0, None, False
    for m in event.finditer(text):
        out.append(text[pos:m.start()])
        pos = m.end()
        kind, star, envname, label = m.group(1), m.group(2), m.group(3), m.group(4)
        if m.group(0) == "\\appendices":
            appendix, counts["sec"] = True, 0
        elif kind == "section" and appendix:
            counts["sec"] += 1
            current = ("app", chr(64 + counts["sec"]))
            out.append("\\section{Appendix %s: " % current[1])
        elif kind == "section" and not star:
            counts["sec"] += 1
            counts["sub"] = 0
            current = ("sec", ROMAN[counts["sec"] - 1])
            out.append("\\section{%s. " % current[1])
        elif kind == "subsection" and not star:
            counts["sub"] += 1
            current = ("sub", "%s-%s" % (ROMAN[counts["sec"] - 1], chr(64 + counts["sub"])))
            out.append("\\subsection{%s. " % chr(64 + counts["sub"]))
        elif kind:
            out.append(m.group(0))
        elif envname:
            key = {"figure": "fig", "table": "tab", "algorithm": "alg", "equation": "eq"}[envname]
            counts[key] += 1
            env = key
            n = counts[key]
            current = (key, ROMAN[n - 1] if key == "tab" else str(n))
            out.append(m.group(0))
        elif label is None:                                   # \caption{
            prefix = {"fig": "Fig. %s. ", "tab": "TABLE %s. ", "alg": "Algorithm %s: "}
            out.append("\\caption{" + (prefix[env] % current[1] if env in prefix else ""))
        else:
            labels[label] = current[1]
    out.append(text[pos:])
    return "".join(out), labels


def convert_algorithm(m):
    body = m.group(0)
    cap = re.search(r"\\caption\{(.*?)\}\s*\\begin\{algorithmic\}", body, re.S).group(1)
    steps = re.search(r"\\begin\{algorithmic\}(?:\[\d\])?(.*?)\\end\{algorithmic\}", body,
                      re.S).group(1)
    req = re.search(r"\\Require (.*?)(?=\\State|\\If)", steps, re.S)
    steps = steps[req.end():] if req else steps
    items = []
    for cmd, rest in re.findall(r"\\(State|If|Else|EndIf)(.*?)(?=\\State|\\If|\\Else|\\EndIf|$)",
                                steps, re.S):
        rest = re.sub(r"\\Comment\{(.*?)\}", r" (\1)", rest.strip())
        if cmd == "State":
            items.append(rest)
        elif cmd == "If":
            items.append("if " + re.sub(r"^\{(.*)\}$", r"\1", rest, flags=re.S) + ":")
        elif cmd == "Else":
            items.append("otherwise:")
    head = "\\textbf{%s}\n\n" % cap.strip()
    if req:
        head += "\\textbf{Input:} %s\n\n" % req.group(1).strip()
    return head + "\\begin{enumerate}\n" + "\n".join("\\item " + i for i in items) + \
        "\n\\end{enumerate}\n"


def to_latex():
    vals, order = load_values(), bbl_order()
    tex = expand_inputs(strip_comments(read(os.path.join(LATEX, "main.tex"))))
    tex = re.sub(r"\\makeatletter\s*\\newcommand\{\\val\}.*?\\makeatother", "", tex, flags=re.S)

    missing = []

    def val(m):
        if m.group(1) not in vals:
            missing.append(m.group(1))
            return "[SOURCE NOT FOUND: %s]" % m.group(1)
        return vals[m.group(1)]
    tex = re.sub(r"\\val\{([a-z0-9_]+)\}", val, tex)

    def cite(m):
        keys = [k.strip() for k in m.group(1).split(",")]
        unknown = [k for k in keys if k not in order]
        if unknown:
            missing.extend("cite:" + k for k in unknown)
        return compress([order.index(k) + 1 for k in keys if k in order])
    tex = re.sub(r"\\cite\{([^}]+)\}", cite, tex)

    tex, labels = number_labels(tex)

    def ref(m):
        if m.group(1) not in labels:
            missing.append("ref:" + m.group(1))
            return "??"
        return labels[m.group(1)]
    tex = re.sub(r"\\ref\{([^}]+)\}", ref, tex)
    tex = re.sub(r"\\label\{[^}]+\}", "", tex)
    tex = re.sub(r"\\begin\{algorithm\}.*?\\end\{algorithm\}", convert_algorithm, tex, flags=re.S)

    eq = iter(range(1, 100))
    tex = re.sub(r"\\begin\{equation\}(.*?)\\end\{equation\}",
                 lambda m: "\\[%s \\qquad (%d)\\]" % (m.group(1).strip(), next(eq)), tex, flags=re.S)

    def graphic(m):
        name = os.path.splitext(os.path.basename(m.group(2)))[0]
        png = os.path.join(HERE, "figures", name + ".png")
        if not os.path.isfile(png):
            missing.append("figure:" + name)
        width = "16cm" if "textwidth" in m.group(1) else "12cm"
        return "\\includegraphics[width=%s]{%s}" % (width, png.replace("\\", "/"))
    tex = re.sub(r"\\includegraphics\[([^\]]*)\]\{([^}]+)\}", graphic, tex)

    tex = replace_command(tex, "makecell", lambda a: a.replace("\\\\", " "))
    tex = replace_command(tex, "IEEEPARstart", lambda a, b: a + b, nargs=2)
    tex = re.sub(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", unwrap_table, tex, flags=re.S)
    tex = re.sub(r"\\(scriptsize|footnotesize|small)\b|\\setlength\{[^}]*\}\{[^}]*\}", "", tex)
    tex = tex.replace("\\begin{IEEEkeywords}", "\\textit{Index Terms}---").replace(
        "\\end{IEEEkeywords}", "")
    tex = re.sub(r"\\begin\{IEEEbiographynophoto\}\{([^}]*)\}", r"\n\n\\noindent\\textbf{\1} ", tex)
    tex = tex.replace("\\end{IEEEbiographynophoto}", "\n\n")
    tex = re.sub(r"\\markboth\{.*?\}\{.*?\}\s*\n", "\n", tex, flags=re.S)
    tex = re.sub(r"\\bibliographystyle\{[^}]*\}", "", tex)
    tex = re.sub(r"\\bibliography\{[^}]*\}", "\n\n%s\n\n" % REF_MARK, tex)
    if missing:
        sys.exit("unresolved: " + ", ".join(missing))
    return tex, order


def border(table):
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + side)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "000000")
        borders.append(el)
    tbl_pr.append(borders)


def finish(path, order):
    doc = Document(path)
    for st in doc.styles:
        if st.type != 1:
            continue
        st.font.name = FONT
        rpr = st.element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts")
            rpr.insert(0, rf)
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            rf.attrib.pop(qn(a), None)
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rf.set(qn(a), FONT)
        if st.name.startswith(("Heading", "Title", "Subtitle")):
            st.font.color.rgb = RGBColor(0, 0, 0)
    for name, size in (("Normal", 10), ("Body Text", 10), ("First Paragraph", 10),
                       ("Compact", 10), ("Abstract", 9), ("Title", 20), ("Author", 11),
                       ("Heading 1", 11), ("Heading 2", 10), ("Image Caption", 8),
                       ("Table Caption", 8)):
        if name in [s.name for s in doc.styles]:
            doc.styles[name].font.size = Pt(size)
    if "Heading 1" in [s.name for s in doc.styles]:
        doc.styles["Heading 1"].font.all_caps = True
    for p in doc.paragraphs:
        if re.match(r"TABLE [IVX]+\. ", p.text):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_with_next = True
            for r in p.runs:
                r.font.size = Pt(8)
        elif p.style.name in ("Body Text", "First Paragraph"):
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for t in doc.tables:
        border(t)
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(7.5)
    for sec in doc.sections:
        sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        sec.left_margin = sec.right_margin = Cm(2.0)
        sec.top_margin = sec.bottom_margin = Cm(2.0)

    refs = load_refs(os.path.join(HERE, "references.csv"))
    mark = next(p for p in doc.paragraphs if p.text.strip() == REF_MARK)
    mark.insert_paragraph_before("References", style="Heading 1")
    for i, k in enumerate(order, 1):
        p = mark.insert_paragraph_before()
        add_runs(p, ieee_reference(i, refs[k]))
        p.paragraph_format.left_indent = Cm(0.8)
        p.paragraph_format.first_line_indent = Cm(-0.8)
        for r in p.runs:
            r.font.size = Pt(8)
    mark._element.getparent().remove(mark._element)
    doc.save(path)


def ieee_reference(i, e):
    """One IEEE-style reference line; *venue* renders in italics."""
    def short(a):
        sur, _, ini = a.partition(",")
        return ("%s %s" % (ini.strip(), sur.strip())).strip()
    au = [short(a) for a in e["authors"].split(";") if a.strip()]
    if len(au) > 6:
        who = au[0] + " et al."
    elif len(au) > 1:
        who = ", ".join(au[:-1]) + ", and " + au[-1]
    else:
        who = au[0] if au else ""
    bits = ["*%s*" % e["venue"]]
    if e["volume"]:
        bits.append("vol. %s" % e["volume"])
    if e["issue"]:
        bits.append("no. %s" % e["issue"])
    if e["pages"]:
        bits.append("pp. %s" % e["pages"].replace("-", "\u2013"))
    bits.append(e["year"])
    proc = re.search(r"Proceedings|Conference|Symposium|Workshop|NOMS|Notes", e["venue"])
    text = '[%d] %s, "%s," %s%s.' % (i, who, e["title"], "in " if proc else "", ", ".join(bits))
    if e["doi"]:
        text += " doi: %s." % e["doi"]
    elif e["url"]:
        text += " [Online]. Available: %s" % e["url"]
    return text


def main() -> int:
    tex, order = to_latex()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pypandoc.convert_text(tex, "docx", format="latex", outputfile=OUT,
                          extra_args=["--resource-path", LATEX])
    finish(OUT, order)
    print("wrote %s (%d references)" % (os.path.relpath(OUT, os.path.dirname(HERE)), len(order)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
