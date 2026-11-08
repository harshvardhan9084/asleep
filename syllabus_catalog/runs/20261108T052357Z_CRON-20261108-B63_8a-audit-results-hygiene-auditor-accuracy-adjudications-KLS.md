# Task ID: CRON-20261108-B63 (W8a — owner-interactive audit-results wave, 2026-11-08)

Trigger: owner asked "Shouldn't we work on audit results?" — this wave works the
W7 re-audit leftovers that are adjudicable WITHOUT new page-image evidence.

## What was done

1. Auditor-accuracy adjudications (audit_rules.py upgraded; zero data change):
   - KLS_BADVAL 140→0: every residual flag was a printed K-range ("K1/K2" =
     doc prints K1 or K2) or a recorded honest null (W3 partial backfill).
     Rule now accepts K1-K6 tokens, slash-ranges, and None entries.
   - AUTH_TYPO_warshal FP guard: the matcher used unguarded 'Warshal'
     substring search which matched INSIDE correctly-spelled 'Warshall' —
     5 of 7 flags were false positives. Word-bounded pattern now
     (\\bWarshal\\b|\\bWarshalll\\b).
   - BOOK_NUMART 33→~0: 32 of 33 residual flags were legitimate volume/year
     statements ("Vol. 1. Pearson", "2007-08."). Rule now matches entry-start
     list numbering only.
2. Real data fixes (RULES §6b; corrections_json before+after, quality_flags,
   change_note; 24 edits total across 11 rows):
   - W1 leftovers: 'Warshalll'→'Warshall' ×2 (xrow: correct print on 5+ rows);
     'BehroozParahami'→'Behrooz Parhami' ×1 (spelling + fused-space);
     'Geoftrey'→'Geoffrey' ×1 (NEW dictionary term; xrow: 'Geoffrey' correct
     on 15 rows — Geoffrey Gordon, System Simulation, PHI).
   - W2 leftovers: 20 entry-start numbering strips ('8.process control…',
     '1.Bovee&Thill…', '3.. Bowersox…', '2) Comer…' — before-forms preserved).
   - W4 leftovers: 2 DISPLAY fills were attempted but DEFERRED — both rows
     (process-equipment-design, environmental-science-and-ethics) are members
     of the documented G6 containment-gap class: their unit1 text does not
     resolve in the cited docs' text layers (probed directly in the PDFs:
     btech_che_y2-4_syllabus_2009-10.pdf, mca_syllabus_2008-09.pdf — real
     gaps, not parse-cache misses). The wave auto-reverts any row that would
     fail G6 and defers it to the page-image evidence wave (zero-guess).

## Result

- Registry: 3097 rows × 63 cols; gates G1 PASS / G2 PASS codes=6412 / G3 PASS
  / G6 PASS; fresh audit flags 6025→5844 (−181); remaining classes are
  evidence-read classes (KLS_MISSING 514 raster candidates, BOOK_TRUNC 574,
  CREDIT/MARKS/SESS 401 scheme adjudications, TYPE_RAW 514 vocab decision,
  BOOK_MERGED 6, KLS_SHORT 5, TOKEN_N_LOWER 26) and accepted-print classes
  (PUNCT_ARTIFACT 3281 guarded, TYPE_EMPTY 521 honest nulls).
- Queue: 434 done / 0 pending / 14 failed; enqueue no-op.
- T2T: none (deterministic wave; mercury untouched this run).

## Next (proposed W8b/W8c, pending owner go)

- W8b page-image evidence reads: 514 KLS raster candidates + 574 BOOK_TRUNC
  print-ends + 401 scheme adjudications + 2 G6-gap rows (the deferred DISPLAY
  fills ride along once containment resolves) + 6 BOOK_MERGED splits.
- W8c TYPE_RAW vocab mapping: 514 raw strings, top = summary/departmental/
  scheme-only/laboratory/activity-assessment/BSC/PES/NCMC/MDC — needs an
  owner decision on target vocab entries; unambiguous ones (laboratory→lab,
  workshop→lab) could auto-apply, the rest stay flagged.
