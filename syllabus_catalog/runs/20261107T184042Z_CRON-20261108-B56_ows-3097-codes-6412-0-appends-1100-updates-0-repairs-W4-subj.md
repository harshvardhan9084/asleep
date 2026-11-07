# Task ID: CRON-20261108-B56

Agent: main (GLM) — owner-approved correction wave W4 (deterministic) + W3 addendum

Task: W4 subject_type normalization (129 raw variants → controlled vocab) + subject_name_display generation; W3b legacy co_kls string-format normalization to JSON arrays.

Work Log:
- W4: subject_type_norm populated on 2,509 subject rows across the 10-value controlled vocab (core 907, departmental-elective 735, lab 365, elective 130, practical 122, theory 116, open-elective 94, project-or-capstone 19, non-credit 11, value-added-mandatory 10); raw subject_type preserved verbatim (evidence); 570 rows remain unmapped/empty → TYPE_UNMAPPED/TYPE_EMPTY needs_review (zero-guess; name-based inference applied only for unambiguous -lab/-practical/-project suffixes: 596 rows). subject_name_display populated on 3,083 rows (clean segment of the multi-segment name_print history; code-prefix stripped; roman numerals uppercased; intermediate defect — first run rendered the raw multi-segment history — caught in verification and fixed before push).
- W3b: 293 legacy co_kls STRING values ('CO1:K1, K2;CO2:…') normalized to JSON arrays (multi-K per CO joined '/'; content unchanged; corrections_json entry each). 19 unparseable legacy values left verbatim for W7 (numbering gaps — zero-guess). co_kls now uniform JSON on 864 rows.
- G6 containment-gap handling (2 rows, process-equipment-design + environmental-science-and-ethics): unit1 not provable in any currently-resolvable cited doc (supplying doc lost to workspace resets, pre-G6 citation gap; corpus-wide scan of 613 PDFs found no containing print; cited 2009-10 doc prints a variant text 'to be used as material of construction' vs the row's 'used in') — rows left byte-identical to published, G6_CONTAINMENT_GAP needs_review recorded. Also 1 row auto-pruned in W3b by the same class.
- INTERIM NOTE: between the first (aborted) W4 run and this run the local CSV was accidentally restored from a pre-B55 backup; recovered by re-seeding from the PUBLISHED B55 state (work/repo_asleep/syllabus_catalog/ = GitHub durable record) — no data lost; this commit is B55+W4+W3b exactly.
- GATES (final): G1 PASS / G2 PASS codes=6412 / G3 PASS / G6 PASS checks=1471+230. Backups pre_commit_2026-11-07T183951p0000.csv / 184007p0000.csv.

Stage Summary:
- Registry 3097 × 63; subject_type_norm + subject_name_display now first-class columns; co_kls uniform JSON.
- Remaining waves: W5 (marks/credit per-row adjudication — 401 flags) and W3 REX leftovers (165 api_fail + 116 all-null) → wave runner via cron; W7 final re-audit + zero-known-error report.
