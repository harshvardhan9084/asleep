# Run manifest — CRON-20261029-B06-recovery — batch 06R (B06 CSV-recovery re-run: AE y4 ×3 + AG ×7)

Task ID: CRON-20261029-B06-recovery — Job 481578 — base: GitHub 2d7a5ec (CSV at B05 state, 526 rows × 57 cols)

## Why a recovery re-run (publish-integrity incident)

The 13:48 cron fire found the local workspace rolled back to the post-B02 snapshot (4th reset:
queue held only B01×2 + B02×6 done, repo clone lost, .env without PAT, RULES §1b/§1c and
push_catalog.sh + enqueue_corpus.py missing). GitHub was ahead of every local state — and one
step AHEAD OF ITSELF:

- B04 (CRON-20261028-B04, 189ba64), B04-repair (43cea6a), B05 (CRON-20261028-B05, 12819c8,
  526 rows) all completed and pushed by prior sessions.
- **B06 (CRON-20261029-B06, commit 2d7a5ec) shipped ONLY CHANGELOG.md + the runs/ manifest —
  the updated syllabus_extreme_rich.csv NEVER landed** (`git show 2d7a5ec --stat` = 2 files).
  B06's claimed 526→648 (+122 appends/~57 updates + 74-row baseline G2/G3 repair) was lost with
  that session's workspace. The published catalog CSV remained at the B05 state.

Per RULES §1c (GitHub CSV = authoritative baseline) the correct action is to RE-DERIVE, not to
skip: B06's 10 docs were re-selected and re-processed so the catalog rows actually reach GitHub.

## Recovery BEFORE batch work

- .env rewritten with the owner-provided GITHUB_PAT; repo re-cloned (649 files, HEAD 2d7a5ec).
- CSV baseline restored from GitHub into download/art_d_final/ (526 data rows × 57 cols verified).
- All pipeline scripts synced from the repo's published pipeline/ directory; push_catalog.sh
  rebuilt locally (was never pushed); verify_draft.py re-patched with the B06-documented v10
  remedies (they lived only in the lost session): running-header/weightage-cell haystack strips,
  compound-code parsing both sides ('KMC 101/201', 'KAS- 154P', 'NCE-151/251' → atomic codes),
  non_subject_rows GAP exemption, no-code-lab downgrade, plus a v10c bigram order-tolerance
  fallback for scheme-table cell interleaving (fabrication-resistant: every word pair must be
  genuinely printed; digit cells excluded as provenance).
- Queue reconstructed from the GitHub runs manifests + sha16 citations inside the published CSV
  (scripts/pipeline_v2/restore_queue_b06recovery.py): 27 corpus rels marked done (sha16 cited in
  GitHub CSV @2d7a5ec), B04's 2 regulations-only docs failed(regulations-only), B06's 10 rels
  pending-pinned with per-rel recovery notes; batch_counter=5.
- Baseline G2/G3 repair re-derived deterministically from the published B06 manifest rule text
  (scripts/pipeline_v2/repair_baseline_g2g3.py): **74 repairs — exactly the count the B06
  manifest records** (28 BPharm era-print G2 groups + 6 BTech KCS/BCS lab twins + 4 G3 name
  dups qualified with era-print markers). Post-repair G2 PASS (course-scoped), G3 PASS.

## Batch (10 PDFs: 3 Aeronautical y4 + 7 Agricultural Engineering — same doc set as B06)

179 subjects drafted by 10 subagents (2 waves, cap 5): doc counts 22/18/20/14/23/26/20/9/6/21 —
**all 10 matched the B06 manifest's per-doc subject counts exactly (179/179)**, a strong
determinism signal for the re-derivation.

## Verify (step 5) — 10/10 PASS after evidence-backed v10 re-patches

- draft 01: GP101 5-char ORPHAN false positive (print 'GP 101' spacing) — tolerant code parse.
- draft 02: EOE071-074/081-084 GAP false positives — codes carried verbatim in
  non_subject_rows (B06-documented exemption).
