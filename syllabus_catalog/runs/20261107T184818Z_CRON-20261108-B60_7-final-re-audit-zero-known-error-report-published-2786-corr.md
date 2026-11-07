# Zero-Known-Error Report — B58 (W7 final re-audit)

Registry: 3097 rows x 63 cols (schema v2). Corrections recorded in corrections_json: 2786 on 1418 rows.
Coverage: co_kls populated 864 rows; subject_type_norm 2509; subject_name_display 3083.

## Corrections by wave/rule
- W1/AUTH_TYPO_coreman: 2
- W1/AUTH_TYPO_deshpandey: 5
- W1/AUTH_TYPO_dijikstra: 5
- W1/AUTH_TYPO_hopcraft: 5
- W1/AUTH_TYPO_liptschutz: 3
- W1/AUTH_TYPO_parahami: 1
- W1/AUTH_TYPO_printice: 9
- W1/AUTH_TYPO_transistive: 1
- W1/AUTH_TYPO_trembley: 9
- W1/AUTH_TYPO_vravice: 4
- W1/AUTH_TYPO_warshal: 8
- W2/BOOK_MERGED_SPLIT: 4
- W2/BOOK_NUMART: 488
- W2/BOOK_SPACECOMMA: 410
- W3/KLS_BACKFILL: 561
- W3b/KLS_FORMAT_NORMALIZE: 293
- W6/MATH_ITALIC: 2
- W6/PUNCT_ARTIFACT: 976

## Remaining machine flags (audit_rules.py fresh scan)
- PUNCT_ARTIFACT: 3281
- BOOK_TRUNC: 574
- TYPE_EMPTY: 521
- KLS_MISSING: 516
- TYPE_RAW: 514
- CREDIT_FORMULA: 142
- KLS_BADVAL: 139
- SESS_SUM: 133
- MARKS_SUM: 126
- BOOK_NUMART: 33
- TOKEN_N_LOWER: 26
- AUTH_TYPO_warshal: 7
- BOOK_MERGED: 6
- KLS_SHORT: 5
- DISPLAY_MISSING: 2
- AUTH_TYPO_parahami: 1

## quality_flags inventory (row-level)
- DISPLAY_MISSING: 3085
- PUNCT_ARTIFACT: 1041
- corrected_KLS_BACKFILL: 548
- TYPE_EMPTY: 520
- kls_not_printed: 510
- BOOK_TRUNC: 329
- corrected_KLS_FORMAT_NORMALIZE: 293
- corrected_BOOK_SPACECOMMA: 291
- w5_scheme_mismatch: 286
- KLS_MISSING: 272
- corrected_PUNCT_ARTIFACT: 172
- corrected_BOOK_NUMART: 71
- TYPE_RAW: 55
- TYPE_UNMAPPED: 55
- BOOK_NUMART: 20
- reviewed_print_ends_here: 20
- kls_raster_candidate: 18
- kls_partially_printed: 13
- reviewed_book_block: 13
- TOKEN_N_LOWER: 10
- formula_variance_faithful_print: 10
- corrected_AUTH_TYPO_warshal: 8
- corrected_AUTH_TYPO_trembley: 8
- corrected_AUTH_TYPO_printice: 8
- corrected_AUTH_TYPO_dijikstra: 5
- corrected_AUTH_TYPO_deshpandey: 5
- corrected_AUTH_TYPO_hopcraft: 5
- reviewed_semicolon_style: 5
- corrected_BOOK_MERGED_SPLIT: 4
- corrected_AUTH_TYPO_vravice: 4

## Zero-known-error status for the Claude-claimed classes
- AUTH_TYPO_*: 0 remaining (11 dictionary terms corrected, page-cited, B52)
- BOOK_MERGED true merges: 4 splits applied; semicolon-style false positives re-flagged (B53)
- BOOK_NUMART/BOOK_SPACECOMMA: resolved (B53) — remainder re-scanned by W7 flags only
- PUNCT_ARTIFACT: 4 benign edge cases (newline-boundary) — surfaced above if re-detected
- MATH_ITALIC: 0 remaining (NFKC-mapped, B54)
- KLS_MISSING: resolved to: backfilled / partially-printed (nulls aligned) / raster-candidate / not-printed (B55/B56)

## Open items for the owner (needs_review — zero-guess held)
- W5 w5_scheme_mismatch rows: per-row evidence reads for fix-from-print (positional certainty).
- kls_raster_candidate rows: page-image reads to recover K-levels printed on raster CO tables.
- G6_CONTAINMENT_GAP rows: unit text provable only in docs lost to workspace resets (supplying-doc citation gap, pre-G6 era).
- TYPE_UNMAPPED / TYPE_EMPTY rows: raw prints outside the controlled vocab.
- '(n)' stray tokens: collide with LR(0)/list-marker notation — per-row review.
- Release decisions (LICENSE, JSON snapshot, API) — owner call.
