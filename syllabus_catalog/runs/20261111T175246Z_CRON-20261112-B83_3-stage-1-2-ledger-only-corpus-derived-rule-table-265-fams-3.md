# CRON-20261112-B83 — T3 code-name mismatch, stage-1 + stage-2 (ledger-only)

Run: cron fire of job 524343 (2026-11-11 23:00 IST slot, executed 2026-11-12 01:30 +08).
Workspace: preserved from B82 session (no reset). origin/main verified @82782a6 (B82 already
pushed; stale tracking ref made it look ahead-1 — fetch fixed, tree clean). .env 7 keys
canonical (names verified, values never printed). CSV md5 95f41cfa… matches repo HEAD copy.

## Test executed
T3 (code-name mismatch, P2) — stage-1 rule-table scan + stage-2 own-cited-doc page evidence.
Stage-1 rule table is CORPUS-DERIVED: per-(course, family) dominant-domain histogram over
word-bounded keyword classification (substring bugs found and fixed en route: fore'casting'
-> ME, 'architecture' -> ARCH false positives on CS courses, 'electronic' -> e-commerce,
'medicinal' -> horticulture). 265 families; 33 established (family n>=10, detectable>=8,
share>=0.70). Pool/audit/GP families (BOE/KOE/ROE/AU*/GP/VAC, 122 rows) out of scope by
design; service domains (MATH/MGMT/HOTEL) never arm-A candidates (universal curriculum
components); family n<4 skipped (77); secondary-domain clusters >2 rows suppressed and
recorded (290, e.g. KME-CS x4 = AKTU ME 2019-20 Python/DSA labs, attested composition).

## Funnel + verdicts (probe ledger work/pipeline_v2/probes/t3_probe_ledger.json)
- stage1 candidates: 86 (armA rare-technical-domain + accumulator guard; armB MBA-spec 0 hits)
- stage2 print_agrees_attested: 76 — the row's OWN cited doc prints the code with the
  (abbreviated/wrapped/DE-pool) same name; composition/grammar-breaker classes recorded,
  print wins per §6b/B76 — NO fixes, NO flags (examples: KAG-059 'Food Quality & Control'
  @p2; EBM-011 laser&fibre-optics @p5; BP202T Biochemistry @p34).
- review set 10 (recorded, NOT fixed — multi-stage confirmation pending):
  * code_not_in_any_cited_doc: 3 — BPE072 biomedical-plastics, BPE074
    polymer-structure-and-property-relationship, KPE303 fundamentals-of-polymer-science
    (whole-doc text-layer scan of every cited sha found no printed code)
  * no_citation: 7 — EF402, EF503, RTT051, KTT503, BVL051, BVL-052, BVL602
    (rows cite no doc their code can be checked against)
- inconclusive_doc_unresolved: 0 this funnel (the 5 earlier BAS303-class rows dropped out
  of the narrowed arm-A; 13bd875d remains a registered lost-sha from B28, unchanged)
- MBA specialization arm (MK/FM/HR/IB/IT/OM… suffix vs topic): 0 confirmed mismatches.

## CSV / flags
NO CSV write (standing mechanics: ledger-only until multi-stage confirmation). Fresh
audit_rules.py re-scan: total flags 442 = B82 anchor (TYPE_EMPTY 375 / BOOK_TRUNC 66 /
DISPLAY_MISSING 2 counts unchanged, rows 3,080 x 62). Gates G1/G2/G3/G6 not exercised —
no CSV mutation this run (audit-only run class).

## Artifacts
- scripts/pipeline_v2/t3_quality_probe.py (stage-1+2 probe; ledger-only)
- scripts/pipeline_v2/build_t3_evidence_xlsx.py
- work/pipeline_v2/probes/t3_probe_ledger.json (86 candidates, page evidence, skips,
  secondary-domain clusters, grammar crosscheck) — mirrored to
  syllabus_catalog/owner_requests/t3_probe_ledger.json for durability
- syllabus_catalog/owner_requests/quality_probe_T3_2026-11-12.xlsx (3 sheets: verdicts 86 /
  review set 10 / funnel transparency 112)

## Next batch (cascade order)
T8 (branch coherence) stage-1; then adjudicate the 10-row T3 review set only with
page-image-level evidence (text layer exhausted) — do NOT fix without the print.
T2T: calls=0 (probe run, no mercury drafting).
