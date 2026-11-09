# Manifest — CRON-20261110-B74 — W10c TYPE_EMPTY corpus round + durable notes

## Context
- Reset #58 on entry (1h after B73): routine restore executed (.env 7 vars, repo @e542231 B73, CSV md5 53343e76 verified, toolchain 441 files, corpus_map 613→610 shas, wave_state batch_next=74). The B73 durability fix paid off immediately: w9a_ckpt.json restored from repo runs/ (168 verdicts) and the 127 durable W9a2 note rows were in the CSV — zero evidence lost.
- wave_runner --loop: NOOP (W3 queue 0; 0 T2T calls). Flag-repair mission continued at 923 flags / 763 rows.

## W10c — TYPE_EMPTY 385 (the class W10b deferred to corpus page reads)
- probe (w10c_scheme_probe.py, deterministic fitz text layers, cited docs first): per row, locate the printed scheme row of primary_code; govern by the nearest STANDALONE category section header above the code line (tight grammar; acronym forms like OEC/DE-I never match; title-text words cannot match).
- Two grammar defects found and fixed during verification (zero-guess held — nothing written until reproduction was clean):
  1. "Department Elective-<slot>" (printed form) did not match the DE regex → codes fell back to generic "Elective-<n>" headers (mis-class elective). Fixed: DE regex accepts slot suffixes.
  2. Reproduction harness initially used raw-code-only search (hyphen/space variants missed) — fixed; final verification: 31/31 same-page verdicts reproduce exactly.
- Verdicts (385): print_category 31 (same-page governing header) / cross_page_section 36 / no_header_above 178 / no_code_print_found 140.

## Apply (w10c_apply.py)
- WRITES only for the 31 print_category rows → subject_type ∈ {elective 18, departmental-elective 10, open-elective 3} (per-row split in corrections_json). Each write: corrections_json {before:'',after:<cat>,rule:TYPE_EMPTY,evidence:<file#sha p.N>,wave:W10c} + verification_status=corrected + corrected_W10C_CATEGORY tag + subject_type_norm mirror + change_note + notes marker.
- cross_page_section deliberately NOT written: doc-continuity demonstrated unsafe on textile-era schemes (cores listed pages after unrelated section headers, e.g. ETEF-304 wet-processing). Honest flags kept.
- Durable "W10c probe:" notes on all 385 targets (idempotent) — probe evidence survives resets; ckpt committed to syllabus_catalog/runs/w10c_ckpt.json.

## Result
- Flags 923 → 892 (TYPE_EMPTY 385 → 354 = exactly the verified writes); flagged rows 763 → 732.
- Gates G1/G2(6,412)/G3/G6 PASS; rows 3,085 × 62 v2.1; CSV md5 53343e76… → 06f83f59374d83e255c0f23a7100b9d0; diff scope verified cell-by-cell: only subject_type / subject_type_norm / corrections_json / verification_status / quality_flags / change_note_vs_previous / notes.
- T2T: 0 calls (deterministic local text-layer reads only; mercury keys idle).

## Remaining flag classes (892)
TYPE_EMPTY 354 (probe-noted: 140 no_code_print_found + 178 no_header_above + 36 cross_page), BOOK_TRUNC 144, CREDIT_FORMULA 139, SESS_SUM 125, MARKS_SUM 122, BOOK_MERGED 6, DISPLAY_MISSING 2. Next candidates: W9b round-2 scheme probes (CREDIT_FORMULA/SESS_SUM/MARKS_SUM 386), W10c global-index fallback for the 140 no_code_print_found rows.
