#!/usr/bin/env python3
"""
sanitize_paper_notations.py
Sanitizes mathematical notations, dashes, quotation marks, and non-ASCII glyphs
across all paper drafts to standard, clean, robust ASCII notations.
Zero words are changed; only the notations/characters are standardized.
"""

import re
from pathlib import Path

ARTIFACT_DIR = Path(r"C:\Users\daksh\.gemini\antigravity-ide\brain\35fef10f-b661-4c76-8fdf-ffe550bd93ad")

# Mapping of problematic/non-ASCII characters to standard ASCII academic notations
CHAR_MAP = {
    "\u2014": " -- ",      # Em dash
    "\u2013": "-",         # En dash (number ranges, page ranges)
    "\u03c1": "rho",       # Greek rho
    "\u0394": "Delta-",    # Greek Delta (e.g. Delta-p95)
    "\u03c3": "sigma",     # Greek sigma
    "\u03a3": "sum",       # Greek capital Sigma
    "\u03b1": "alpha",     # Greek alpha
    "\u207a": "^+",        # Superscript + (e.g. d^+)
    "\u207b": "^-",        # Superscript - (e.g. d^-)
    "\u2081": "_1",        # Subscript 1 (e.g. w_1)
    "\u2082": "_2",        # Subscript 2 (e.g. w_2)
    "\u2083": "_3",        # Subscript 3 (e.g. w_3)
    "\u2099": "_n",        # Subscript n (e.g. v_n)
    "\u00b2": "^2",        # Squared
    "\u00b3": "^3",        # Cubed
    "\u2076": "^6",        # Superscript 6 (e.g. 10^6)
    "\u2212": "-",         # Unicode minus
    "\u00b7": " * ",       # Middle dot
    "\xd7": " x ",         # Multiplication sign (e.g. 12 services x 3 faults)
    "\u2208": " in ",      # Element of
    "\u2286": " subset of ", # Subset
    "\u2260": " != ",      # Not equal
    "\u2264": " <= ",      # Less than or equal
    "\u2265": " >= ",      # Greater than or equal
    "\u2248": " ~= ",      # Approximately equal
    "\u00b1": "+/-",       # Plus-minus
    "\u2192": " -> ",      # Arrow
    "\u2018": "'",         # Left single quote
    "\u2019": "'",         # Right single quote / apostrophe
    "\u201c": '"',         # Left double quote
    "\u201d": '"',         # Right double quote
    "\u00a0": " ",         # Non-breaking space
    "\u00f6": "oe",        # o-umlaut (Thoenes)
}


def sanitize_file(filepath: Path) -> dict:
    with open(filepath, "rb") as f:
        raw = f.read()

    # Handle raw byte 0x97 (CP1252 em dash)
    if b"\x97" in raw:
        raw = raw.replace(b"\x97", b" -- ")

    # Decode with UTF-8 (using latin-1 fallback if any invalid bytes remain)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    # Replace each character according to CHAR_MAP
    counts = {}
    for ch, replacement in CHAR_MAP.items():
        cnt = text.count(ch)
        if cnt > 0:
            counts[ch] = cnt
            text = text.replace(ch, replacement)

    # Clean up any duplicate spaces around dashes or symbols, but preserve indentation/newlines
    # e.g., '  --  ' -> ' -- '
    text = re.sub(r"[ \t]+--[ \t]+", " -- ", text)
    text = re.sub(r"[ \t]+x[ \t]+", " x ", text)
    text = re.sub(r"[ \t]+\*[ \t]+", " * ", text)

    # Check for remaining non-ASCII
    remaining_non_ascii = [ch for ch in text if ord(ch) > 127]

    # Save back cleanly in UTF-8 (which is now 100% pure ASCII compatible)
    with open(filepath, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

    return {
        "file": filepath.name,
        "replacements": counts,
        "remaining_non_ascii": len(remaining_non_ascii),
        "total_chars": len(text),
    }


def main():
    target_files = [
        "final_paper_v3.md",
        "paper_draft_v2.md",
        "final_journal_paper.md",
        "paper_draft.md",
    ]

    for fname in target_files:
        fpath = ARTIFACT_DIR / fname
        if fpath.exists():
            res = sanitize_file(fpath)
            print(f"File: {res['file']}")
            print(f"  Total chars: {res['total_chars']}")
            print(f"  Replacements made: {sum(res['replacements'].values())}")
            for ch, count in res["replacements"].items():
                print(f"    U+{ord(ch):04X} ({CHAR_MAP[ch]}): {count}")
            print(f"  Remaining non-ASCII chars: {res['remaining_non_ascii']}")
            print("-" * 50)


if __name__ == "__main__":
    main()
