# Batch CRON-AUTO-B65 — W8b page-image evidence wave for KLS leftovers (2026-11-08)

Owner go: "Continue with both" (= W8b + W8c). Companion to B64 (W8c).

## What was probed

All 519 KLS raster-candidate leftovers (KLS_MISSING 514 + KLS_SHORT 5) from the
W7 re-audit. Every row's cited documents were read page-by-page:

- text-layer pages read directly (fast path; the dominant failure mode turned
  out to be **multi-level K prints** — "K1, K2" per CO — which W3's single-K
  regexes could not parse, stranding text-layer rows in the REX leftovers)
- raster-suspect pages (weak/empty text layer) rendered at 200 dpi and read
  with tesseract psm6 (deterministic OCR of the print — no model guess)
- persistent per-(sha,page) read cache: ~2,700 page reads across runs,
  178 unique pages OCR'd, heavy doc sharing across rows

## Toolchain incidents caught and fixed during the wave (audit-grade lessons)

1. Mixed citation sha lengths (12-char legacy + 16-char) — resolver by unique prefix.
2. Multi-level K prints joined "Ka/Kb" per catalog convention (125 committed rows
   already use it; auditor KLS_BADVAL accepts the composite).
3. Compendium false-match: the legacy CO→K pair regex spanned newlines and matched
   a Computer Graphics table inside a cyber-security course PDF — the PAIR fallback
   was REMOVED; replaced by a block state-machine (CO marker opens a block; K tokens
   join it; legend/section lines close it) with max_CO == co_count exactness.
4. Zero-guess attribution gate: a K table is accepted only when >=2 distinct
   subject-name tokens appear on the same page (title affinity >= 2).

## Disposition of the 519

| Outcome | Rows | Handling |
|---|---|---|
| sequence_found + title-verified | 2 | applied (below) |
| probed: no recoverable printed K sequence | 498 | NO data change; flag reclassified fix:W3 → needs_review with probe verdict (auditor upgrade in audit_rules.py bakes this into future re-audits) |
| cited doc not locally resolvable (post-reset; 3 shas: 79a6daf1f0cd9310, 2615fceb4d68, e18a3256f09b7f6e) | 19 | NO data change; needs_review with re-supply note |

## Applied — 2 rows, 2 edits (RULES §6b, before preserved in corrections_json)

- engineering-graphics-design-lab: co_kls (empty) → ["K2","K2","K2","K2","K2","K3"]
  — text-layer pp read of cited doc, CO1..CO6 printed with K column, title affinity 2.
- project-management-mba: invalid legacy non-JSON co_kls string (contained
  impossible "K7" tokens) → ["K2/K1/K3","K2/K4/K6","K3/K4/K5","K4/K5"] — verbatim
  printed table, title affinity 2; legacy garbage preserved in corrections_json.

## Post-wave audit (regenerated from the updated CSV)

Flags 5844 → **5399** (−445): TYPE_RAW 514→71 (B64), KLS_MISSING 514→512 (B65),
517 KLS flags now carry needs_review probe verdicts. Remaining evidence-read
classes unchanged: BOOK_TRUNC 574, CREDIT/MARKS/SESS 401, TYPE_EMPTY 521
(accepted-print honest nulls), PUNCT_ARTIFACT 3281 (guarded), BOOK_MERGED 6,
KLS_SHORT 5, TOKEN_N_LOWER 26, DISPLAY_MISSING 2.

## Gates

G1 PASS / G2 PASS codes=6412 / G3 PASS / G6 PASS (zero deferrals; both edits
probe-evidenced, G6 containment untouched — unit texts byte-identical).

## Transparency

T2T calls: 0 (deterministic wave; mercury-3 has no image-capable client in this
workspace — OCR is the image-evidence path). Keys: 5/5 untouched, 0 calls, 0
cooldowns, 0 exit-3. OCR/read failures: none blocking; 19 rows await doc re-supply.
No rr_sid assignments; no new keys; zero-guess discipline held throughout.
