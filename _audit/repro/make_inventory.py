"""AUDIT-ONLY: builds _audit/inventory.md. Read-only over the project."""
import os, hashlib, collections
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
SKIP = {".git", ".venv", ".pytest_cache", "__pycache__", "_audit"}
BS = chr(92)

rows = []
by_hash = collections.defaultdict(list)
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in SKIP]
    for f in fn:
        p = Path(dp, f)
        rel = str(p.relative_to(ROOT)).replace(BS, "/")
        try:
            st = p.stat()
        except OSError:
            continue
        digest = hashlib.md5(p.read_bytes()).hexdigest() if st.st_size < 40_000_000 else "big"
        by_hash[digest].append(rel)
        rows.append((rel, st.st_size, datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"), digest))
rows.sort()

GUESS = [
    ("measurement/results_controlled/", "Raw controlled fault-injection run record"),
    ("measurement/results/hotel/", "Raw Hotel Reservation run record (Sep-13 batch, 42 runs)"),
    ("measurement/results_validation", "Ad-hoc HR validation run"),
    ("measurement/results/", "Raw/legacy Social Network run record"),
    ("measurement/", "Metric collection module"),
    ("EVIDENCE_FREEZE/raw/", "COPY of measurement/results_controlled (frozen duplicate)"),
    ("EVIDENCE_FREEZE/implementation/", "COPY of a pipeline script (frozen duplicate)"),
    ("EVIDENCE_FREEZE/derived/", "COPY of analysis/outputs CSV (frozen duplicate)"),
    ("EVIDENCE_FREEZE/audit/", "Self-audit note written by a previous session"),
    ("EVIDENCE_FREEZE/", "Frozen evidence bundle"),
    ("analysis/outputs/", "Phase-8 derived statistics table"),
    ("analysis/output/", "Older derived statistics table"),
    ("analysis/plots/", "Generated plot image"),
    ("analysis/", "Analysis / statistics script"),
    ("centrality/output/", "Computed centrality table"),
    ("centrality/", "Centrality computation / weight tuning"),
    ("faultinjection/", "Fault injection config / orchestrator"),
    ("infra/", "Environment setup, health check or load generation"),
    ("sdg/output/", "Extracted service dependency graph"),
    ("sdg/raw_traces/", "Raw Jaeger trace dump"),
    ("sdg/", "Trace collection / graph construction"),
    ("scripts/", "Experiment driver or figure script"),
    ("scratch/", "Ad-hoc manuscript/report generator (scratch)"),
    ("docs/", "Documentation / phase report"),
    ("tests/", "Pytest integration test"),
    (".vscode/", "Editor settings"),
]


def guess(rel):
    for k, v in GUESS:
        if rel.startswith(k):
            return v
    if rel.endswith(".md"):
        return "Manuscript draft / notes"
    if rel.endswith((".docx", ".pdf")):
        return "Generated report document"
    if rel.endswith(".csv"):
        return "Loose results CSV at repo root"
    if rel.endswith(".py"):
        return "Root-level script"
    return "Other"


dups = {k: v for k, v in by_hash.items() if len(v) > 1 and k != "big"}

out = [
    "# File Inventory (Task A)",
    "",
    f"Generated {datetime.now():%Y-%m-%d}. Excludes `.git`, `.venv`, `.pytest_cache`, `__pycache__`, `_audit`.",
    "",
    f"**{len(rows)} files.**",
    "",
    "| Path | Bytes | Modified | Purpose (guess) |",
    "|---|---:|---|---|",
]
for rel, size, mtime, _ in rows:
    out.append(f"| `{rel}` | {size} | {mtime} | {guess(rel)} |")

out += ["", "## Exact-duplicate groups (identical MD5)", ""]
for k, v in sorted(dups.items(), key=lambda x: -len(x[1])):
    shown = ", ".join(f"`{x}`" for x in sorted(v)[:6])
    out.append(f"- {len(v)} copies: {shown}" + (" ..." if len(v) > 6 else ""))

(ROOT / "_audit" / "inventory.md").write_text("\n".join(out), encoding="utf-8")
print("files", len(rows), "| duplicate groups", len(dups), "| files in a duplicate group",
      sum(len(v) for v in dups.values()))
