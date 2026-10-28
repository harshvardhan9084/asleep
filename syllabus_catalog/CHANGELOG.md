- 20261028T200216Z [CRON-20261028-B05] (B05): rows 402→526, codes 485→651, +124 net appends/~697 update plans across 10 docs (4 BPharm eras + BTech ACT/AE wave), 122 cross-era TIEs adjudicated to same-doc rows, 7 legacy-course duplicates deduped; gates G1/G2/G3/G6 PASS — manifest: runs/20261028T200216Z_CRON-20261028-B05_rows-402-526-codes-485-651-124-net-appends-697-u.md
- 20261028T191859Z [CRON-20261028-B04-repair] (B04R): rows 402→402, codes 485, ~81 field repairs (66 unit-text lecture-count normalizations + 15 lectures_per_unit fills, RMT limit-formula page-image completion); gates G1/G2/G3/G6 PASS — manifest: runs/20261028T191859Z_CRON-20261028-B04-repair_rows-402-402-codes-485-81-field-repairs-66-unit-.md
- 20261028T184124Z [CRON-20261028-B04] (B04): rows 204→402, codes 270→485, +198 BCA/BPharm appends, ~142 updates across 4 code eras, 2 regulations-only quarantined, G2/G3 pool+code-reuse evolutions; PUSH BLOCKED (no PAT) — manifest: runs/
# CHANGELOG — syllabus_extreme_rich.csv

One entry per push; GitHub git log + this file are the authoritative
per-run change history (RULES §1c, owner directive 2026-10-28).

## 2026-10-28T12:07:17Z — run `CRON-20261028-B03` — batch B03

- BCA re-ingestion per RULES 1b: rows 196→204, codes 303→310, +8 BCA subject rows (course-boundary crossrefs), ~39 BCA updates, BBC102 code-ownership transfer adjudicated, G2 now course-scoped
- rows 196→204, subjects 184→192, owned codes 263→270
- subjects by course: BCA 22→30, BPharm 40→40, BTech 122→122
- row kinds: {"elective_pool": 2, "program_rule": 2, "semester_summary": 8, "subject": 192}
- gates G1/G2/G3/G6 enforced at the pipeline commit (see runs/ manifest for detail)
- commit: this push (git log — message carries run id + batch)
- data: [syllabus_extreme_rich.csv](syllabus_extreme_rich.csv) — 57 columns; zero-guess; provenance per row; rr_sid owner-assigned
## 2026-10-28T11:34:12Z — run `CRON-20261028-B03` — batch B03-prep-repair

- course-boundary repair: 8 BTech rows reverted from BCA contamination (RULES 1b), 87 rows course-canonized, ladder hardened, tracking now GitHub-referenced (RULES 1c)
- rows 196→196, subjects 184→184, owned codes 270→263
- subjects by course: B.Tech 87→0, BCA 22→22, BPharm 40→40, BTech 35→122
- row kinds: {"elective_pool": 2, "program_rule": 2, "semester_summary": 8, "subject": 184}
- gates G1/G2/G3/G6 enforced at the pipeline commit (see runs/ manifest for detail)
- commit: this push (git log — message carries run id + batch)
- data: [syllabus_extreme_rich.csv](syllabus_extreme_rich.csv) — 57 columns; zero-guess; provenance per row; rr_sid owner-assigned
