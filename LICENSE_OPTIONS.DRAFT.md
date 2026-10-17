# DRAFT — licence options (not a licence; nothing here is granted)

This file is a decision aid. No licence has been chosen, and until a `LICENSE` file is
added the repository is "all rights reserved" by default. It is named so that GitHub and
Zenodo do not detect it as a licence. Do not mirror it to the share copy.

The repository contains three kinds of material, which are usually licensed separately.

| Material | Where | Common choices |
|---|---|---|
| Code | `analysis/`, `centrality/`, `measurement/`, `faultinjection/`, `infra/`, `tools/`, `paper/*.py`, `tests/` | MIT (short, permissive); Apache-2.0 (permissive, with an explicit patent grant) |
| Data | `data/` (campaign run records, persisted Jaeger spans, graphs) | CC-BY-4.0 (attribution required); CC0-1.0 (no conditions) |
| Text and figures | `paper/`, `_audit/`, `PREREGISTRATION*.md`, `README.md` | CC-BY-4.0 |

Points to settle before choosing:

1. **Rights holder.** Confirm whether Vellore Institute of Technology has any claim over
   work done as part of a programme, and whether co-authors must agree.
2. **Third-party material.** The `infra/` compose overrides and load-generator files are
   written to run against DeathStarBench, which is a separate project with its own
   licence. They are not copies of DeathStarBench code, but check this before licensing,
   and do not add DeathStarBench files to this repository.
3. **The journal.** PeerJ publishes articles under CC-BY-4.0; supplementary code and data
   deposited elsewhere may carry their own licences.
4. **One licence or two.** A single `LICENSE` file (for example MIT) plus a short note in
   `README.md` stating that `data/` and `paper/` are CC-BY-4.0 is a common arrangement.

To adopt a choice: add the standard, unmodified licence text as `LICENSE` (and, if data and
text differ, `LICENSE-DATA` or a README section), add the SPDX identifier to
`pyproject.toml` and to `CITATION.cff`, and delete the word DRAFT from both.
