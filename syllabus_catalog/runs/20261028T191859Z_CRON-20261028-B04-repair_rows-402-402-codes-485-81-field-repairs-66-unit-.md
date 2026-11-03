# CRON-20261028-B04-repair — registry field repair (post-push evidence fixes)

Date: 2026-10-29 (UTC) · Agent: Z.ai (GLM pipeline agent) · Base: GitHub 189ba64 (B04 completion push)

## What this run is

Owner supplied the GitHub PAT in the cron repeating message; with push authentication restored, the
session closed out B04 by propagating the two genuine post-commit evidence repairs into the published
registry, then re-publishing. This is a FIELD REPAIR of the already-committed B04 registry — no new
subjects, no code changes, no re-merge.

## Repairs applied (both verified against page images / fulltext before touching data)

- R1 — 2019-20 doc rows (sha 28cd10357b812c41): the doc prints each unit's lecture count at the START
  of the unit row ("10 Hours ..."), and the committed unit texts embedded that count cell as a text
  prefix. 66 unitN_text cells stripped of the prefix; the counts preserved into the CSV-established
  `lectures_per_unit` dict format (B02 BPharm precedent, e.g. `{'1': 10, '2': 10, '3': 10, '4': 8, '5': 7}`)
  which was empty for all 15 affected rows. Text content otherwise verbatim-unchanged.
- R2 — BP106RMT REMEDIAL MATHEMATICS unit1: the printed limit formula region is garbled in the PDF text
  layer (fraction layout scrambles to `lim x − a = na n−1 / x→a x − a ...`). Re-transcribed from the
  rendered PAGE IMAGE (printed p.27, drafts/_b04s06_rmt_p27-027.png + 300 dpi crop) per RULES §6
  (visible print authoritative): `lim(x→a) (x − a)^n / (x − a) = n a^(n−1), lim(θ→0) sin θ / θ = 1` —
  replacing the `[limit-formula region garbled in text layer]` annotation. Print defect (exponent sits
  only on the numerator trailing group; standard identity is (xⁿ−aⁿ)/(x−a)) kept verbatim as printed.

## Matching discipline (never guess)

Draft-subject → registry-row identity required ALL of: draft sha16 in the row's source_syllabus
citation chain + normalized name equality + printed-code overlap + course equality (§1b) +
newer-session guard (draft.session >= row.effective_session_latest). Two same-name candidates were
disambiguated by code (REMEDIAL BIOLOGY BP106RBT units-bearing vs BP112RBP scheme-only twin);
REMEDIAL MATHEMATICS matched uniquely. 2013-14-era rows whose content was legitimately superseded by
newer-era fieldwise wins were NOT touched (session guard).

## Gates

G1 PASS (header identical) · G2 PASS course-scoped codes=485 · G3 PASS · G6 PASS (15/15 provenance
spot-checks). Backup: work/pipeline_v2/backup/pre_repair_2026-10-28T191833p0000.csv.

## Numbers

rows 402 → 402 (unchanged) · codes 485 (unchanged) · 81 field updates across 15 rows
(66 unit-text normalizations + 15 lectures_per_unit fills + RMT formula) · census unchanged
(BTech 122 / BCA 46 / BPharm 222 subjects + 12 frozen non-subject rows) · md5 0fea2c4f02c42ca892f6b7be5557e593.

## Tooling hardening (same session, pre-repair)

- merge_draft.py: reinstated the lost B02-era foreign-format draft guard (51 abandoned pre-§7-schema
  drafts in drafts/ crashed `draft_vocab` on list-units; they carry 0 registry rows and are now skipped
  with a printed note) + draft_vocab made shape-tolerant.
- verify_draft.py: v7 haystack remedy — standalone "N hours" lecture-count lines stripped (junction
  evidence: BP607T unit2 pp.236→237, BP806T unit1 pp.274→275).
- Drafts 04/06/10 restored from the batch04_run/ lost-context snapshots after an over-broad code-first
  patch briefly mis-targeted the cGMP elective-pool subject (BP708T is printed on every 2026-27 pool
  slot); the registry itself was never affected (repair ran against the corrected drafts).

## State after this run

Registry (GitHub, this push): 402 rows × 57 cols, codes 485. B04 fully closed: 8 syllabus rels done,
2 regulations-only rels failed-with-evidence, queue 20 done + 2 failed... (counts per queue.json),
438 PDFs pending. Next hourly batch starts B05.
