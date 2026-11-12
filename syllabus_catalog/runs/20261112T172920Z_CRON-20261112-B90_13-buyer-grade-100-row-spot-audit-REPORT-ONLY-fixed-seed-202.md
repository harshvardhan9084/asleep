# CRON-20261112-B90 — T13 buyer-grade 100-row spot audit (report-only) — CASCADE COMPLETE

Run: cron delivery of job 524343 standing payload, ~2026-11-13 IST slot after
B89. NO RESET: 7-key .env intact (names verified), HEAD f5cb20b = `git
ls-remote origin main` (= B89 push), download/ CSV md5 95f41cfa byte-identical
to repo copy, toolchain synced. READ FIRST from repo CHANGELOG (top entry B89,
"T13 next — final test of the plan").

## Test executed
T13 (buyer-grade 100-row spot audit, P1, REPORT-ONLY quality gate):
- Sample: reproducible fixed-seed random.Random(20261113) over subject rows
  sorted by subject_id → 100 rows (list recorded in the ledger).
- 10 deterministic checks per row: identity, numeric sanity (mark fields incl.
  sum sessional+ese==total when all numeric; '–' print markers tolerated as
  info), semester range, CO completeness, unit completeness, structured
  books/experiments JSON parse, citation integrity (every cited sha16 checked
  against the repo corpus; T12's 6 documented unresolved shas read dynamically
  from the T12 ledger and counted as known, not new), buyer-facing display,
  flag consistency vs the AUDIT-OF-RECORD, session coherence (info).
- Check-model corrections mid-run (probe bugs, not data bugs): (1)
  quality_flags CSV string is append-only history incl. corrected_* marks —
  flag consistency now compares row state against audit_flags.json ACTIVE
  flags, not the historical string; (2) experiments entries use key 'exp', not
  'book'; (3) empty primary_code on documented pool/slot rows (HSMC/EOE
  printed slots, accumulator rows with all_codes/code_history) → info note,
  not issue.

## Verdicts (100 rows)
- clean 34 / minor 64 / issues 2 (clean 34.0%).
- The 64 minor rows carry notes only: 57 rows with repair-history
  corrected_* marks (proof of past fixes, not defects), 7 documented
  pool/slot rows without a single primary code, 2 rows citing older-doc
  editions (info), 9 rows referencing T12's known unresolved shas.
- 2 issues, both identity:effective_session_latest_empty — pharmacognosy-iii
  BOP364 [BPharm], advanced-spinning-technology RTT602 [BTech]. REPORT-ONLY
  per plan: listed for the owner; NO fix, NO flag change (not computable from
  any print without stage-2 evidence; honest needs_review).
- No new unresolved citation shas. Flag-consistency vs audit-of-record: 0
  mismatches (active flags match row states).

## Cascade status — COMPLETE
All 13 tests of the 2026-11-11 quality-test plan now executed:
T1(adjudicated B82) / T2(stage-1 G2 PASS) / T3 / T4+T5(B81 fixes) / T6 / T7 /
T8 / T9 / T10 / T11 / T12(6 shas stay flagged) / T13(this batch). Runs revert
to audit-only unless the owner opens a new work item.

## Standing mechanics compliance
REPORT-ONLY: no CSV write, no quality_flags change. Fresh audit_rules.py scan
on the unchanged CSV: flags 442 = TYPE_EMPTY 375 / BOOK_TRUNC 65 /
DISPLAY_MISSING 2 — unchanged. Gates n/a (no CSV mutation). enqueue_corpus:
0 new PDFs (165 PARKED untouched). T2T: calls=0 (deterministic corpus probe,
no mercury drafting; .env active keys 5+PAT, verified by name only).
wave_runner --loop remains RETIRED (W3 closed). Batch numbering: B89 last →
this is B90.

## Files
- work/pipeline_v2/probes/t13_probe_ledger.json (copy:
  syllabus_catalog/owner_requests/t13_probe_ledger.json)
- syllabus_catalog/owner_requests/quality_probe_T13_2026-11-12.xlsx (3 sheets)
- syllabus_catalog/runs/<ts>_CRON-20261112-B90_*.md (this manifest)