- draft 03: 23 containment hard-fails = scheme-table cell order ('Textbook topics' header,
  L-T-P digit cells, 'Lectures N' furniture) + cross-page junction (Surveying unit5 proven
  verbatim across the pp.19→20 junction by direct text-layer inspection); NCE/NEW/NME compound
  codes ('NCE-151/251' prints BOTH codes) — v10b PDF-side compound parser.
- draft 05: 8 no-code labs (doc prints none; scheme rows print combined theory codes) —
  evidence-flagged downgrade, zero codes invented.
- draft 07: KMC101 GAP (compound 'KMC 101/201' draft token) + KAS-154P ORPHAN (print spacing).
- draft 10: 12→7→0 containment (running-header/masthead furniture + standalone 'N%' cells +
  cell-order tolerance).
- 60 residual WARNs all in the documented classes (Group A/B label joins, Sem-II offset
  reprints, book-title line splits).

## Merge (step 6) — TIER2_OVERRIDES restored, two live rejects recorded

- COMMIT attempt 1: 60 UPDATE / 119 APPEND, gates PASS — but the 8 live-pool Tier-2 hits were
  then reviewed per-key (the generic pre-adjudication was insufficient). Two were WRONG merges
  and were fixed:
  - fundamentals-of-electronics-engineering (AEC101C/201C) had updated the just-appended
    fundamentals-of-electrical-engineering (AEE101C/201C) from the SAME 2026-27 doc — the print
    carries BOTH as separate subjects; FORCE_APPEND (B06's recorded 'Electronics vs Electrical'
    reject class).
  - fundamentals-of-mechanical-engineering (AME101D/201D) had updated the 2020-21 KME101
    'Fundamentals of Mechanical Engineering & Mechatronics' row — names differ by a substantive
    token; evidence inconclusive → zero-guess keeps separate rows (FORCE_APPEND).
  - 6 live hits ALLOWed with evidence (thermodynamics + fundamentals-of-computing era-family
    merges, surveying era merge, aircraft-systems-and-maintenance-lab plural, and the BEE-lab
    family consolidation).
  - Divergence from B06 recorded: the BEE-lab family (2008-09 'BAISC' print + 2018-19 'BAISC'/
    'BASIC' reprints + 2020-21 KEE-151P/251P lab) lands as ONE row here (the 2020-21 doc itself
    prints one subject spanning both semester codes; typo prints preserved in name_print/
    code_history) where B06 kept two rows — B06's extra row is the sole census delta.
- DOC_SCOPE restored for all 10 sha16s (cover-print branch evidence: Agricultural/Aeronautical
  Engineering; program_year from each doc's semester span).
- Final: **COMMIT OK — rows 526→647 (635 subjects + 12 frozen non-subject), codes 850
  exact-owned course-scoped, +121 appends / ~58 updates**; gates G1 PASS · G2 PASS codes=850 ·
  G3 PASS · G6 PASS containment_checks=79; census BTech 340 · BPharm 249 · BCA 46; branches 19
  (+ Aeronautical Engineering, + Agricultural Engineering restored).
- CSV md5: computed at push time · backup: pre_commit_2026-10-29T071654p0000.csv
- Queue: batch06's 10 rels marked done (409 pending remain, MBA/MCA/BTech-heavy).

## Stage summary

- The B06 catalog deltas (+121 appends here vs B06's +122) are now ACTUALLY on GitHub; the
  CHANGELOG/manifest claims of CRON-20261029-B06 are superseded by this run's CSV.
- verify_draft.py v10/v10b/v10c and merge_draft.py TIER2_OVERRIDES/DOC_SCOPE are re-pushed with
  this run per RULES §1c item 4 (toolchain versioning) so the next reset cannot lose them again.
- Open items: (1) doc05's 8 no-code lab rows appended without codes (doc prints none); (2) the
  BEE-lab single-row consolidation vs B06's two-row outcome (recorded above); (3) 12 frozen
  non-subject rows still await the owner's migration instruction; (4) 409 PDFs pending; (5)
  rr_sid owner-assigned at the very end; (6) push_catalog.sh should be committed INTO the repo
  pipeline/ so it stops being session-local.
