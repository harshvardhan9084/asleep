# CRON-20261031-B13 — B13 — 2026-10-31

rows 1113-1231, codes 1329-1486, +118 appends/~90 updates/!197 repairs

# CRON-20261031-B12 — B12 — 2026-10-30

rows 1068→1113, codes 1764→1947, +45 appends/~165 updates — BTech Biotechnology y1-y4 wave 2014-15→2025-26 (10 docs, 211 subjects drafted); 8 NPTEL raster pages page-image recovered; 17 TIER2_OVERRIDES + 5 name-transfers + 1 slot-skip adjudicated; gates G1/G2/G3/G6 PASS

# CRON-20261031-B11 — B11 — 2026-10-30

rows 979→1068, codes 1494→1749, +89 appends/~188 updates — BME y3/y4 RBM-era + Biotechnology era wave 2009-10→2026-27 (10 docs, 277 subjects drafted); 41 flags adjudicated (20 recorded B11 TIER2_OVERRIDES); doc02 scanned-page OCR recovery page-image-verified; doc04 folded-lab code strips preserved published AKTU ownership; gates G1/G2/G3/G6 PASS

# CRON-20261031-B10 — B10 — 2026-10-30

rows 875→979, codes 1346→1494, +104 appends/~107 updates/!104 repairs — BTech AU y4 five-era completion + Bioinformatics y2/y3 + BME 2009-10/2011-12 + AE/ECE-EI 2016-17 _2 copy (10 docs, 215 subjects drafted); EBM-012 slot reassignment recorded (REHAB→BIOELECTRICITY); HAP sem-IV/V split repaired (§11); G6 durable-corpus fallback + OCR-evidence remedies; gates G1/G2/G3/G6 PASS

# CRON-20261031-B09 — B09 — 2026-10-30

rows 777→875, codes 1164→1346, +98 appends/~102 updates — BTech AU five-era wave (2009-10→2024-25) + AI-ML y4 ×2 + all-branch y1 2016-17 + AE/ECE-EI 2016-17 (9 docs, 200 subjects drafted); B08 BCA-project cross-course contamination repaired (§1b); 3 live cross-draft convergences; gates G1/G2/G3/G6 PASS

# CRON-20261030-B08 — B08 — 2026-10-30

rows 744→777, codes 1089→1164, +33 appends/~101 updates — BTech AG y4 (5 era prints) + AI-DS/AI-ML y2-y4 wave (8 docs, 134 subjects drafted); 2016-17 NAG code-collision adjudicated; 12 cross-draft convergences; gates G1/G2/G3/G6 PASS

# CRON-20261030-B07 — B07 — 2026-10-30

rows 647→744, codes 1089, +97 appends/~121 updates — BTech AG corpus wave (10 docs, 222 subjects drafted); 5 era-splinters converged; gates G1/G2/G3/G6 PASS

# CRON-20261029-B06-recovery — B06R — 2026-10-29

rows 526→647, codes 850, +121 appends/~58 updates — B06 CSV-recovery re-run: prior commit 2d7a5ec shipped CHANGELOG+manifest only (CSV lost); re-derived B06's 10 docs (AE y4 x3 + AG x7) incl. 74-row baseline G2/G3 repair redo; gates G1/G2/G3/G6 PASS

# CRON-20261029-B06 — B06 — 2026-10-29

rows 526→648, codes 855, +122 appends/~57 updates across 10 docs (AE y4 x3 + AG x7) incl. baseline G2/G3 repair (74 rows)

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
