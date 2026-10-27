# Project report (BCSE497J Project-I)

The final project report, built in the format of the university's final template
(`template/BCSE497J_Project_I_Report_Template_FINAL.docx`).

```bash
python -m pytest -q -m "not integration" -p no:cacheprovider > report/out/pytest_offline.txt
python report/make_report_figures.py   # Gantt chart from commit dates; DFD, use case, sequence diagrams
python report/build_report.py          # writes report/out/Project_Report.docx
python report/check_overlap.py         # wording overlap with the paper, drafts and old draft
```

Rules: every number in `text/report.md` is a `{{claim_id}}` from `paper/numbers.json`; the build
fails on a typed digit. Result figures and tables are the paper's, read from `paper/`. The text
was written for the report and is not copied from the paper (see `out/overlap.txt`).
The Review-2 draft (`../BCSE497J_Microservice_Failure_Analysis_Report.docx`) predates the
audit and is not used. Open the .docx in Word and accept the prompt to update fields, which
fills the table of contents and lists. Not for mirroring to the share repository: it holds
personal details, and a public copy would match the report in a plagiarism check.
