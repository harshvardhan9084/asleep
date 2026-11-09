# CRON-20261109-B69 — Owner-directive structural prune (rows + column)

## Directive (verbatim, 2026-11-09)
"At very first, delete those ~12-18 rows whose are not subjects of any kind
from ~3097 rows." + "Delete 'k era pool codes' immediately".

## R1 — 12 non-subject rows deleted (3,097 → 3,085)
row_kind audit found exactly 12 rows that are not subjects of any kind (the
owner's ~12-18 upper bound included them all): 8 semester_summary ("Semester
III/IV/V/VI printed totals" — CSE-AI 2022-23, AIML 2024-25, Civil 2024-25),
2 program_rule (MOOCs-essential-for-Hons, Minor/Honors MT-1/HT-1), 2
elective_pool (Science-Based Open Elective 2nd-year pool, Open Elective-I
3rd-year pool). None carries a primary_code or all_codes; their printed
policy text is preserved in the repo history (this manifest + prior runs) and
in the pre-prune backup.

## R2 — k_era_pool_codes column deleted (63 → 62 cols, schema v2.1)
The column held exactly ONE non-empty cell in 3,097 rows — and that cell lived
on the science-based-open-elective-pool row deleted by R1 ("KOE031-038; KOE041-048
(K-era ranges) / BOE3**/BOE4** (B-era wildcards)"). On real subject rows the
column was 100% empty: elective-pool membership is already carried by
all_codes + choice_group_id (53 rows) on the subject rows themselves. G2
owned-code count before vs after: 6,412 → 6,412 (the column contributed zero
unique codes). REF_HEADER in merge_draft.py updated to the 62-col v2.1 header;
codes_of_row ownership tuple cleaned accordingly.

## Gates / audit / push
G1 PASS (62-col v2.1 header), G2 PASS (6,412 owned codes, dups 0), G3 PASS,
G6 PASS (0 containment checks — pure deletion, no value edits). Post-prune
audit: rows=3,085 flagged=1,860 flags=4,908 (identical flag mass — no flag
was attached to the deleted rows). Backup:
work/pipeline_v2/backup/pre_prune_*.csv. T2T calls: 0 (deterministic prune;
keys 5/5 untouched). Push batch CRON-AUTO-B69.
