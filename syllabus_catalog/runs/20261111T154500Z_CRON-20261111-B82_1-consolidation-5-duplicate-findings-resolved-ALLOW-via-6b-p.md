# CRON-20261111-B82 — T1 duplicate consolidation — 2026-11-11

Owner quality-test cascade, T1 follow-up (the 5 duplicate_likely_code_gap
findings from QT1 probe ledger). Workspace reset #68 at batch start (repo,
.env, probe state wiped) — standard restore executed: foreign DATABASE_URL-only
.env isolated (`.env.foreign_backup_20261111_1524`, chmod 600, values never
printed), 7-key .env rebuilt from the scheduler authorizations (chmod 600),
anonymous clone of the public repo (HEAD b647eea — QT1 probe artifacts had been
pushed at 12:28, nothing lost), CSV restored from repo and md5-verified
(51093a9e = B81 anchor), toolchain rsynced from pipeline/ (t1_quality_probe.py
+ b81_computable_sums.py back in place). Baseline audit re-scan: 443 = TYPE_EMPTY
375 / BOOK_TRUNC 66 / DISPLAY_MISSING 2 (B81 anchor confirmed).

## Method (§6b verbatim-vs-fix, zero-guess)

For each finding pair: extracted BOTH rows' printed subject names from their
OWN cited docs (fitz text layer of the repo corpus; 21 doc probes recorded in
`work/pipeline_v2/probes/t1_evidence_ledger.json`, 0 unresolved shas), then
adjudicated per the B28 TIER2-ALLOW accumulator class. No content fields
(units/COs/books/marks) transferred; sessions never invented.

## ALLOW — 5 consolidations (rows 3085 → 3080, 9 codes unioned)

1. `control-system` ← `control-system-i` (+EIC-501, RBM501, RIC603): primary's
   own 2016-17 era already prints 'NIC-501 CONTROLSYSTEM-I' (p.5); secondary
   prints 'EIC 501 CONTROL SYSTEM I' (2009-10 BME p.6), 'CONTROL SYSTEM- I'
   (2017-18 p.4), 'RIC603 CONTROL SYSTEM-I' (2018-19 p.19); units 2/4/5 shared
   0.948-1.0, unit1 rewording = era/branch variant (B28 ITC class).
2. `i-c-engine-fuels-lubrication` ← `i-c-engine-fuel-lubrication` (+BME052):
   prints 'KME 054' (2020-21 AU p.15), 'BME 054- I C Engine, Fuels & Lubrication'
   (AU 2024-25 p.20), 'BME 052 - I C Engine Fuel & Lubrication' (ME-Ind/ME
   2024-25 p.16/p.17); units all 0.988-0.995. AKTU cross-doc slot inconsistency
   recorded (AU doc prints 'BME 052- Mechatronics Systems' p.22). BME054 NOT
   unioned — already owned by mechatronic-systems per its establishing print
   (G2 code-owner rule, B20 class); the first apply attempt hit exactly this
   G2 collision and was rolled back + corrected (gate working as designed).
3. `computer-aided-design` ← `computer-aided-design-cad` (+NME-701, EME-701):
   'ECE 051/NCE 051 COMPUTER AIDED DESIGN' (CE 2010-11/2016-17) vs 'NME-701:
   COMPUTER AIDED DESIGN (CAD)' (ME-Ind 2016-17 p.4), 'EME-701 : COMPUTER AIDED
   DESIGN (CAD)' (ME-PE 2009-10 p.39); units all 1.0 — multi-branch accumulator
   (B28 FEM class).
4. `pharmaceutical-chemistry-vi-medicinal-chemistry-ii` ←
   `pharmaceutical-chemistry-vii-medicinal-chemistry-ii` (+RPH-627): old scheme
   prints 'PHARMACEUTICAL CHEMISTRY-VI (MEDICINAL CHEMISTRY-II)' @BOP-361 (p.16);
   CBCS-rev scheme renumbers the SAME sem-6 course to 'PHARMACEUTICAL
   CHEMISTRY-VII (MEDICINAL CHEMISTRY-II)' @RPH-627 (p.16); units 1-4 verbatim
   identical, unit5 revised.
5. `net-framework-and-c` ← `dot-net-framework-c` (+RCAI-702, MCA-512): one
   subject across five code eras (MCA503 2004-05 → MCA-512 2010-11 → NBC-701
   2016-17 → RCAI-702 2020-21), print variants of '.NET Framework and C#';
   units all 1.0.

Each merged row carries: all_codes union, code_history chain appended verbatim
(' | T1-B82 merge from <sid>'), source_history entries deduped by sha16 and
appended with era annotations, secondary's scheme line preserved, notes +
change_note_vs_previous + a corrections_json entry
(rule=T1_TIER2_ALLOW_CONSOLIDATION, wave=T1-B82, before/after/evidence page-cited).

## DEMOTE — 1 recorded (no CSV change)

`microcontroller-embedded-systems-design` vs `microcontroller-for-embedded-systems`:
units 1-2 shared (0.999/1.0) but units 3-5 diverge (0.094/0.121/0.016) — the
recorded B28 same-core-different-tail split class (OOS ECS-305 precedent):
different subjects sharing an intro core. KEC-061/KECZ-061 slot-print proximity
recorded as an observation.

## Gates + audit

G1 PASS / G2 PASS codes=6412 / G3 PASS / G6 PASS containment_checks=5 (corpus
fallback). Audit re-scan: flags 443 → 442 (BOOK_TRUNC 66 → 65; the deleted
secondary rows' flags left the registry with their rows). CSV md5
51093a9e → 95f41cfa. Backup: work/pipeline_v2/backup/pre_commit_B82_*.csv.

Artifacts pushed: pipeline/t1_consolidate_b82.py (versioned toolchain),
syllabus_catalog/owner_requests/{t1_adjudication_b82,t1_evidence_ledger,
t1_probe_ledger}.json. T2T: calls=0 (fitz text layer only, no drafting).

Next: T1 stage-1 cleared for the 5 findings; 199 candidate_unresolved pairs go
to the T1 next-stage discriminator; cascade continues with T3 (code-name
mismatch) next batch per the owner's one-test-per-batch order.
