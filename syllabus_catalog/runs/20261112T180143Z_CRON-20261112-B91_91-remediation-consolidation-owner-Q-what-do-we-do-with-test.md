# B91 — Remediation consolidation (owner direction 2026-11-12)

- Run: `CRON-20261112-B91`
- Trigger: owner message — "so what now? what are we gonna do with the test
  results? i wanted the clean and faithful 'syllabus rich' CSV at first place"
  → first batch after CASCADE COMPLETE (T1-T13, B90/a6f7dfd): convert the
  cascade evidence into the concrete path to the clean CSV.

## What ran (LEDGER-ONLY, 0 CSV changes)

1. **BOOK_TRUNC restoration dry-run** (`pipeline/b91_booktrunc_probe.py`,
   ledger `owner_requests/b91_booktrunc_probe_ledger.json`):
   for each of the 65 active BOOK_TRUNC flags, the stored entry (located by
   the audit's field index — detail is a display tail `t[-80:]`) was searched
   in the row's own cited docs' printed book blocks (squashed containment,
   block-scoped with whole-doc fallback, backward/forward span assembly with
   numbered-boundary cutting):

   | verdict | n | meaning |
   |---|---|---|
   | restorable_from_print | 12 | one unambiguous strictly-longer printed span → B92 value restore (page-image verify first) |
   | stored_matches_print | 9 | print shows exactly the stored text → flag stale, retire with evidence |
   | ambiguous_multi_candidate | 1 | several printed spans → manual pick |
   | not_in_text_layer | 37 | stored entry absent from cited text layer → stay flagged / page-image queue |
   | block_pages_not_found | 4 | row's course block not locatable in text layer → stay / page-image |
   | entry_not_found_in_row | 2 | audit slug mismatch (managerial-economics-mba, active-pharmaceutical-…-the) → B92 slug remap then re-probe |

2. **DISPLAY_MISSING dry-run**: both rows (MCA-211, ECH603) have a non-empty
   `subject_name_print` → display fill candidate from a print-attested column.

3. **Plan workbook** `owner_requests/quality_probe_B91_remediation_plan_2026-11-12.xlsx`
   (+ copy at `download/art_d_final/syllabus_remediation_plan_B91.xlsx`),
   6 sheets: PATH_TO_CLEAN_CSV / RESTORE_CANDIDATES (15) /
   FLAG_RETIRE_CANDIDATES (9) / STAY_FLAGGED / OPEN_REVIEW_QUEUE (149:
   T9 112, T7 18, T3 10, T6 6+3, T13 2, T10 1) / CASCADE_RESULTS.

## Proposed next batch (B92, staged for owner confirmation per multi-stage mechanics)

- 12 + 2 value restorations from print (page-image verified before write)
- 9 BOOK_TRUNC flag retirements (flags-column change only, print evidence per row)
- 2 slug remaps + probe re-run for the leftover 2
- TYPE_EMPTY 375 and T12's 6 shas stay flagged (zero-guess doctrine)

## Invariants

- CSV md5 unchanged `95f41cfa2f1c505047c5620eef30dc7e`; flags 442 unchanged
  (375/65/2); gates n/a (no CSV mutation); T2T calls=0.
- Probe worked from the audit-of-record active set (422 rows / 442 flags),
  which T13 verified 0-mismatch at B90.
