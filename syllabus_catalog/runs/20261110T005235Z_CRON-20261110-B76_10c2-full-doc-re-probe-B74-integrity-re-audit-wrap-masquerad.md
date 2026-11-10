# Manifest — CRON-20261110-B76 — W10c2 full-doc re-probe + B74 write integrity re-audit

## Context
- Reset #59 (second pass this morning): routine restore executed (.env 7 vars, repo @dfe4a40 B75, CSV md5 7b73a07e verified, toolchain 346 files, corpus_map rebuilt 613→610 shas matching B75 manifest, wave_state batch_next=76; w9a/w10c ckpts + w9b_adjudication restored from repo runs/). Loop: NOOP (W3 queue 0; 0 T2T).

## W10c2 — full-document re-probe of the 354 non-written TYPE_EMPTY rows
- B74 stopped at the FIRST page hit per cited doc; this wave scans ALL pages of ALL cited docs (source_syllabus/source_history shas only — zero cross-doc writes), same tight same-page governing-header grammar.
- Initial probe: 3 print_category. Manual reproduction exposed a NEW grammar failure class: **wrap-masquerade** — wrapped name-cell fragments ("Science Based / Open Elective" p.3 carpet-textile 2017-18; "Open / Elective/" p.44 textile-chem 2009-10) match the header regexes but are subject-name cell tails, not section headers.
- Grammar tightened (gap ≤ 8 printed lines + wrap-continuation rejection via WRAP_WORDS prev-line vocabulary); re-probe: 1 print_category (fabric-structure-design-analysis BTT051 → departmental-elective, clean "Departmental Elective I" header directly above the code, btech_textile-tech_y3_syllabus_2024-25.pdf p.7), 213 no_header_above, 140 no_code_print_found — all honest, page-cited.

## B74 integrity re-audit (the 31 committed corrected_W10C_CATEGORY rows)
- All 31 re-verified under the tightened grammar + three new discriminators: (a) wrap-continuation of the claimed header line; (b) scheme-table COLUMN-HEADER block between claimed header and code (header governs a different table — the elective bullet-list-then-table pattern, KTT503/KTT50x model-curriculum 2020-21 class); (c) semester break between.
- Verdicts: **22 REVERT** (18 wrap-masquerade: "Departmental / Elective-II" name-cell tails on 2009-10 textile-chem pages misread as section headers; 4 column-header/semester-break: KTT503 chemical-processing-of-textiles, textile-design-colour, KTT603 advance-weaving-technology, BMI55x startup-...-mca), **9 KEEP** (sub-header inside one table: MCA-413 fundamentals-of-e-commerce, advances-in-chemical-processing OPEN-ELECTIVE course-2 row, eoe405, 2009-10 Elective slots passing all discriminators).
- Reverts: subject_type → "" + verification_status=needs_review + corrections_json {before,after:"",rule:TYPE_EMPTY_REVERT,evidence page-cited reason} + reverted_W10C_B76 tag + change_note + durable "W10c2 reaudit:" note. Keeps: durable reaudit note only (no field change).
- Zero-guess held: no verdict written without page-level print evidence; inconclusive reads stay empty/flagged.

## Result
- Flags 879 → 900 (TYPE_EMPTY 354→375: −1 written +22 reverted to honest empty); flagged rows 720→741. The +22 is the honest re-flagging of B74's over-reach, not new errors.
- Gates G1/G2(6,412)/G3/G6 PASS (G6 probes the 23 field-changed rows only — the B74/B75 notes-are-not-content convention); rows 3,085 × 62 v2.1; CSV md5 7b73a07e… → c52f7d5de83e0569f770f50bce38b3f9; diff verified cell-by-cell: 69 field cells across exactly 23 rows + 454 note cells, 0 out-of-scope cells.
- w10c2_ckpt.json + w10c2_reaudit.json committed to syllabus_catalog/runs/ (reset-proof).
- T2T: 0 calls (deterministic local text-layer reads; mercury keys idle).

## Remaining flag classes (900)
TYPE_EMPTY 375, BOOK_TRUNC 144, CREDIT_FORMULA 129, SESS_SUM 123, MARKS_SUM 121, BOOK_MERGED 6, DISPLAY_MISSING 2. Next candidates: BOOK_TRUNC/BOOK_MERGED OCR rounds (page-image reads), TYPE_EMPTY page-image rounds for the 140 no_code_print_found, DISPLAY_MISSING 2.
