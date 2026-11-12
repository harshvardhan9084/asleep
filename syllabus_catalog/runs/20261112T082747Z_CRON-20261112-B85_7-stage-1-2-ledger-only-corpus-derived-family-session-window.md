# CRON-20261112-B85 — T7 semester/year coherence, stage-1 + stage-2 (ledger-only)

Run: cron delivery of job 524343 standing payload (trace 1a1ced6264574b95),
~2026-11-12 13:48 IST / 2026-11-12 16:18 +08 slot after B84. Workspace was RESET
(foreign DATABASE_URL-only .env, repo clone absent, CSV stale md5 8faad353):
standard restore executed — foreign .env isolated as .env.foreign_backup_20261112_081857
(never printed), 7-key .env rebuilt (names verified only), anonymous clone, HEAD
324ad6b verified against `git ls-remote` (= B84 push), CSV copied and md5-verified
byte-identical (95f41cfa…), pipeline toolchain rsynced from repo HEAD. Local
worklog/probes wiped by the reset — durable record = repo runs/ + owner_requests/
(t7/t8 probe ledgers committed there; local work/pipeline_v2/probes rebuilt this run).

## Test executed
T7 (semester/year coherence, P2, expected yield: low) — stage-1 rule-table scan +
stage-2 own-cited-doc page evidence. Rule table CORPUS-DERIVED per (course, family):
core session window [min, max] over sessions holding >=5% of the family's DATED rows
(effective_session_latest parses as YYYY-YY), family established at n>=10 dated rows.
Hits are DIRECTION-TAGGED: era_forward (session > window max — the suspicious
grammar-violation direction) 16, era_backward (session < window min — mostly
first-print rows of later-recited families) 8. Letter-generation windows (E/N/R/K/A/B)
derived as SECONDARY context only — letter-level rules false-positive across courses
(B = BTech-era AND BPharm BP; M = MCA AND 2004-05 MBA docs); recorded, never used
as the rule. Skips (recorded, never silent): family_small_window 443, pool_or_no_code
312 (BOE/KOE/ROE/AU*/GP/VAC + empty-prefix classes out of scope by design),
undated_row 177. 85 family windows established.

## Funnel + verdicts (probe ledger work/pipeline_v2/probes/t7_probe_ledger.json)
- stage-1 candidates: 24 (EAG-604/ECE-251/KCS101/KAE-771/BEC151/KAG-057/RAG072/RAG080/
  RAG088/RME151/RME401/EBM-603/RCH076/NCS-082/NCS-087/KEC-077/EEC-032/KPE-751 in
  BTech; BP112RBP in BPharm; KMBI601 in MBA; MCA301/MCA404/(2)/NBC-9051/RCAI-505 in
  MCA 2026-27 rows).
- stage-2 (ALL cited docs scanned, no early stop; doc session parsed from the cited
  filename; fitz text layer, cited pages first, whole-doc fallback):
  - attested_cross_era_carryover 6 — the code IS printed in a cited doc whose parsed
    session equals the row's effective session (BP112RBP @2017-18, KCS101 @2018-19,
    KAE-771 @2021-22, BEC151 @2022-23, RME151 @2016-17, KPE-751 @2021-22); print
    wins per §6b/B76 — composition classes, NO fixes, NO flags.
  - effective_session_provenance_review 18 — the code prints in the row's OWN cited
    docs but only in docs of OTHER sessions than the row's effective_session_latest
    (e.g. EAG-604 s=2025-26 found only in 2009-10-era docs; MCA 2026-27 rows found
    in earlier-session docs). Effective-session provenance review set, UNfixed for
    a later multi-confirmed batch (same underlying multi-era accumulator
    composition T8 recorded from the branch lens — ECE-251/KAG-057 overlap).
  - session_year_review_candidate 0; no_citation 0; inconclusive_doc_unresolved 0.

## Data-quality OBSERVATION (recorded, zero candidates — outside T7 era scope)
program_year is bulk-defaulted '2' for 100% of BCA/MCA/MBA/BPharm rows (incl.
Sem-1 subjects) and 1,412/2,227 BTech rows — drafting artifact; a naive
slots-vs-year check would flag ~1,141 rows. NOT adjudicated: fixing needs per-row
print evidence per 6b/§4 (owner-visible ledger note only). Session-format sanity:
0 malformed effective_session_latest values.

## Ledger + evidence
- work/pipeline_v2/probes/t7_probe_ledger.json (copy:
  syllabus_catalog/owner_requests/t7_probe_ledger.json)
- syllabus_catalog/owner_requests/quality_probe_T7_2026-11-12.xlsx (4 sheets:
  stage2 verdicts / rule-table transparency / per-citation evidence /
  data-quality observation)

## Standing mechanics compliance
LEDGER-ONLY: no CSV write, no quality_flags change (flags 442 unchanged = TYPE_EMPTY
375 / BOOK_TRUNC 65 / DISPLAY_MISSING 2, fresh audit scan this run). Gates n/a (no
CSV mutation). enqueue_corpus not re-run this fire (0 new at B84 scan <24h ago;
running it is idempotent but unnecessary). T2T: calls=0 (deterministic corpus probe,
no mercury drafting; .env active keys 5+PAT, verified by name only). wave_runner
--loop remains RETIRED (W3 closed). Batch numbering from CHANGELOG: B84 last →
this is B85. Cascade next: T10 (CO duplication across rows).
