# CHANGELOG — syllabus_extreme_rich.csv

One entry per push; GitHub git log + this file are the authoritative
per-run change history (RULES §1c, owner directive 2026-10-28).

## 2026-10-28T11:34:12Z — run `CRON-20261028-B03` — batch B03-prep-repair

- course-boundary repair: 8 BTech rows reverted from BCA contamination (RULES 1b), 87 rows course-canonized, ladder hardened, tracking now GitHub-referenced (RULES 1c)
- rows 196→196, subjects 184→184, owned codes 270→263
- subjects by course: B.Tech 87→0, BCA 22→22, BPharm 40→40, BTech 35→122
- row kinds: {"elective_pool": 2, "program_rule": 2, "semester_summary": 8, "subject": 184}
- gates G1/G2/G3/G6 enforced at the pipeline commit (see runs/ manifest for detail)
- commit: this push (git log — message carries run id + batch)
- data: [syllabus_extreme_rich.csv](syllabus_extreme_rich.csv) — 57 columns; zero-guess; provenance per row; rr_sid owner-assigned
