# CRON-20261108-B66 — W9a BOOK_TRUNC adjudication (owner go: "Do [BOOK_TRUNC 574, scheme adjudications 401, W8c memo 71] now")

## Scope
All 574 BOOK_TRUNC audit flags (349 rows / ~350 cited docs). Evidence wave: printed
books-list probe (text layer first, bounded 200dpi tesseract raster fallback, then a
global 610-doc / 18,773-page squash-key index when the row's cited docs miss),
strict zero-guess acceptance (RULES §4/§6/§6b; W8a auditor-FP precedent).

## Adjudication results (574 = 388 + 186)
- 388 auditor false positives reclassified by the UPGRADED auditor rule (no data change):
  entries starting author-like that end with a publisher token from the corpus ending
  distribution (McGraw Hill / PHI / TMH / Springer / CRC Press / Pearson Education / ...),
  an edition-year form, or an author-at-end form. Rule upgrade persisted in
  audit_rules.py (_PUB_SUFFIXES + start-broken guard), so future audits stay clean.
- 186 probed against the printed books lists (page-cited verdicts in w9a_ckpt.json):
  - 1 verbatim heal APPLIED (§6b corrections_json before/after + page evidence):
    digital-image-processing textbooks[2]: '...Prentice Hall, Upper Saddle' ->
    '...Prentice Hall, Upper Saddle River, NJ.' (raw character-prefix preserved;
    fuller print at mca_y3_syllabus_2015-16.pdf#1a425db0ddc35c7c p.16).
  - 36 verified_complete -> accepted-print (print == stored or strict containment;
    the storage faithfully mirrors the print; flagged action upgraded with page evidence).
  - 74 print_garbled -> needs_review (the SOURCE PRINT itself ends abruptly — e.g. the
    2026-27 BPharm catalog prints entry 5's author line without completing the title).
  - 27 corroborated_elsewhere -> needs_review (same book printed in a DIFFERENT form in a
    non-cited corpus doc; junction conflicts ('-SS Rao' vs ', SS Rao', 'D. L. Loudon' vs
    'Loudon D L') forbid overwrite under zero-guess; stored form kept with the pointer).
  - 44 no_print_found -> needs_review (no printed entry recovered; probe pages recorded).
  - 4 sha_unresolved -> needs_review (post-reset missing docs; re-supply to resume).

## Gates / push
G1 PASS, G2 PASS (6,412 owned codes), G3 PASS, G6 PASS (containment on touched rows).
Data change: 1 row / 1 edit. Auditor + w9a toolchain (w9a_book_trunc.py, page index)
synced to repo pipeline/. T2T calls: 0 (deterministic wave; keys untouched).
