# CRON-20261112-B86 — T10 CO duplication across rows, stage-1 + stage-2 (ledger-only)

Run: cron delivery of job 524343 standing payload, ~2026-11-12 17:26 IST slot after
B85. Workspace was RESET again (foreign DATABASE_URL-only .env, repo clone absent,
CSV stale md5 8faad353): standard restore executed — foreign .env isolated as
.env.foreign_backup_20261112_115636 (never printed), 7-key .env rebuilt (names
verified only), anonymous clone, HEAD 7421469 verified against `git ls-remote`
(= B85 push), CSV copied and md5-verified byte-identical (95f41cfa…), pipeline
toolchain rsynced from repo HEAD. Local probes/worklog wiped by the reset —
durable record = repo runs/ + owner_requests/ (t7/t8/t10 ledgers committed there).

## Test executed
T10 (CO duplication across rows, P3, expected yield: low) — stage-1 clustering +
stage-2 own-cited-doc page evidence. Rule: signature = ordered tuple of normalized
non-empty co1..co6 texts (MIN_CO>=3 to avoid trivial single-sentence collisions);
exact clusters = identical signature across >=2 rows; near clusters = token-Jaccard
>=0.85 on concatenated CO text (prefilter: >=8 shared tokens and >=70% of smaller
set), not exact. Pool 1,326 of 3,080 subject rows carry >=3 CO slots; 34 skipped
(<3 slots). Stage 1 yield: 78 exact clusters / 166 rows + 15 near clusters / 31
rows (197 member rows total).

## Stage-2 verdicts (every member row's OWN cited docs, CO1 fragment search —
squashed text, cited pages first then whole doc, fitz text layer, no early stop)
Cluster verdicts: attested_print_duplication 89 / inconclusive_partial 3 /
drafting_side_duplication_review 1. Member verdicts: co_print_found 192 /
inconclusive_doc_unresolved 2 / co_print_not_found 1 / no_citation 2.

- attested_print_duplication 89 clusters: >=2 member rows' own docs print the same
  shared CO text (e.g. IoT quartet BBC012/BCS070/KOT501/BMI012 — cross-program
  shared electives; BCA/MCA shared-course families; KCS502/MCA404 compiler-design;
  UHV, OS, Python, SPM, data-analytics...). 6b print-wins: the duplication exists
  in the printed docs themselves → composition/template class, NO fix.
- drafting_side_duplication_review 1 cluster (the run's only genuine review
  candidate, UNfixed per standing mechanics — multi-stage confirmation needed):
  digital-signal-processing BEC503 (own 2025-26 ACT doc prints the COs, p7) vs
  signal-processing KIC-052 (EI 2020-21 doc cited twice; shared CO1 fragment NOT
  in its text layer) → KIC-052's stored COs read as copied from the BEC503 print
  beyond its own doc's evidence. Later batch: page-image check of the EI doc
  (text layer may lack the CO block) BEFORE any flag/fix.
- inconclusive_partial 3 clusters: UHV BVE301 pair (BTech row's
  Common-Subjects-2nd-Year sha unresolvable + AG docs lack CO block in text
  layer; BCA row attested p10 of 2025-26 doc); KEC-101T (attested 3 docs) vs
  KEC101TH (no_citation); CMOS BEC-063 (attested p25 of 2024-25 doc) vs
  BEC653A LAB row (no_citation — lab row carries the theory row's COs verbatim,
  suspicious but print-unverifiable; recorded, no fix).
- near-dup clusters (15) are mostly SAME subject across sessions/programs with
  wording drift ("to " prefix, embedded "co1" token in BMBAB209, analyse/analyze,
  mechatronics/mechatronic) — all members' prints found; cross-check context only.

## Standing mechanics compliance
LEDGER-ONLY: no CSV write, no quality_flags change. Fresh audit_rules.py scan on
the unchanged CSV: flags 442 = TYPE_EMPTY 375 / BOOK_TRUNC 65 / DISPLAY_MISSING 2
— unchanged. Gates n/a (no CSV mutation). enqueue_corpus: 0 new PDFs (165
PARKED in PDFs/other_courses untouched). T2T: calls=0 (deterministic corpus
probe, no mercury drafting; .env active keys 5+PAT, verified by name only).
wave_runner --loop remains RETIRED (W3 closed). Batch numbering from CHANGELOG:
B85 last → this is B86. Cascade next: T11 (cross-course same-code consistency),
then T9 → T6 (10%) → T13.

## Files
- work/pipeline_v2/probes/t10_probe_ledger.json (copy:
  syllabus_catalog/owner_requests/t10_probe_ledger.json)
- syllabus_catalog/owner_requests/quality_probe_T10_2026-11-12.xlsx (3 sheets:
  cluster verdicts / member evidence / rule+skip transparency)
- syllabus_catalog/runs/<ts>_CRON-20261112-B86_*.md (this manifest)
