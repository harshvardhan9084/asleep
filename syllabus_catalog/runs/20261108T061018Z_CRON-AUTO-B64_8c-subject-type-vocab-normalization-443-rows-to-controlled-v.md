# Batch CRON-AUTO-B64 — W8c subject_type vocab normalization (2026-11-08)

Owner go: "Continue with both" (= W8b + W8c, answering "Shouldn't we work on audit results?").

## Scope

W7 re-audit class `TYPE_RAW` (514 rows: raw `subject_type` outside the 8-value
controlled vocab). Zero-guess discipline: applied values only from (a) the row's own
pre-recorded `subject_type_norm` (prior committed waves, owner-reviewed through B63),
(b) owner-sanctioned literal mappings, (c) print-token decisions already recorded on
committed rows. `subject_category_print` untouched (verbatim print preserved).

## Applied — 443 rows, 443 edits

| Rule | Mapping | Rows |
|---|---|---|
| W4/TYPE_NORM_RECORDED | copy recorded `subject_type_norm` → `subject_type` | 429 |
| W4/TYPE_NORM_OWNER_LAB | laboratory/workshop → lab | 7 |
| W4/TYPE_NORM_PRINT_BSC | 'Basic Science Course' phrase → core | 6 |
| W4/TYPE_NORM_PRINT_VA | print 'VA' → value-added-mandatory | 1 |

Every write carries corrections_json {field, before, after, rule, evidence, wave:"W8c"}
+ quality_flags tag + change_note seg (RULES §6b). `subject_type_norm` kept in sync.

## Left flagged — 71 rows (35 distinct raw values)

Documented in `work/pipeline_v2/w8c_decision_memo.json` (PES, PEC, NCMC, MDC, IPR, SEC,
SDC, departmental, scheme-only, activity-assessment, humanities, remedial, camp, …).
These have NO recorded decision and NO owner sanction → stay TYPE_RAW needs_review
(zero-guess: no print-evidence-based guess permitted).

## Gates

G1 PASS / G2 PASS codes=6412 / G3 PASS / G6 PASS checks=327 (pre_edit_hits=[]; prior
OCR/verification evidence records honored; zero deferrals).

## Transparency

Deterministic wave: 0 T2T calls, 0 mercury usage, 5/5 keys untouched, no image reads.
Working CSV == repo CSV md5 e94d2ed5… before batch; backup pre_commit_*.csv retained.
