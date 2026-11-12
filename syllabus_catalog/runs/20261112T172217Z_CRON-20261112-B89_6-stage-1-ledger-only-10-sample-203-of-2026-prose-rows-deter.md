# CRON-20261112-B89 — T6 unit-text containment (10% sample), stage-1 (ledger-only)

Run: cron delivery of job 524343 standing payload, ~2026-11-13 early IST slot
after B88. NO RESET this run: 7-key .env intact (names verified), repo clone
present, HEAD 0a29c8a = `git ls-remote origin main` (= B88 push), download/ CSV
md5 95f41cfa byte-identical to repo copy, local pipeline scripts identical to
repo HEAD (t9 probe md5 7457f3b…). READ FIRST satisfied from repo CHANGELOG
(top entry B88, "T6 next").

## Test executed
T6 (unit-text containment, P2, medium; plan prescribes a 10% sample) — stage 1:
- Population: 2,026 subject rows carry real unit prose (>=40 chars in
  unit1..unit5_text; median 239 chars/unit). Deterministic sample: rows sorted
  by subject_id, every 10th from offset 5 → 203 rows (reproducible from the
  ledger's rule block).
- Method: verbatim containment — squashed unit text (all non-alnum removed, so
  PDF line breaks / hyphenation / spacing cannot break the match) must appear
  in the squashed text layer of the row's own cited syllabus docs; fallback
  24-char shingle coverage: >=0.85 high_overlap (assembled with minor edits),
  0.35-0.85 partial_overlap, <0.35 not_in_doc. Best doc decides per unit.

## Verdicts (rows: 203; prose units in sample: 971)
- attested_verbatim 179 rows (88.2%) — all prose units verbatim-contained in a
  cited doc's text layer; unit-level 916/971 verbatim. Corpus quality on this
  axis is strong.
- mixed_overlap 15 rows — at least one unit verbatim/high, others partial
  (unit-level: 28 high_overlap + 14 partial_overlap + 13 not_in_doc spread
  across these rows; mostly unit5 tail truncations and paraphrased NPTEL
  unit texts).
- unit_text_not_found_review 6 rows — docs resolvable but NO unit found
  (coverage <0.35): EBM-803, RBT082/RBT085/RBT088 (NPTEL electives),
  NCH-702, EEC-304. UNfixed per standing mechanics — stage-2 page-image
  verification (per §6b, text-layer absence is not proof of absence) before
  any fix/flag in a later batch.
- no_citation 3 rows — no parseable citation fields.
- 0 CSV changes, 0 fix candidates this batch (ledger-only).

## Standing mechanics compliance
LEDGER-ONLY: no CSV write, no quality_flags change. Fresh audit_rules.py scan
on the unchanged CSV: flags 442 = TYPE_EMPTY 375 / BOOK_TRUNC 65 /
DISPLAY_MISSING 2 — unchanged. Gates n/a (no CSV mutation). enqueue_corpus:
0 new PDFs (165 PARKED untouched). T2T: calls=0 (deterministic corpus probe, no
mercury drafting; .env active keys 5+PAT, verified by name only). wave_runner
--loop remains RETIRED (W3 closed). Batch numbering from CHANGELOG: B88 last →
this is B89. Cascade next: T13 (buyer-grade 100-row spot audit) — the FINAL
test of the 2026-11-11 quality-test plan; after T13 the cascade is complete
and runs revert to audit-only unless the owner opens a new work item.

## Files
- work/pipeline_v2/probes/t6_probe_ledger.json (copy:
  syllabus_catalog/owner_requests/t6_probe_ledger.json)
- syllabus_catalog/owner_requests/quality_probe_T6_2026-11-12.xlsx (3 sheets)
- syllabus_catalog/runs/<ts>_CRON-20261112-B89_*.md (this manifest)
