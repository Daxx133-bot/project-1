#!/usr/bin/env python3
import json
import re
from pathlib import Path

TRANSCRIPT_PATH = Path(r"C:\Users\daksh\.gemini\antigravity-ide\brain\35fef10f-b661-4c76-8fdf-ffe550bd93ad\.system_generated\logs\transcript_full.jsonl")
TARGET_FILE = Path(r"C:\Users\daksh\.gemini\antigravity-ide\brain\35fef10f-b661-4c76-8fdf-ffe550bd93ad\paper_draft_v2.md")

# 1. Extract original lines from transcript
p1, p2 = None, None
with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        si = data.get("step_index")
        if si == 668:
            p1 = data["content"]
        elif si == 670:
            p2 = data["content"]

def parse_view_file(content):
    lines = {}
    for line in content.split("\n"):
        m = re.match(r"^(\d+): (.*)$", line)
        if m:
            lines[int(m.group(1))] = m.group(2)
        elif re.match(r"^(\d+):$", line):
            lines[int(line[:-1])] = ""
    return lines

lines1 = parse_view_file(p1)
lines2 = parse_view_file(p2)
all_lines = {**lines1, **lines2}
text = "\n".join([all_lines.get(i, "") for i in range(1, max(all_lines.keys()) + 1)])

# 2. Character replacements to standard ASCII academic notations
CHAR_MAP = [
    ("\u2014", " -- "),      # Em dash
    ("\u2013", "-"),         # En dash (page ranges, number ranges)
    ("\u03c1", "rho"),       # Greek rho
    ("\u0394", "Delta-"),    # Greek Delta
    ("\u03c3", "sigma"),     # Greek sigma
    ("\u03a3", "sum"),       # Greek capital Sigma
    ("\u03b1", "alpha"),     # Greek alpha
    ("\u207a", "^+"),        # Superscript + (d^+)
    ("\u207b", "^-"),        # Superscript - (d^-)
    ("\u2081", "_1"),        # Subscript 1 (w_1)
    ("\u2082", "_2"),        # Subscript 2 (w_2)
    ("\u2083", "_3"),        # Subscript 3 (w_3)
    ("\u2099", "_n"),        # Subscript n (v_n)
    ("\u00b2", "^2"),        # Squared
    ("\u00b3", "^3"),        # Cubed
    ("\u2076", "^6"),        # Superscript 6 (10^6)
    ("\u2212", "-"),         # Unicode minus
    ("\u00b7", " * "),       # Middle dot
    ("\xd7", " x "),         # Multiplication sign
    ("\u2208", " in "),      # Element of
    ("\u2286", " subset of "), # Subset
    ("\u2260", " != "),      # Not equal
    ("\u2264", " <= "),      # Less than or equal
    ("\u2265", " >= "),      # Greater than or equal
    ("\u2248", " ~= "),      # Approximately equal
    ("\u00b1", "+/-"),       # Plus-minus
    ("\u2192", " -> "),      # Arrow
    ("\u2018", "'"),         # Left single quote
    ("\u2019", "'"),         # Right single quote
    ("\u201c", '"'),         # Left double quote
    ("\u201d", '"'),         # Right double quote
    ("\u00a0", " "),         # Non-breaking space
    ("\u00f6", "oe"),        # o-umlaut (Thoenes)
]

clean = text
for old, new in CHAR_MAP:
    clean = clean.replace(old, new)

# Normalize spaces around dashes and operators
clean = re.sub(r"[ \t]+--[ \t]+", " -- ", clean)
clean = re.sub(r"[ \t]+\*[ \t]+", " * ", clean)
clean = re.sub(r"[ \t]+x[ \t]+", " x ", clean)

# Save cleanly in UTF-8
with open(TARGET_FILE, "w", encoding="utf-8", newline="\n") as f:
    f.write(clean)

non_ascii = [ch for ch in clean if ord(ch) > 127]
print(f"paper_draft_v2.md cleaned successfully! Total chars: {len(clean)}, non-ASCII count: {len(non_ascii)}")
