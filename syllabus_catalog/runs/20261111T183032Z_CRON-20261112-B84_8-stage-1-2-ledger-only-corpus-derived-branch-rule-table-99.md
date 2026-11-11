# CRON-20261112-B84 — T8 branch coherence, stage-1 + stage-2 (ledger-only)

Run: cron delivery of job 524343 standing payload (trace 1a1cbd557f601c85), received
~2026-11-11 23:58 IST / 2026-11-12 02:28 +08, after B83 completed the 23:00 IST slot
in a sibling session. Workspace was RESET (foreign DATABASE_URL-only .env present,
repo clone absent, CSV md5 stale): standard restore executed — foreign .env isolated
as .env.foreign_backup_20261111_181923 (never printed), 7-key .env rebuilt (names
verified only), anonymous clone of origin/main, HEAD d642f10 verified against
`git ls-remote`, CSV copied and md5-verified byte-identical (95f41cfa…), pipeline
toolchain rsynced from repo HEAD (stale local files never authoritative). bb61084
already in pushed history (B82/B83 landed earlier) — nothing pending to push at
restore time.

## Test executed
T8 (branch coherence, P2, expected yield: low) — stage-1 rule-table scan + stage-2
own-cited-doc page evidence. Rule table CORPUS-DERIVED: per-(course, family)
histogram over the branch tokens of branch-bearing rows only. Established = family
n>=10 branch-bearing rows, top-branch share>=0.60; families spreading across >=8
distinct branches are UNIVERSAL composition classes (BOE/BCS/BAS elective-service
families) and never candidates; families with <10 branch-bearing rows cannot
establish a rule honestly — suppressed and recorded. Branch-token compatibility =
squash equality, containment, or common prefix>=12 chars ('Electrical Engg.' vs
'Electrical Engineering'; CSE(AI) suffix vs CSE), plus a variant table for AKTU's
own printed spellings (the 2020-21 AG model-curriculum prints 'Agriculture
Engineering' where scheme rows print 'Agricultural Engineering' — variant-equal,
not a mismatch).

## Coverage honesty (probe ledger work/pipeline_v2/probes/t8_probe_ledger.json)
- 3,080 subject rows; 1,156 branch-bearing (BTech 1,155 + MCA 1); 1,924 rows carry
  NO branch_names at all — branch coherence is uncheckable for them (never invent
  a branch value); recorded as a coverage stat, NOT a pass.
- 99 families with branch data; 27 established; 11 universal.
- stage-1 skips (recorded, never silent): universal_family 140,
  family_spread_no_majority 132, family_small_branchdata 119, no_prefix 44,
  pool_family 44 (BOE/KOE/ROE/AU*/GP/VAC classes out of scope by design).

## Funnel + verdicts
- stage-1 candidates: 7 — every one is a Civil-family (ECE-251-era / KCE / RCE) or
  departmental code sitting in an Agri/Biotech scheme row: CAEG ECE-251,
  Engineering Graphics & Design KCE101/KCE-151P, Strength of Materials
  RCE308/RCE358, Fluid Mechanics for Biotechnology RCE309/RCE359.
- stage-2 (own-cited-doc fitz text layer, cited pages first, whole-doc fallback;
  title context recorded for EVERY resolvable doc even when the code is
  text-layer-absent):
  - print_agrees_stored_attested 6 — the row's OWN cited doc prints the code
    inside the stored branch's scheme ('B.Tech. I Semester (Agriculture
    Engineering)' @btech_ag_y1_model-curriculum_2020-21 p3 for KCE151P; Agri
    scheme context for KCE101/RCE308/RCE358; Biotech scheme for RCE309/RCE359).
    Cross-branch service composition, print wins per §6b/B76 — NO fixes, NO flags.
  - era_multi_scheme_service_row 1 — ECE-251 'Computer Aided Engineering
    Graphics' (stored Agri): code found only in the 2009-10 Biotech scheme doc
    while two OTHER cited docs (btech_ag_syllabus_2013-14,
    btech_ag_y2_scheme-syllabus_2017-18) print 'Agricultural Engineering' in
    their titles but never print ECE-251 in the text layer (as-drafted/bitmap
    citation class). Define-once multi-scheme row — nothing contradicts the
    stored branch. Ledger note, no fix.
  - print_proven_branch_incoherence 0 → ZERO fix candidates, ZERO CSV change.
- Review set: none (all 7 candidates resolved to composition classes with print
  evidence; no inconclusive cases).

## Ledger + evidence
- work/pipeline_v2/probes/t8_probe_ledger.json (copy:
  syllabus_catalog/owner_requests/t8_probe_ledger.json)
- syllabus_catalog/owner_requests/quality_probe_T8_2026-11-12.xlsx (3 sheets:
  stage2 verdicts / rule-table transparency / per-citation evidence)

## Standing mechanics compliance
LEDGER-ONLY: no CSV write, no quality_flags change. Fresh audit_rules.py scan on
the unchanged CSV: flags 442 = TYPE_EMPTY 375 / BOOK_TRUNC 65 / DISPLAY_MISSING 2
(BOOK_TRUNC 66→65 from the B82 consolidation row-removals; delta already recorded
in the B82 CHANGELOG entry). Gates n/a (no CSV mutation). T2T: calls=0
(deterministic corpus probe, no mercury drafting; .env active keys 5+PAT, verified
by name only). wave_runner --loop remains RETIRED (W3 closed). Batch numbering from
CHANGELOG: B83 last → this is B84. Cascade next: T7 (semester/year coherence) per
the owner plan order after T3, T8.
