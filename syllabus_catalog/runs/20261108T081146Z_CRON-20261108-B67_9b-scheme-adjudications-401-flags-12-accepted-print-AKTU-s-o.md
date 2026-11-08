# CRON-20261108-B67 — W9b scheme adjudications 401 (owner go: "Do [BOOK_TRUNC 574, scheme adjudications 401, W8c memo 71] now")

## Scope
All 401 W5 scheme flags (CREDIT_FORMULA 142 / SESS_SUM 133 / MARKS_SUM 126; 296 rows).
Evidence: the printed scheme rows — provenance quotes ('3-1-0 / 4 cr', 'PS 50 + TE 50'),
verbatim pipe rows, and code-anchored doc probes — adjudicated per RULES §3 (latest
print wins) and §6b(4) (scheme line must prove the extraction error).

## Method (zero-guess)
For each row: structured primary-print values (L-T-P, 'N cr', SW/PS/TE, CT/TA/ESE/Total
labels) + printed number multiset -> (0) multiset equality => accepted-print (AKTU's
own table breaks the arithmetic); (1) print-stated columns must not be contradicted;
(2) unique invariant-gated repair from printed numbers only => fix-from-print.
SAFE-REPAIR policy: no L/T/P changes (contact-hour semantics); credit only to its
print-stated value; ct/ta only emptied (a print lacks the split entirely, never one
half); marks fields only to print-stated labeled values.

## Results (296 rows)
- 12 accepted-print — printed row == storage; the print itself breaks L+T+P/2 or the
  component sums (e.g. BCA labs print 0-0-3 with 2 cr; BPharm 2026-27 prints
  10|0|20 components) — kept faithful, flags upgraded with page-cited evidence.
- 15 rows / 31 field edits APPLIED (corrections_json before+after, page-cited):
  credit 3->4 x3 (OS/cloud/NLP: '3-1-0 / 4 cr' primary print vs stored 3 cr from an
  older 3-0-0/3cr era — §3 latest-wins); PS/TE labs x4 (ct/ta 50/50 emptied — print
  has no component split — sessional_total 100->50 per 'PS 50 + TE 50 / 100');
  ct/ta emptied x8 (print states only the sessional total; the 25/50, 10/10 splits
  were extraction inventions) — SESS_SUM resolves as print-lacks-split.
- 269 rows stay needs_review WITH probe notes: 198 no printed row recoverable
  (primary scheme docs missing post-reset / code-anchored row not found), 71 printed
  row found but numbers support no invariant-consistent repair, 0 ambiguous.
- Auditor upgraded: w9b_ckpt override block (actions/details updated, zero data change).

## Gates / push
G1 PASS, G2 PASS (6,412 owned codes), G3 PASS, G6 PASS (3 containment checks on
touched rows). T2T calls: 0 (deterministic; keys 5/5 untouched).
