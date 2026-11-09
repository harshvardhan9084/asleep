# Manifest — CRON-20261110-B75 — W9b round-2 (scheme invariants) + audit v22

## Context
- Reset #59 on entry: routine restore executed (.env 7 vars, repo @d4db881 B74+manifest-fix, CSV md5 06f83f59 verified, toolchain 441 files, corpus_map 613→610 shas, wave_state batch_next=75; w9a/w10c ckpts restored from repo runs/). Loop: NOOP (W3 queue 0; 0 T2T).
- Flag-repair mission continued at 892 flags / 732 rows.

## W9b round-2 (CREDIT_FORMULA 139 / SESS_SUM 125 / MARKS_SUM 122; 281 rows)
- classify 281 rows; probe 281/281 code-anchored in cited docs (60 hits / 221 miss); adjudicate: accepted-print 12, stored_matches_no_print 71, no_print_found 198.
- Zero invariant-consistent repairs exist in this round (adjudicate edits=0) — zero-guess held; the B67 repairs were the unique ones.

## Audit v22 (audit_rules.py)
1. accepted-print verdicts (printed scheme row matches storage verbatim — AKTU's own table breaks the arithmetic; B67 committed class) → recorded-honest flag drop, same semantics as v21 W9a verified_complete / v19 / v20. 13 flags dropped across the 12 rows (one row carried 2 invariants). Zero data change.
2. Durability: all 281 verdicts appended as "W9b2 probe:" note segments (evidence + printed-row quote); the accepted-print marker drives the scan-side skip (reset-proof). w9b_adjudication.json committed to syllabus_catalog/runs/.
3. stored_matches_no_print / no_print_found stay honestly flagged with probe annotations.

## Result
- Flags 892 → 879 (CREDIT_FORMULA 129, SESS_SUM 123, MARKS_SUM 121); flagged rows 720.
- Gates G1/G2(6,412)/G3/G6 PASS; rows 3,085 × 62 v2.1; CSV md5 06f83f59… → 7b73a07e278eb1a8a961f5cf03c19ee5 (notes-only diff, verified cell-by-cell).
- T2T: 0 calls (deterministic local reads; mercury keys idle).

## Remaining flag classes (879)
TYPE_EMPTY 354, BOOK_TRUNC 144, CREDIT_FORMULA 129, SESS_SUM 123, MARKS_SUM 121, BOOK_MERGED 6, DISPLAY_MISSING 2. Next candidates: W10c global-index fallback (140 TYPE_EMPTY no_code_print_found), BOOK_MERGED/BOOK_TRUNC OCR rounds, DISPLAY_MISSING 2.
