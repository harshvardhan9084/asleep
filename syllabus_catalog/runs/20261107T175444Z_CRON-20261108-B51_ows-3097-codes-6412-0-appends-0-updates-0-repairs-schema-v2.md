# Task ID: CRON-20261108-B51

Agent: main (GLM) — owner-directed correction wave (Phase 1 D2, interactive turn)

Task: Schema v2 bump — owner decisions D1/D2/D3 (2026-11-08): RULES §6b verbatim-vs-fix amendment; add 6 new columns (subset of the audit's Part 2 proposal); record wave-list approval. Wave order per owner: W1 typos → W2 books → W3 co_kls → W4 type/display → W5 marks → W6 artifacts → W7 re-audit (W1/W2/W6 deterministic, no T2T; W3 heavy T2T).

Work Log:
- PHASE 1: RULES.md §6b added (primary fields FIXED; print forms stay in *_print/source_scheme_line/quirks; every correction records {field,before,after,rule,evidence} in corrections_json + quality_flags; corrections need page-cited print or authoritative reference evidence; zero-guess unchanged; needs_review when inconclusive). §5 G1 updated to the 63-col reference header. merge_draft.py REF_HEADER bumped to v2 (single source of truth).
- SCHEMA V2 (6 cols appended, order per REF_HEADER): subject_name_display (W4 fills), subject_type_norm (W4), quality_flags (machine flags), corrections_json (D1 verbatim-vs-fix ledger), code_family (derived prefix), verification_status (unreviewed/reviewed_clean/corrected).
- PHASE 2: scripts/pipeline_v2/audit_rules.py built (deterministic per-row flag engine extending claude_audit_scan.py; each flag = fix:<wave> or needs_review). Full scan: rows=3097 flagged=3085 flags=10390 — PUNCT_ARTIFACT 3372, DISPLAY_MISSING 3085, KLS_MISSING 1361 (=W3 size), BOOK_TRUNC 574 (heuristic, needs_review), TYPE_EMPTY 521 + TYPE_RAW 514 (=W4), BOOK_SPACECOMMA 314, BOOK_NUMART 180, CREDIT_FORMULA 142 / SESS_SUM 133 / MARKS_SUM 126 (=W5, needs_review by design), TOKEN_N_LOWER 26, AUTH_TYPO flags per term (trembley 9, warshal 7, deshpandey 5, dijikstra 4, vravice 4, liptschutz 3, parahami 2), BOOK_MERGED 6, MATH_ITALIC 2. Flags saved to work/pipeline_v2/audit_flags.json.
- B51 COMMIT: 57→63 cols; quality_flags populated on 3097 rows; code_family on 1918 rows; verification_status=unreviewed/reviewed_clean initial state; corrections_json empty. Gates: G1 PASS (v2) / G2 PASS codes=6412 / G3 PASS / G6 PASS (0 touched). Backup pre_commit_2026-11-07T175419p0000.csv.

Stage Summary:
- Registry: 3097 rows × 63 cols (schema v2). No field values altered — additive only.
- Open: W1 (B52) dictionary typos w/ page-cited evidence; W2 (B53) book hygiene; W6 (B54) artifacts; W3 (B55+) co_kls backfill 1,361 rows (deterministic K-extraction first, mercury-3 REX for the rest); W4/W5 follow; W7 re-audit → zero-known-error report.
- Cron note: hourly job 509551 found DISABLED by API ("; Disabled by API") — recreation with wave-runner payload follows the deterministic waves.
