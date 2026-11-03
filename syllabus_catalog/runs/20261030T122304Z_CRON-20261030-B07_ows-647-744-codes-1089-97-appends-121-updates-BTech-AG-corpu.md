# Run manifest — CRON-20261030-B07 — batch 07 (BTech Agriculture Engineering corpus wave, 10 docs)

Task ID: CRON-20261030-B07 — Job 481578 — base: GitHub 93feccc (B06R state, 647 rows × 57 cols)

## Context (5th workspace reset recovery)

The 20:40 (2026-10-29) cron fire found the local workspace rolled back to the Oct-27 post-B02
snapshot AGAIN (5th reset: queue held only B01×2 + B02×6 done, repo clone lost, .env without PAT).
GitHub was ahead of every local state: B04 (189ba64), B04-repair (43cea6a), B05 (12819c8),
B06 CSV-recovery (93feccc, 647 rows) all published. Recovery BEFORE batch work (RULES §1c,
GitHub authoritative):
- .env rewritten with the owner-provided GITHUB_PAT (per cron directive)
- repo re-cloned → work/repo_asleep (HEAD 93feccc, 653 files; pipeline/ scripts + RULES §1b/§1c
  restored into scripts/pipeline_v2/ from the repo copy)
- download/art_d_final/syllabus_extreme_rich.csv restored FROM GitHub (647 rows × 57 cols)
- worklog.md B03/B04/B04R/B05/B06/B06R sections REBUILT from syllabus_catalog/runs/ manifests
- queue reconstructed to the B06R-published state: 37 rels newly marked done by sha16 citation in
  the published CSV, 2 failed(regulations-only) per the B04 manifest, batch_counter=6

## Batch (10 PDFs, all BTech Agricultural Engineering, 240 pages)

| # | doc | session | subjects |
|---|-----|---------|----------|
| 01 | btech_ag_y1_syllabus_2022-23 | 2022-23 | 18 |
| 02 | btech_ag_y2_model-curriculum_2019-20 | 2019-20 | 19 (6 detailed + 6 labs + 7 scheme-only) |
| 03 | btech_ag_y2_scheme-syllabus_2017-18 | 2017-18 | 21 (incl. 4 scheme-only) |
| 04 | btech_ag_y2_syllabus_2014-15 | 2014-15 | 16 |
| 05 | btech_ag_y3-4_syllabus_2009-10 | 2009-10 | 17 (print says 2nd Year III/IV Sem — print wins) |
| 06 | btech_ag_y3_scheme-syllabus_2020-21 | 2020-21 | 27 (15 DE electives all detailed + mini-project slot) |
| 07 | btech_ag_y3_syllabus_2018-19 | 2018-19 | 22 |
| 08 | btech_ag_y3_syllabus_2024-25 | 2024-25 | 30 (incl. BAG554 + BNC501/502/BNC601/602 scheme-only) |
| 09 | btech_ag_y3s5-6_scheme-syllabus_2015-16 | 2015-16 | 21 |
| 10 | btech_ag_y4_syllabus-cbcs_2019-20 | 2019-20 | 30 (incl. 4 assessment scheme-only; RAG085 pool-only → nsr) |

222 subjects drafted across the 10 docs; 40 non_subject_rows preserved (scheme totals, DE pools,
NC/MOOC rows, mini-project footnotes, annexure listings); ~110 quirks recorded (pacBAGing,
Evaulate K-legend, Martial Science, IndianTraditional, Verbatim typos kept per RULES §6).

## Pipeline events

- Subagent transport outage (environment-wide 403 "broken session") killed D03/D06/D08 extraction
  mid-run; incremental append preserved the partial disk state. Three repair waves then failed the
  same way, so the main agent completed D03/D06/D08 in-session (§7 incremental appends throughout).
- verify_draft.py: 8/10 PASS first run; 2 FAILs remediated with print evidence — D03's
  RVE301/RAS302/RME101/RCE151 marked scheme-only (no detail sections printed in the 18-page doc);
  D10's RAG753/RAG754/RAG851/RAG852 marked scheme-only (assessment rows) and RAG085 moved to
  elective_pool nsr (NPTEL pool-only item, same class as RAG091). Re-run: 10/10 PASS.
