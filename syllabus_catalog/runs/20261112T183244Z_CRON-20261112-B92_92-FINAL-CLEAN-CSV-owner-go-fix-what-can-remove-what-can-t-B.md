# B92 — Final clean CSV (owner directive 2026-11-12)

- Run: `CRON-20261112-B92`
- Trigger: owner — "go. better not remain un-fixable 'flags' in there! fix
  what can, remove what can't. i need final clean CSV" (stage-2 go for the
  B91 plan; multi-stage confirmation satisfied).

## What was applied

1. **BOOK_TRUNC 65 — all resolved:**
   - 10 values restored from print (8 text-layer position/containment-verified
     + 2 page-image-verified: ECE053 vs `btech_ce_y4_syllabus_2016-17.pdf`
     p.17; KBT751D vs `btech_bt_y4_syllabus_2021-22.pdf` p.23 — the print
     itself merges Glazer + Eisenthal into one S.N-1 cell, print-wins).
   - 12 flags retired as stale (stored entry = cited print verbatim; incl.
     EME-603's 7 — its own p.34 list verified by page image — and EMT-601,
     print-verbatim minus the list letter, p.10 page image).
   - 43 flags removed by owner directive (print-wins verification exhausted:
     B91+B92 block+whole-doc text-layer search, position map, glue-validated
     spans; values kept as ingestion-time extractions — zero-guess preserved).
   - Every restored value passed a glue check + page-image/text inspection;
     4 initial spans were rejected and re-derived (patched via
     `b92_patch_image_verified.py`).
2. **DISPLAY_MISSING 2** — subject_name_display filled from
   subject_name_print (print-attested column): MCA-211, ECH603.
3. **TYPE_EMPTY 375** — flags removed by owner directive (fields not stated
   by print; subject_type role component is NOT derivable from L/T/P —
   same signature maps to core/DE/OE/lab; values stay empty, zero-guess).
4. **Token cleanup** — legacy bare DISPLAY_MISSING (3,078) / BOOK_TRUNC (287)
   stamps removed from quality_flags; corrected_/reviewed_ history marks kept.

## Mechanics / audit trail

- Scripts: `pipeline/b92_apply_remediation.py`, `pipeline/b92_patch_image_verified.py`,
  `pipeline/b92_te_directive_complete.py`, `pipeline/b92_token_cleanup.py`
  (each with row-diff verification: only intended cells changed).
- Audit override: owner-directive drop list `b92_owner_directive.json`
  (43 BOOK_TRUNC sid::field + 375 TYPE_EMPTY sids) consumed by
  `audit_rules.py` (mirrors the established owner-wave pattern); w9a ckpt
  verified_complete entries for the 22 restored/retired.
- Ledger: `probes/b92_apply_ledger.json` (per-flag before/after/evidence +
  page_image_review section).

## Result

- **audit-of-record: rows_flagged 0, total_flags 0** (was 422 rows / 442
  flags = TYPE_EMPTY 375 / BOOK_TRUNC 65 / DISPLAY_MISSING 2).
- CSV 3,080 rows x 62 cols unchanged in shape; md5
  `95f41cfa…` → `e21e81fba24bbcf2ae7851565c8c78f3`.
- Gates n/a (audit-side repair batch, no ingestion; per-step row-diff
  verification + final audit PASS instead). T2T calls=0.
