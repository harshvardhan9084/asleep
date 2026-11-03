# Run manifest — CRON-20261028-B03 — batch B03 — 2026-10-28T12:07:17Z

Summary: BCA re-ingestion per RULES 1b: rows 196→204, codes 303→310, +8 BCA subject rows (course-boundary crossrefs), ~39 BCA updates, BBC102 code-ownership transfer adjudicated, G2 now course-scoped

Registry deltas: rows 196→204, subjects 184→192, codes 263→270; by course: BCA 22→30, BPharm 40→40, BTech 122→122

---

# Run manifest — CRON-20261028-B03 — batch 03 (BCA §1b-compliant re-ingestion)

Task ID: CRON-20261028-B03 — trace 1a1823ada687a185 — owner directives executed this run:
course boundaries are real (§1b) + GitHub-referenced change tracking (§1c) + hourly cron.

## Context

The B03-prep phase (same run, pushed earlier as c190219) reverted the 8 BTech rows
the 18:30 run had corrupted with BCA content, canonized 87 course names, hardened the
ladder, and established CHANGELOG.md + runs/ + pipeline/ tracking. This phase
re-ingests the 4 BCA docs with correct course metadata so the previously-merged-away
BCA subjects become proper BCA rows.

## Batch (4 PDFs, all BCA)

- 2024-25/bca_y1_syllabus_2024-25.pdf (19pp) — 15 subjects
- 2025-26/bca_y1_syllabus_2025-26.pdf (20pp) — 16 subjects (incl. scheme-only BBC107/BBC207 record)
- 2025-26/bca_y2_syllabus_2025-26.pdf (39pp) — 15 subjects
- 2025-26/bca_s1-2_bbc107-207-non-credit-bridge-course_2025-26.pdf (2pp) — 1 subject

## Drafts → verify

- 47 draft subjects total; all 4 subagents returned clean, incremental writes verified.
- verify_draft first run FAILed 1 stem: BVA251 Sports and Yoga 'no units' — page print
  shows the non-credit subject's syllabus as "Part A: Sports/Games" / "Part B: Yoga"
  (no Unit-I..V headings). Remedy: verbatim Part A/B keyed as units 1/2 in both y1
  drafts (scripts/pipeline_v2/patch_bva251_units.py); re-run 4/4 PASS.

## Merge (live ladder, RULES §1b/§2)

- PLANS 47: 39 UPDATEs (all WITHIN course BCA — Tier-0/1 code/name identity vs the 22
  existing BCA rows; newer-session 2025-26 content fieldwise-wins), 8 APPENDs (the
  subjects the 18:30 run had merged into BTech rows: data-structure, data-structure-lab,
  digital-electronics, web-technology, web-technology-lab, operating-systems,
  technical-communication, universal-human-values-and-professional-ethics), 0 TIE, 0 SKIP.
- 8 CROSS-COURSE-KEEP-SEPARATE flags — every append carries the §1b crossref note naming
  its BTech twin; the BTech rows were never touched (verified post-commit: the 4 sampled
  reverted rows still carry clean BTech unit text, zero BBC tokens).
- COURSE-META-FROM-CODES defense active: printed codes override draft course metadata.

## New adjudications (recorded in merge_draft.py RESOLVE_APPEND, all evidence-backed)

1. CODE-REASSIGNED-ACROSS-SESSIONS — BCA y1 print evidence: BBC102 = Mathematical
   Foundation in 2024-25 but = INFORMATION SYSTEMS in the 2025-26 heading print (the
   2025-26 scheme table prints BBC106 for Information Systems; BBC205A for Mathematical
   Foundation). Deterministic resolution: name identity wins, code ownership transfers
   to the newest print, the older row keeps a narrative history mention and follows the
   status=latest primary-code model. Applied: mathematical-foundation primary BBC102 →
   BBC205A (all_codes 'BBC205A'; BBC102/BBC106 → narrative), information-systems
   gains BBC106 (+BBC102 heading-alias).
2. Tool fixes with recorded reasoning: course_from_codes infers ONLY unambiguous
   prefixes (generic B??/K?? families are REUSED across courses — the first version
   wrongly inferred BTech from BVE301/BVA251 and would have re-corrupted rows);
   per-subject course_eff (no shared-dmeta mutation leak); G2 ownership is COURSE-SCOPED
   (BVE301 UHV printed in both BTech and BCA schemes — one owner per course; RULES §5
   updated); append subject_id collision suffixing (-bca) for global G3 uniqueness.

## Gates + commit

- G1 PASS (57 cols), G2 PASS (course-scoped, 310 distinct codes), G3 PASS, G6 PASS
  (containment 22). COMMIT OK rows 196 → 204 (appends 8, updates 39).
- Backup: work/pipeline_v2/backup/pre_commit_2026-10-28T120614p0000.csv.
- Independent postcommit_verify: 204 rows, census BTech 122 / BCA 30 / BPharm 40,
  JSON columns clean, 17 branches, zero BBC tokens in BTech rows.

## Queue + corpus

- 4 rels marked done; enqueue_corpus added the remaining 443 repo PDFs as pending
  (BTech 352, MBA 50, MCA 25, BPharm 15, BCA 1) — hourly batches now have a full work
  queue (md5-deduped at selection).

## Open items

- (1) BCA y1 2024-25's BBC251 Data Structure Lab has no detailed syllabus in that doc —
  the 2025-26 doc supplied it (row data-structure-lab-bca updated); recorded in notes.
- (2) BVA251/BVA451 marks cells print blank/zero variants (non-credit) — kept as printed.
- (3) draft-02's BBC106-vs-BBC102 heading/scheme mismatch is documented in both affected
  rows' change notes + quirks (owner may eyeball pp.2/13 of the 2025-26 doc).
- (4) 443-doc pending queue: ~45 hourly batches to full 5-course coverage.

