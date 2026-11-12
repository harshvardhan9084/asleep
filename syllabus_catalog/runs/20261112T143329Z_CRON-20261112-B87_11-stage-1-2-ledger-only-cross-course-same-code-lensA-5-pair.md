# CRON-20261112-B87 — T11 cross-course same-code consistency, stage-1 + stage-2 (ledger-only)

Run: cron delivery of job 524343 standing payload, ~2026-11-12 20:00 IST slot after
B86. Workspace was RESET again (foreign DATABASE_URL-only .env, repo clone absent,
CSV stale md5 8faad353): standard restore executed — foreign .env isolated as
.env.foreign_backup_20261112_142752 (never printed), 7-key .env rebuilt (names
verified only), anonymous clone, HEAD 48cd487 verified against `git ls-remote`
(= B86 push), CSV copied and md5-verified byte-identical (95f41cfa…), pipeline
toolchain rsynced from repo HEAD. Local probes wiped by the reset — durable
record = repo owner_requests/ (t7/t8/t10/t11 ledgers committed there).

## Test executed
T11 (cross-course same-code consistency, P2, expected yield: low) — two
deterministic lenses + stage-2 own-cited-doc page evidence:
- Lens A (primary key): primary_code groups spanning >=2 course_name values →
  5 cross-course pairs (4 same-identity @ratio>=0.8, 1 mismatch). Same-course
  sharing is T1's domain — skipped by construction.
- Lens B (plan columns all_codes + code_history_all): code primary-owned in
  course X and listed in course-Y row's code fields → 9 codes/11 refs;
  8 same-identity refs skipped (attested shared-course context), 3
  xref_identity_mismatch candidates.
Stage 2 method: per involved row, locate the code in the row's OWN cited docs
(fitz text layer, cited pages first then whole doc, T1/T3/T7/T8 sha index +
name_near) — for Lens-A pairs with both sides found, the PRINTED names are
compared across courses (print wins per 6b; a stored-name variant is not a
collision). Classifier corrected mid-run: both-found alone never proves
"distinct" — v1 print_confirms_distinct verdicts were re-derived with the
printed-name cross-check and lens-B reclassified as listing anomalies.

## Verdicts
- attested_cross_course_shared 4: BVA251 Sports & Yoga (BCA/BTech/MCA, all six
  prints) and RAS254 Professional Communication Lab (BTech 'Laboratory
  Practicals' vs MCA 'Lab' — printed names cross-match; stored-name diff =
  variant). No fix.
- unverified_shared_pair 1: BVE301 UHV — BTech row's Common-Subjects-2nd-Year
  sha unresolvable (same limitation recorded in B10/B86); BCA side prints fine.
- xref_listing_review 3 (code-field LISTING anomalies, UNfixed for a later
  multi-confirmed batch): NGP401 (BTech 'GP' primary) listed in the MCA
  General-Proficiency row (whose own primary NGP-701 is not in its doc's text
  layer); RAS254 cross-listed in the MCA lab row's code fields; RHU001 (MCA
  Human Values primary) listed in the MBA Cyber Security row RCA405's code
  fields — both rows' own prints are coherent; the anomaly is the listing only.
- 0 print_confirms_distinct, 0 hard code collisions, 0 fix candidates.

## Standing mechanics compliance
LEDGER-ONLY: no CSV write, no quality_flags change. Fresh audit_rules.py scan
on the unchanged CSV: flags 442 = TYPE_EMPTY 375 / BOOK_TRUNC 65 /
DISPLAY_MISSING 2 — unchanged. Gates n/a (no CSV mutation). enqueue_corpus:
0 new PDFs (165 PARKED untouched). T2T: calls=0 (deterministic corpus probe, no
mercury drafting; .env active keys 5+PAT, verified by name only). wave_runner
--loop remains RETIRED (W3 closed). Batch numbering from CHANGELOG: B86 last →
this is B87. Cascade next: T9 (book-entry identity within row), then
T6 (10% sample) → T13.

## Files
- work/pipeline_v2/probes/t11_probe_ledger.json (copy:
  syllabus_catalog/owner_requests/t11_probe_ledger.json)
- syllabus_catalog/owner_requests/quality_probe_T11_2026-11-12.xlsx (3 sheets)
- syllabus_catalog/runs/<ts>_CRON-20261112-B87_*.md (this manifest)
