# B96 — `df_year_plan.csv`: the per-student year-plan grain (owner need #1)

- Run: `CRON-20261113-B96` (owner request, interactive, 2026-11-13)
- Zero writes to the of-record CSV: `syllabus_extreme_rich.csv` byte-identical
  (md5 323ffc13eb5bfe5887fdd819bea63a19); audit-of-record 0/0.

## What was built

The owner's #1 need: "a student tells us course + branch + academic year and
we list the ~6+6 subjects they study each semester." The deduplicated catalog
cannot answer this (subject-level grain). The grain survives in the SOURCE
PDFs (scheme tables, deterministic text layer) and the 109 committed draft
JSONs. New deliverable:

`syllabus_catalog/df_year_plan.csv` — 7,223 rows x 19 cols, one row per
PRINTED scheme line (doc x semester x SN): source (pdf-scheme-page /
draft-fallback), doc_file + doc_sha16 + doc_rel, course, session,
doc_branches (from the cover page), semester (+ semester_int, Roman
normalized), SN, codes, subject_name_print, L/T/P, credit, row_kind
(subject / elective-slot / non-credit), subject_id (catalog link via
normalized codes), nums_raw (marks columns as printed).

Parser: layout-based (fitz word coordinates). Rows delimited by SN entries;
midpoint y-boundaries (SNs vertically centred on wrapped names); numeric
column semantics from data-driven x-clusters (first three = L/T/P, last =
credit when 'Credit' prints); header-vocabulary tokens suppressed inside row
bands. Verified exactly on the known cell: BTech CSE y3 2024-25 sems 5-6 =
BCS501/502/503 + BCS551-554 + BNC501/502 + elective slots, every row linked
to the right catalog subject_id.

Tool: `pipeline/resolve_year_plan.py` — course + branch + session (+ year)
-> semester-wise printed subject lists; `--demo` for five worked examples.

## Coverage (honest)

- 11 programs present: BTech 4,417 rows / BVoc 767 / MBA 552 / MTech 368 /
  BArch 371 / MCA 205 / BPharm 106 / BDes 169 / BFA 23 / BFad 8 / Other 237.
- BTech: 13 sessions with year-2-4 semester coverage, including the recent
  eras in force today — 2024-25 (33 docs, sems 3-8), 2025-26 (31 docs,
  sems 3-8), 2026-27 (13 docs, sems 1-8).
- MBA: 12 sessions; 2024-25 (5 docs, y1), 2025-26 (6 docs, y1-y2).
- MCA/BPharm: partial (newest-era scheme docs for some cells are not in the
  repo corpus; recoverable by adding those PDFs and re-running b96).
- MBA table layouts differ (code column inside the name flow) — rows parse
  with subject links lost on some docs; flagged for a later pass.
- 1,377 draft-fallback rows (docs whose PDFs are not in the repo).

## Record

Batch numbering: next = B97. The B95 df_syllabus.csv consumer view is
unchanged. Todo for later batches: MBA layout pass, BPharm/MCA missing
session PDFs, elective-slot -> subject resolution via the elective pools in
the catalog.
