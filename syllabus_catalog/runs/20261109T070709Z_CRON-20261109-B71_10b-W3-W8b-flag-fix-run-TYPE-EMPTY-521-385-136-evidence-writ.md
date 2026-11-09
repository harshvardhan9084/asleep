# Run manifest — CRON-20261109-B71 (owner directive: fix the audit flags from now)

UTC: 2026-11-09T06:3x–07:1x · cron Job 512756 · workspace state: B70 (bfb5d5e) intact, no reset this run
Registry: 3,085 rows × 62 cols (schema v2.1) · audit flags 1,627 → **974** (−653) · flagged rows 1,323 → 784
G2 owned codes 6,412 before/after (zero data loss) · T2T 27 calls / 24 ok / 1 key_fail / 0×429 / 0 empty / 5 keys active

## W10b — TYPE_EMPTY 521 → 385 (136 evidence-backed writes)
Zero-guess ladder (every write carries corrections_json before/after + W10b rule + evidence + quality tag
corrected_W10B_TYPE_EVIDENCE + change_note + subject_type_norm mirror, RULES §6b):
- L1 own-recorded norm copy: 1 row ("The Department may conduct one Lab …" → practical)
- L2 name-print contact Lab/Laboratory/Workshop → lab: 101 (incl. 2 dual prints decided by committed precedent:
  'Software Project Management Lab', 'Mini Project Lab' → committed sibling carries lab, W9c recorded_copy class)
- L3 name-print contact Project/Seminar/Internship/Dissertation → project-or-capstone: 19 (W4 EXACT precedent)
- L4 name-print category: open-elective 3, departmental-elective 4 (incl. 'DEPTT. Elective I'), elective 8
  (scheme slot prints: textile-era 'Elective N …' pairs + MCA ELECTIVE-I/II/III)
- HONEST NO-WRITE: 381 rows with no name-print evidence (L/T/P alone cannot decide — committed L-dominant rows
  carry theory/core/DE alike) + 4 'HSMC Audit Group' rows (no codes, no committed audit-group precedent).
  Both stay flagged for the W10c corpus page-read wave.
- G6 containment-gap pre-existing rows (process-equipment-design, environmental-science-and-ethics) NOT touched —
  corpus-wide probe over 610 PDFs (norm_al containment, junction-tolerant) = 0 hits → no citation-widening remedy;
  deferred to W10c page-image evidence. Their 2 DISPLAY_MISSING flags ride along (stay honest).

## Audit v19 (audit_rules.py)
- CONTROLLED_TYPES aligned to the W4 controlled vocab (owner-reviewed B56): +project-or-capstone, +non-credit —
  W10b's 19 proj writes were flagged TYPE_RAW by the stale 8-value subset; vocabulary inconsistency, not data error.
- KLS recorded-honest semantics: rows carrying kls_not_printed (text/OCR probe-confirmed no printed CO/K table)
  are no longer flags (same evidence-not-error class as the None entries); kls_raster_candidate (unprobed) keeps
  needs_review; untouched rows keep fix:W3.

## W3 — KLS 517 flags → 0 (all evidence-recorded, zero data guesses)
- Deterministic text-layer scan (corpus 610 PDFs, checkpoint-resume): wins=0, rex_queue=22, not_printed=495.
- w3_rex_prompt.md restored (lost in a workspace reset, never committed) — rebuilt per W3 REX semantics, zero-guess.
- mercury-3 REX over the 22: first pass all-null (parse contract rejected printed K-RANGES) → parse fixed to the
  W8a-legitimate range form K[1-6](/K[1-6])* (22 results reset + re-run, documented in-code); re-run verdict: all
  22 rows have NO printed K-assignment in any cited page (mercury honestly null, payload pages are unit text).
- 22 rex rows tagged kls_not_printed with the zero-null verdict note (w3_kls_apply all-null branch added).
- 495 scan not_printed rows already tagged (B55) — audit v19 clears their flags.

## W8b — OCR page-image evidence over the 12 raster-candidate rows
- w8b_kls_ocr target selection extended to the audit-v19 needs_review raster rows (CSV-tag direct scan).
- Probe: 12 targets, 109 raster pages OCR'd (tesseract psm6, persistent per-(sha,page) cache) → found=0 —
  no recoverable printed CO/K sequence in any image. w8b_ocr_null_tag.py (new) records kls_not_printed +
  probe-evidence note on the 12 rows; gates PASS.

## Toolchain fixes shipped with this run
- wave_commit.refresh_flags_consumed: dict-changed-size-during-iteration crash fixed.
- audit_rules v19 (above). w3_kls_rex parse-contract fix. w3_kls_apply +rex_null branch.
- w8b_kls_ocr target patch. New: w10b_type_evidence.py, w8b_ocr_null_tag.py, w3_rex_prompt.md (restored).

## Gates (final state, per wave_commit run_gates)
G1 PASS (62-col v2.1) · G2 PASS codes=6412 · G3 PASS · G6 PASS — on every W10b/W3/W8b commit.
Push: CRON-AUTO-B71 via push_catalog.sh (CSV + CHANGELOG + this manifest + pipeline toolchain).

## Remaining 974 flags (all honest, evidence paths documented)
TYPE_EMPTY 385 (W10c corpus page reads) · BOOK_TRUNC 169 · CREDIT_FORMULA 139 / SESS_SUM 125 / MARKS_SUM 122
(W5 faithful-print-vs-fix adjudication, scheme-line evidence) · TOKEN_N_LOWER 26 · BOOK_MERGED 6 ·
DISPLAY_MISSING 2 (rides with the G6-gap rows). Zero-guess: no fix without new print evidence.
