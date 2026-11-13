# B93 — Reset-proof restoration of the B92 audit-of-record basis (bookkeeping-only)

- Run: `CRON-20261113-B93`
- Trigger: standing cron payload (job 524343), 2026-11-13 09:30 IST firing; 36th
  workspace reset detected post-B92 (foreign DATABASE_URL-only .env isolated as
  `.env.foreign_backup_20261113_*`, 7-key .env rebuilt, repo re-cloned, CSV
  md5-verified against HEAD).

## Situation found

- CSV intact: `download/art_d_final/syllabus_extreme_rich.csv` =
  3,080 rows x 62 cols, md5 `e21e81fba24bbcf2ae7851565c8c78f3` == B92 HEAD blob
  (the owner's final clean CSV — unchanged).
- B92's audit-of-record basis files were EPHEMERAL and lost to the reset:
  `work/pipeline_v2/b92_owner_directive.json` (43 BOOK_TRUNC + 375 TYPE_EMPTY
  drops) and the B92-updated `work/pipeline_v2/w9a_ckpt.json`.
- Fresh audit without the basis re-reported raw heuristic hits: 413 rows /
  432 flags (TYPE_EMPTY 375 + BOOK_TRUNC 57) — all within classes B92 already
  adjudicated; no data regression.

## What was done (zero CSV change — verified md5 before == after)

1. Re-derived the B92 basis with B92's OWN deterministic code path (imports
   `b92_apply_remediation` position-map/clean_value/validate_span + t9/b91
   helpers) against the same durable PDFs, in READ-ONLY mode:
   - 57 raw BOOK_TRUNC -> 43 removed_owner_directive (**exact match** with the
     B92 manifest's recorded 43 — independent cross-validation) + 14
     verified_complete (10 cascade print-equal + 4 durable B92 page-image
     attestations: 2 inside the CSV's own corrections_json
     [industrial-biotechnology-lab ref[0] p.23 print-merged cell;
     water-resources-systems tb[3] p.17] + 2 in the committed B92 manifest
     [EMT-601 ref[3] p.10 print-verbatim minus list letter; EME-603 tb[0] p.34
     print-verbatim]).
   - TYPE_EMPTY 375 -> directive list = the fresh audit's active set (b92_te
     semantics, verbatim).
   - Any unattested divergence aborts (no guessing) — zero divergences remained.
2. Wrote `b92_owner_directive.json` (43 + 375) and the merged
   `w9a_ckpt.json` (B73-era 168-entry wave + 14 B92/B93 verified_complete,
   older statuses on the same keys superseded by the fresh re-derivation).
3. **Reset-proofing (permanent fix):** committed both basis files to the repo
   (`syllabus_catalog/runs/b92_owner_directive.json`, `w9a_ckpt.json` merged)
   and patched `audit_rules.py` to fall back to the repo copies when the
   work/ copies are missing — the audit-of-record now survives resets.
4. Ledger: `syllabus_catalog/runs/b93_ledger.json` (+ work probes copy).
5. Re-ran the audit WITH the restored basis: **rows_flagged 0, total_flags 0**
   (b92_owner_directive_removed=418 = 43 BT + 375 TE; +14 via w9a
   verified_complete) — matches B92's recorded audit-of-record exactly.

## Result

- CSV: byte-identical to B92 HEAD, md5 `e21e81fba24bbcf2ae7851565c8c78f3`,
  3,080 x 62 — the final clean CSV stands.
- Gates n/a (bookkeeping batch, no ingestion, no CSV mutation; audit PASS).
- T2T calls=0 (no mercury usage; no new corpus docs — enqueue delta 0 of 448).
