# syllabus_catalog

Structured, provenance-traced syllabus registry for Dr. A.P.J. Abdul Kalam Technical
University (AKTU), Lucknow — built as open reference data under the 5-course charter:
**B.Tech / B.Pharm / BCA / MCA / MBA**.

## Files

- `syllabus_extreme_rich.csv` — the main rich syllabus registry (canonical deliverable).

## Current snapshot

- Shape: **134 rows x 57 columns** (1 header row excluded from that count).
- Row kinds (`row_kind`): `subject` x122, `elective_pool` x2, `program_rule` x2,
  `semester_summary` x8.
- **237 owned course codes**, each appearing in **exactly one** row (subject-first,
  define-once registry; five code generations A/B/K/R/M cross-referenced per subject).
- Coverage so far: B.Tech batch ingests (2021-22 K-era through 2024-25) across CSE-family
  branches, E&C, Mining Engineering and common-subject pools; B.Pharm / BCA / MCA / MBA
  rows land as their session documents are processed from the corpus.

## Data invariants

- **Zero-guess**: every cell is either verbatim-print-derived from an authorized source
  document or explicitly blank. Blank means "not printed", never "unknown".
- **Provenance**: unit/CO text carries its source citation (`source_syllabus` chain).
- **Newer-wins, field-wise**: when a subject appears across sessions, each field holds
  the latest printed value; older sessions remain visible in history columns.
- **`*_print` columns** preserve the printed original form (spelling/spacing included).
- **`rr_sid` is intentionally blank**: row IDs are assigned by the owner at the very end.

## Refresh cadence

Updated per processed batch of the pipeline-v2 corpus queue
(`PDFs/5-course/<session>/<file>`), after gates G1 (schema), G2 (code idempotency),
G3 (subject idempotency) and G6 (provenance) pass.

> Registry built from AKTU's own published syllabus/evaluation-scheme documents.
