# CRON-20261112-B88 — T9 book-entry identity within row, stage-1 + stage-2 (ledger-only)

Run: cron delivery of job 524343 standing payload, ~2026-11-12 22:30 IST slot after
B87. Workspace was RESET again (foreign DATABASE_URL-only .env, repo clone absent,
CSV stale md5 8faad353): standard restore executed — foreign .env isolated as
.env.foreign_backup_20261112_170138 (never printed), 7-key .env rebuilt (names
verified only), anonymous clone, HEAD dd259f6 verified against `git ls-remote`
(= B87 push), CSV copied and md5-verified byte-identical (95f41cfa…), pipeline
toolchain rsynced from repo HEAD.

## Test executed
T9 (book-entry identity within row, P3, expected yield: low) — stage-1 within-row
book duplication + stage-2 own-doc print counting. Stage 1 over
textbooks_structured / reference_books_structured (single 'book' strings;
1,316/1,415 rows non-empty):
- cross_list_TB_RB: identical squashed entry in BOTH lists of a row → 165 groups;
- exact_within_TB / exact_within_RB → 8 + 10 groups;
- near_dup: token-Jaccard >= 0.85, not exact (WEAKER class — Jaccard also catches
  genuinely different sibling books like "Machine Design" vs "Machine Design Data
  Book"; the print decides) → 99 groups.
Total 211 flagged rows / 282 groups.

## Stage-2 method (two iterations, v2 is authoritative)
v1 counted title-fragment occurrences on CITED pages only — degenerate (all
counts 0: citations in this corpus carry no usable page hints). v2 scopes the
count to the row's COURSE BLOCK: pages of the row's own cited docs where the
primary_code prints near the row's subject name (T7 name_near machinery, all
pages, no early return); whole-doc count kept as fallback context ONLY (a
year-wide scheme book legitimately prints one book under several courses —
whole-doc-only hits are tagged weaker, never attested). Fragments: longest
quoted segment per entry, else first ~6 words, squashed; near-dup groups need
BOTH variants to print for attestation (one variant printing = stored drift
beyond print).

## Verdicts (rows: 211; groups: 282)
- attested_print_duplication 16 rows / 30 groups — the course block itself
  prints the entry (or both variants) >= 2 times; 6b print-wins → composition,
  NO fix.
- attested_in_doc_fallback_review 41 / 54 — course block not locatable in the
  doc text layer, but fragment hits >= 2 somewhere in the doc (weaker).
- drafting_side_duplication_review 71 / 89 — print carries the entry ONCE in the
  course block while the row stores it twice (cross-list TB&RB mostly): stored
  duplication beyond print. UNfixed per standing mechanics — later
  multi-confirmed batch (page-image fallback per the B14 v14 class) before any
  dedupe/flag.
- book_print_unverified 83 / 109 — fragment not found anywhere in the cited
  docs' text layers (book sections missing from text layer; NOT counted as
  evidence of anything).

## Standing mechanics compliance
LEDGER-ONLY: no CSV write, no quality_flags change. Fresh audit_rules.py scan
on the unchanged CSV: flags 442 = TYPE_EMPTY 375 / BOOK_TRUNC 65 /
DISPLAY_MISSING 2 — unchanged. Gates n/a (no CSV mutation). enqueue_corpus:
0 new PDFs (165 PARKED untouched). T2T: calls=0 (deterministic corpus probe, no
mercury drafting; .env active keys 5+PAT, verified by name only). wave_runner
--loop remains RETIRED (W3 closed). Batch numbering from CHANGELOG: B87 last →
this is B88. Cascade next: T6 (unit-text containment, 10% sample), then T13.

## Files
- work/pipeline_v2/probes/t9_probe_ledger.json (copy:
  syllabus_catalog/owner_requests/t9_probe_ledger.json)
- syllabus_catalog/owner_requests/quality_probe_T9_2026-11-12.xlsx (3 sheets)
- syllabus_catalog/runs/<ts>_CRON-20261112-B88_*.md (this manifest)
