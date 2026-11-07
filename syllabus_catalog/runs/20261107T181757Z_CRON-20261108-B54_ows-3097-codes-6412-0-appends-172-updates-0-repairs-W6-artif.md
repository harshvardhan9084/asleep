# Task ID: CRON-20261108-B54

Agent: main (GLM) — owner-approved correction wave W6 (deterministic, no T2T; executed ahead of W3 per the owner's ordering note grouping W1/W2/W6 as the deterministic set)

Task: W6 unicode/punctuation artifact cleanup in primary fields (RULES §6b): guarded '.,' collapse, ',,'/' ,' normalization, math-italic Unicode → NFKC plain ASCII.

Work Log:
- 978 edits on 172 rows (units co1-6 + book/experiment entries). GUARD: '.,' kept where the period ends a legit abbreviation/initialism (e.g., i.e., viz., etc., No., Inc., Co., single initials 'J.,', dotted initialisms 'U.S.A.,'/'G.P.,') — 138+ such legit prints survive; artifacts like 'Direct Memory Access., I/O' collapsed to '.'. Math-italic decode artifacts → NFKC plain text.
- DECISION (recorded): '(n) lowercase' stray tokens (26 rows) get NO auto-fix — the class collides with legit notation (LR(0) items) and print list markers ((1) calendaring…); stays needs_review for per-row evidence reads.
- 4 benign non-abbrev '.,' edge cases remain (newline-boundary word detection) — surfaced by the W7 re-audit.
- GATES: G1 PASS / G2 PASS codes=6412 / G3 PASS / G6 PASS checks=544. Backup pre_commit_2026-11-07T181713p0000.csv. JSON columns parse clean.

Stage Summary:
- Registry 3097 × 63. Deterministic waves W1 (B52, 52 edits) + W2 (B53, 902) + W6 (B54, 978) complete: 1,932 evidence-recorded corrections. T2T calls so far: 0.
- Next: W3 co_kls backfill — deterministic K-scan of cited docs first, mercury-3 REX for leftovers (the heavy T2T wave), then W4/W5, W7 re-audit.
