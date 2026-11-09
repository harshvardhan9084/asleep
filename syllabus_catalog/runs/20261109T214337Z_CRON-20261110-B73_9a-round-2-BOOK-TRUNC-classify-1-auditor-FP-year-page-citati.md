# Manifest — CRON-20261110-B73 — W9a round-2 (BOOK_TRUNC) + audit v21

## Context
- Reset #57 before this run: .env stripped, repo/toolchain/wave_state/w9a ckpt lost, worklog reverted to B28 era. Standing restore routine executed: .env re-provisioned (7 vars, chmod 600), repo cloned @995eaea (B72), CSV md5-verified 376e7ed06de3ba638a505efeef23540d (3,085×62 v2.1), toolchain 440 files resynced, wave_state rebuilt (batch_next=73), corpus_map rebuilt (613 PDFs → 610 unique shas, matches B71/B72).
- Standing mission (owner directive 2026-11-08): repair the audit flags. Entry state 948 flags / 776 rows (B72).

## W9a round-2 (BOOK_TRUNC 169 flags / 128 rows)
- classify: 1 auditor-FP (advances-in-carpet-manufacturing reference_books_structured[6] — complete citation "…by A D Sule(New Age International Pvt Ltd Publishers, New Delhi),1997,171"; year+page-count tail) / 168 probe.
- index: 18,773 pages / 610 docs / 145 raster-skipped (33 s).
- probe: 168/168 in one budgeted pass — print_garbled 78, no_print_found 40, verified_complete 24, corroborated_elsewhere 23, sha_unresolved 3 (page-cited evidence in w9a ckpt, e.g. distributed-dbms-mca::reference_books_structured[2] → mca-integrated_y3_syllabus_2026-27.pdf#047c7c8deed42470 p.20).
- apply: healed=0 (no verbatim heal available; zero-guess held — print_garbled/corroborated/no_print/sha_unresolved stay flagged needs_review).

## Audit v21 (audit_rules.py)
1. BOOK_TRUNC end-whitelist: edition-year+page-count citation tail `(?:19|20)\d{2},\d{1,4}$` accepted as complete print (mirrors W9a classify END handling; B66 accepted-print class) — exactly the 1 planned FP, no over-drops.
2. verified_complete probe verdicts → recorded-honest flag drop (B66 accepted-print class operationalized; same semantics as v19 kls_not_printed / v20 w10d TOKEN_N): 24 flags dropped, zero data change.
3. Durability fix (reset-proof): all 168 probe verdicts appended as page-cited note segments ("W9a2 probe: <status> @ <field> at <file#sha> p.N — detail") to the rows' notes evidence surface (127 rows, notes-only diff verified cell-by-cell vs B72 CSV; append-only, existing verbatim content untouched). Scan-side skip now keys on the durable notes marker; ckpt drop kept as fallback. Future resets lose nothing.

## Result
- Flags 948 → 923 (BOOK_TRUNC 169 → 144); flagged rows 776 → 763.
- Gates G1/G2/G3/G6 PASS; G2 owned codes 6,412 unchanged; rows 3,085 × 62 schema v2.1.
- CSV md5 376e7ed0… → 53343e7650fd6a2af3afbc92fb3b195b (notes-only).
- Durably committed: syllabus_catalog/runs/w9a_ckpt.json (probe evidence, survives resets).
- T2T: 0 calls this run (deterministic fitz text-layer reads only; mercury_stats unchanged).

## Remaining flag classes (923)
TYPE_EMPTY 385, BOOK_TRUNC 144 (recorded-honest needs_review), CREDIT_FORMULA 139, SESS_SUM 125, MARKS_SUM 122, BOOK_MERGED 6, DISPLAY_MISSING 2. Next candidates: W10e TYPE_EMPTY evidence round (385), W9b round-2 scheme probes (CREDIT_FORMULA/SESS_SUM/MARKS_SUM).