- merge_draft.py decisions: 221 plans (56 UPDATE / 162 APPEND / 3 SKIP); 14 flags + 5 TIEs
  adjudicated via 12 evidence-recorded TIER2_OVERRIDES + alternative_pair slot flags +
  pre-adjudicated COURSE-META-FROM-CODES / CROSS-COURSE-KEEP-SEPARATE / HISTORY-ONLY-CODE-MENTION /
  ALTERNATIVE-PAIR-SLOT / SCOPE-FROM-DOC classes.
- Live-commit TIE (08::16) root-caused to era-splinter appends; G6 FAIL root-caused to the workspace
  reset having orphaned the parses of 7 cited docs (AE 2018-19/2020-21/2024-25, AE y2 mc 2019-20,
  AG 2013-14/2016-17, AG course-structure 2026-27) — re-parsed those PDFs (md5-verified sha16s) so
  the citation chains resolve again. 5 same-course era-splinter rows converged via tier-3 RETARGET:
  RAG501+RAG551 (Irrigation & Drainage Engg. + Lab, 2018-19), NAG-651 (lab, 2015-16), RVE301/RVE401
  (BTech UHV), RAG454 (SWC Engg Lab) — one row per subject WITHIN BTech restored (RULES G1).
- Gates: G1 PASS / G2 PASS (codes 1089, course-scoped owners) / G3 PASS / G6 PASS (88 containment
  checks) → COMMIT OK rows 647→744, +97 appends / ~121 update plans, backup
  pre_commit_2026-10-30T122139p0000.csv. mark_done: 10 rels → done (55 total done, 399 pending).

## Registry deltas

rows 647→744; subjects 732 (BTech 437, BPharm 249, BCA 46); owned codes 1089 (G2);
row kinds: subject 732, semester_summary 8, elective_pool 2, program_rule 2.

## Flags adjudicated (recorded in merge_draft.py TIER2_OVERRIDES with full reasoning)

- Era-family ALLOWs: soft-skills (BAS105/205 → soft-skill-i KNC-101 lineage), workshop-practice-lab
  (BWS151/251 → multi-era row), Irrigation & Drainage Engineering (KAG-601, BAG601 → EAG-505 row),
  Engineering Properties of Biological Material (NAG-505 → ...-food-quality row), Tractor System &
  Controls (NAG-603 → tractor-systems-and-controls).
- Different-subject FORCE_APPENDs: Engineering Maths–III (fuzzy false positive vs Math-I/II),
  Remote Sensing and GIS Applications (BAG062 — kept separate from ACT's Remote Sensing and
  Applications BAC-052: overlap 27, distinct branch curricula, 'GIS' token).
- RETARGETs: Basic Electrical Engineering Lab (BEE151/251 → 2018-19 KEE-151P/251P row; the 2026-27
  AEE151C Electrical Engineering Lab row stays separate), plus the 5 tier-3 era-splinter
  convergences listed above.

## Open items (needs_review, per owner review)

1. 12 non-subject rows (pools/rules/semester summaries) still carry course_name "B.Tech" —
   pre-existing from earlier batches (visible in the GitHub baseline), untouched this batch.
2. Pre-existing B05-era near-duplicate pair heat-and-mass-transfer-lab (KME551;BME551;NBT-452,
   2020-21) vs heat-mass-transfer-lab (RME552, 2018-19) — same-course era splinter from the AE wave,
   not B07-caused; left untouched (flagged for a future repair run).
3. RAG652 (2018-19 "Post Harvest Engg. Of Horticultural...", no "Lab" printed) appended as its own
   row beside the EPAP theory/lab rows — the 2018-19 scheme prints it as a separate slot; zero-guess
   kept as printed.
4. 02 model-curriculum slot rows carry "trailing '50' column unresolved" needs_review flags (kept
   verbatim in draft quirks).
5. rr_sid remains owner-assigned at the very end.
