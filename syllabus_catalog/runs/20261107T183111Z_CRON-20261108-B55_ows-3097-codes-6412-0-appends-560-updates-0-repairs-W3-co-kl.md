# Task ID: CRON-20261108-B55

Agent: main (GLM) — owner-approved correction wave W3 (the heavy T2T wave, first run)

Task: W3 co_kls backfill — deterministic K-scan first, mercury-3 REX for the remainder (owner SPEED directive: all T2T via mercury_call.py 5-key pool).

Work Log:
- QUEUE: 1,361 rows flagged KLS_MISSING/KLS_SHORT.
- PHASE 1 (deterministic text-layer scan of cited docs): 539 complete printed CO/K sequences found and applied (evidence = doc#sha pp.N). 294 partial → REX queue. 528 no K pairs in any cited doc's text layer.
- PHASE 2 (mercury-3 REX, tiny test call first — rc=0, model=mercury-3, ≤5 concurrent ThreadPool): 294 rows attempted.
- PHASE 3 (apply): 539 deterministic + 6 REX-complete + 7 REX-partial (nulls = K not printed for that CO, aligned by CO index) = 552 co_kls backfills, each with a corrections_json entry; 528 rows flagged honestly (kls_raster_candidate = cited doc has image-only pages → page-image reads needed; kls_not_printed = no K in text layer). 116 REX all-null + 165 API-failed rows left untouched with their KLS flags intact (retry via wave runner; keys rest & rejoin automatically).
- GATES: G1 PASS / G2 PASS codes=6412 / G3 PASS / G6 PASS checks=890. Backup pre_commit_2026-11-07T183026p0000.csv.

TRANSPARENCY (owner directive — T2T pool report for this wave):
- T2T calls attempted: 235 (incl. 1 tiny test) | HTTP 200: 134 | 429: 3 (1.3%) | 'response is empty': 37 | other key-fails (402-class): 3 | network: 0 | all-keys-resting exits: 23 (rows affected: 165, retry queued)
- Per key: #1 calls 26 / ok 12 / 429 0 / empty 7 / cooldowns 7 · #2 calls 3 / ok 0 / key_fail 3 / cooldowns 3 · #3 calls 178 / ok 112 / empty 24 / cooldowns 24 · #4 calls 10 / ok 2 / empty 4 / cooldowns 4 · #5 calls 18 / ok 8 / 429 3 / empty 2 / cooldowns 5
- Keys active in .env: 5/5. Subagent fallbacks: 0 (none permitted/needed — extraction leftovers retried later).
- No key discarded, no key requested; all crying keys sent to the 300s rest and rejoined automatically.

Stage Summary:
- Registry 3097 × 63; co_kls populated/repaired on 552 rows (co_kls coverage up from 26% toward full); 528 rows carry honest not-printed/raster flags for the owner.
- Next: wave runner resumes REX leftovers (165 api_fail + 116 all-null partials) on the next runs; then W4 (subject_type normalization + subject_name_display) and W5 (marks/credit per-row adjudication); W7 final re-audit.
