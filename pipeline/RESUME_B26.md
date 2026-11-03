# RESUME NOTE — B26 in-flight state (written 2026-11-03, after the 31st workspace reset)

If you are a fresh session continuing this project with the standard cron batch
message: the batch B26 is IN FLIGHT and its extraction work is ALREADY DONE and
stored in this repo. Do NOT re-extract. Resume from step 5 (verify).

## Durable state (all in this repo — survives resets)

- `pipeline/drafts_B26/01..10_*.draft.json` — ALL 10 B26 extraction drafts
  (284 subjects total), committed at 854e9fd (wave 1) and bab0622 (wave 2).
- `pipeline/restore_queue_b26.py` — citation-based queue rebuild to the B25-end
  state (224 done / 219 pending / 5 failed, batch_counter=25).
- `pipeline/select_batch.py` — patched: stages real file COPIES (the sandbox
  forbids symlink creation; the call is killed at process level, not catchable).
- `syllabus_catalog/syllabus_extreme_rich.csv` — B25 baseline (1855 data rows),
  the authoritative merge target for B26.

## B26 batch content (batch26, 10 docs — deterministic selection)

| # | stem | session | sha16 | subjects |
|---|------|---------|-------|----------|
| 01 | btech_env_y4_syllabus_2016-17 | 2016-17 | c2eff0f0adde9801 | 30 |
| 02 | btech_env_y4_syllabus_2021-22 | 2021-22 | bf77e3978ffc422f | 19 |
| 03 | btech_ft_s5-6_syllabus_2024-25 | 2024-25 | dc6eee55aae5dadc | 23 |
| 04 | btech_ft_s7-8_syllabus_2025-26 | 2025-26 | 7537580daa99b640 | 13 |
| 05 | btech_ft_syllabus-rev_2009-10 | 2009-10 | 834e84015a481092 | 70 |
| 06 | btech_ft_syllabus_2015-16 | 2015-16 | 6228f90ed89f20f4 | 20 |
| 07 | btech_ft_syllabus_2016-17 | 2016-17 | 3b901f828959a8cd | 30 |
| 08 | btech_ft_syllabus_2018-19 | 2018-19 | d375d93b8b8beafc | 24 |
| 09 | btech_ft_y2_model-curriculum_2019-20 | 2019-20 | d50ea38d1e2b1f8d | 21 |
| 10 | btech_ft_y2_scheme-syllabus_2017-18 | 2017-18 | cbbe78b0fd8083e9 | 34 |

Queue rels: `repo_asleep/PDFs/5-course/<session>/<stem>.pdf` (uniform-name layout).

## Resume procedure (after any reset)

1. Standard restore: .env (PAT from the cron message), clone this repo, copy
   `syllabus_catalog/syllabus_extreme_rich.csv` to
   `download/art_d_final/syllabus_extreme_rich.csv`.
2. `python3 scripts/pipeline_v2/restore_queue_b26.py` (rebuilds queue at
   counter=25), then `enqueue_corpus.py` (no-op) and `select_batch.py`
   (yields batch26 — the same 10 docs, deterministic).
3. `parse_batch.py` + `dump_fulltext.py` on staging/batch26.
4. Copy the durable drafts into the working drafts dir (or pass the repo dir):
   `mkdir -p work/pipeline_v2/drafts/B26 && cp work/repo_asleep/pipeline/drafts_B26/*.draft.json work/pipeline_v2/drafts/B26/`
5. Continue with step 5 of the cron message: `verify_draft.py parsed drafts`,
   then merge decisions/commit, mark_done, push_catalog.sh
   "CRON-20261103-B26" "B26", worklog.
6. During extraction/merge work, commit+push intermediate state EARLY and OFTEN
   (drafts go straight into `pipeline/drafts_B26/`) — resets hit every ~1-2
   hours and only pushed state survives.
