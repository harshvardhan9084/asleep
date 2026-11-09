# CRON-20261109-B70 — W10a/W10a2: owner flag-fixing program starts (PUNCT_ARTIFACT class closed)

## Directive (verbatim, 2026-11-09)
"I asked what the cron fire is making you do? Are you fixing up those 4908
audit flags? Okay, do it from now" — the hourly cron now works the audit
flags evidence-first, class by class, starting with the biggest
deterministic one.

## Wave 1 — W6 rerun (deterministic, committed B54 rule re-applied)
392 unit/co-text artifact fixes (TF fields persist in-field; book-field
(JF) edits were recorded but NOT persisted — see discovery below). Gates
G1/G2/G3/G6 PASS (checks 208).

## Discovery — book-field write-back bug (B54 → B69)
W6's JF loop mutated the parsed JSON array in memory (`b[k]=new`) but never
re-serialized it into the row (`r[col]=json.dumps` missing), so every book/
experiment "fix" since B54 was metadata-only: corrections_json recorded
before/after while the field kept the artifact. Same bug hit the first W10a
pass (213 edits, metadata-only before the patch landed).

## Remedies
1. **Audit v18 guard** (W9a auditor-FP precedent): 'et al.,' / 'ed.,' /
   'eds.,' / paren-prefixed '(e.g.,' are standard scholarly print — the W6
   abbreviation guard (both w6_artifacts.py and audit_rules.py, self-
   contained copy) now keeps them; ~157 false-positive flags reclassified.
2. **W10a2 actual write-back** (369 field fixes): clean-v18 (fixpoint) over
   all flagged book/experiment entries + the W6/W10a candidate rows, field
   serialized back into the CSV; each change carries corrections_json
   before/after with an explicit supersession note; ~180 no-op ledger
   repairs appended where a stale record claimed a change the file never
   received (RULES §6b honesty); w6_artifacts.py patched so future runs
   persist.
3. objectives_print stays untouched (recorded W6 policy); its 2 flags were
   paren-prefixed legit print, reclassified by the guard.

## Result
PUNCT_ARTIFACT 3,281 → **0** (class closed). Audit flags 4,908 → **1,627**
(rows flagged 1,860 → 1,323). Remaining: TYPE_EMPTY 521 + KLS_MISSING 512
(fix:W4/W3 waves — next), and the honest needs_review classes (BOOK_TRUNC
169, CREDIT_FORMULA 139, SESS_SUM 125, MARKS_SUM 122, TOKEN_N_LOWER 26 —
recorded no-auto-fix by design, BOOK_MERGED 6, KLS_SHORT 5,
DISPLAY_MISSING 2).

## Gates / push
G1 PASS (62-col v2.1), G2 PASS (6,412 owned codes, dups 0), G3 PASS,
G6 PASS (checks 144/207 across commits, pre_edit_hits=[]). Backups in
work/pipeline_v2/backup/. T2T calls: 0 (deterministic waves; keys 5/5
untouched). Push batch CRON-AUTO-B70.
