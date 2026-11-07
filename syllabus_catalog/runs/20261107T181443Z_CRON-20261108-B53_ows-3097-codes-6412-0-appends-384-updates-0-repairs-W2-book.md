# Task ID: CRON-20261108-B53

Agent: main (GLM) — owner-approved correction wave W2 (deterministic, no T2T)

Task: W2 book-entry hygiene: split merged print entries, strip embedded numbering artifacts, space-comma normalization, per-print truncation review (RULES §6b; before-forms in corrections_json).

Work Log:
- 902 edits: BOOK_SPACECOMMA ×410 (' , ' → ', '); BOOK_MERGED_SPLIT ×4 (true two-entries-in-one-print-line merges: discrete-structures-and-theory-of-logic Tremblay|Deo; structural-analysis Thandavmorthy|Wilbur-Norris; automotive-pollution SAE|Obert; automotive-electrical Grouse|Judge — each renumbered sequentially); BOOK_NUMART strip ×488 (embedded list-numbering tokens, guards for Vol./Volume/No./ISBN/year-ranges); BOOK_TRUNC same-print-line review: 46 verified print-ends-here (flag → reviewed_print_ends_here), 0 extensions (rigorous normalized-prefix model — an earlier loose extension pass produced 53 corrupted entries and was REVERTED from backup before commit; no corrupted data shipped); ~525 entries remain BOOK_TRUNC needs_review (honest).
- BOOK_MERGED false positives: 5 semicolon-style author prints re-flagged reviewed_semicolon_style; 1 print block ('From pages 20-21:' multi-item list, pharmaceutics-viii) flagged reviewed_book_block (never split — zero-guess).
- G6 evidence remedy (B12 class, page-image verified): human-values-professional-ethics unit1..unit5 transcribed from raster pp.14-22 of btech_y2_common-subjects-syllabus-rev_2014-15.pdf#d32696e27932336c (text layer empty there); page-image spot-check p.15 verified unit1 verbatim → recorded note unblocks the gate's OCR_PRIOR_SKIP path.
- Two intermediate defects caught by self-review and fixed BEFORE push (revert+rerun ×2): (1) case-insensitive 'House' matched inside 'Warehouse' causing a false mid-title split (business-intelligence Kimball entry) — PUB_TAIL now word-boundary guarded; (2) two-digit absorb in the split loop. All 6 split/strip results re-verified post-fix; JSON columns parse clean (0 errors).
- GATES: G1 PASS / G2 PASS codes=6412 / G3 PASS / G6 PASS checks=342. Backup pre_commit_2026-11-07T181407p0000.csv.

Stage Summary:
- Registry 3097 × 63; 902 deterministic edits; T2T calls this wave: 0.
- Next: W6 artifacts (B54) then W3 co_kls backfill (deterministic K-scan → mercury-3 REX for leftovers).
