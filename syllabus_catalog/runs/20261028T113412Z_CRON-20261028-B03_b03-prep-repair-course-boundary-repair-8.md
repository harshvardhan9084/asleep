# Run manifest — CRON-20261028-B03 — batch B03-prep-repair — 2026-10-28T11:34:12Z

Summary: course-boundary repair: 8 BTech rows reverted from BCA contamination (RULES 1b), 87 rows course-canonized, ladder hardened, tracking now GitHub-referenced (RULES 1c)

Registry deltas: rows 196→196, subjects 184→184, codes 270→263; by course: B.Tech 87→0, BCA 22→22, BPharm 40→40, BTech 35→122

---

# Repair narrative — RULES §1b course-boundary violation (owner directive 2026-10-28)

Task ID: CRON-20261028-B03 (prep phase) — trace 1a1823ada687a185

## What the owner flagged (verbatim)

1. "you are losing tracking the changes of each run. make it github referenced."
2. "maybe you are saying that you merged some BCA subjects into B.Tech - but both
   courses could contain very similar subjects, but the course boundaries are
   real, you should not merge them."
3. "decrease the interval of cron job to 'every 1 hour'"

## Findings (all evidence-backed, zero-guess)

- The 2026-10-28 18:30 cron run ingested 5 corpus docs (bpharm_y1-2_2013-14,
  bca_y1_2024-25, bca_y1_2025-26, bca_y2_2025-26, bca_s1-2_bbc107-207 bridge)
  and pushed commit 8cabc73 (196 rows, 62 appends, 8 corrupting updates) — then
  the workspace reset wiped the local CSV/queue/drafts; GitHub held the only
  copy. Confirms the owner's tracking complaint; §1c now makes GitHub the
  durable record (CHANGELOG.md + runs/ + pipeline/ + structured commit messages).
- Cross-course corruption CONFIRMED: 8 BTech rows absorbed BCA draft content
  (data-structure, data-structure-lab, operating-systems,
  technical-communication, universal-human-values-and-professional-ethics,
  web-technology, web-technology-lab, digital-electronics) — 13-29 fields each
  overwritten (units, COs, marks, all_codes, code_history, subject_name_print);
  6 BBC* (BCA bridge) codes landed inside BTech all_codes. Root cause: the
  ladder trusted draft course metadata (BCA docs mislabeled BTech) and Tier-0
  had no course precondition; newer-session fieldwise wins then let BCA
  2024-25/2025-26 text replace BTech text.
- Course-name canon split (pre-existing): 87 rows 'B.Tech' vs 35 rows 'BTech'
  (B01/B02 appends wrote the queue's course string verbatim).

## Repairs applied (scripts/pipeline_v2/repair_course_boundary.py)

- Reverted the 8 corrupted BTech rows wholesale to the last clean verified
  state (commit 613ad63 = B02-verified); each row's change_note_vs_previous
  records the revert + reason.
- Canonized course_name to RULES §1b canon on all 87 'B.Tech' rows (BTech),
  each with a recorded change note.
- Sanity: zero BBC*/BOP* tokens left in BTech rows (contamination fingerprint
  check), gates G1/G2/G3 re-run PASS (303 owned codes, each in exactly one row).
- The 62 appended rows (BPharm 40 + BCA 22) verified clean: BPharm/BCA-only
  sources, correct courses — kept.

## Hardening (this run, permanent)

- RULES.md §1b (HARD RULE: never merge/update across courses; canon course
  names; crossref notes instead), §1c (GitHub-referenced tracking), §2 ladder
  guards on Tier 0/1/2, §3 cross-course carve-out REMOVED, §11 prohibitions.
- merge_draft.py: canon_course() everywhere; course_from_codes() — printed
  codes OVERRIDE mislabeled draft course meta (the corruption's root cause);
  hard course guard on Tier 0/1/2; CROSS-COURSE-KEEP-SEPARATE +
  COURSE-META-FROM-CODES adjudications; G3 now rejects non-canon course names.
- Queue reconstruction: 5 docs restored from 8cabc73 provenance; bpharm done;
  4 BCA docs pending-pinned for §1b-compliant re-draft (the reverted BCA
  subjects re-ingest as proper BCA rows).
- enqueue_corpus.py: the whole 5-course repo corpus (asleep) idempotently
  enqueues as pending so every hourly run has deterministic work.

## Cron

- Job recreated at hourly cadence per owner instruction (was 2-hourly).

