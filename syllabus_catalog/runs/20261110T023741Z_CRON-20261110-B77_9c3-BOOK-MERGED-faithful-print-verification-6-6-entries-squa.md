# Manifest — CRON-20261110-B77 — W9c3 BOOK_MERGED faithful-print verification + audit v23

## Context
- Reset #60 on entry: routine restore executed (.env 7 keys restored — was a DB stub; repo @7cac5b2 B76, CSV md5 c52f7d5d verified; toolchain synced; corpus_map 613→610 shas; wave_state batch_next=77; w9a/w10c/w10c2 ckpts restored from repo runs/). Loop: NOOP (W3 queue 0; 0 T2T).

## W9c3 — BOOK_MERGED faithful-print verification (6 entries, 5 rows)
- The auditor's merged-citation heuristic (author(Year); Title / Author; Title…Publisher patterns) suspected 6 book entries of being two citations joined.
- Probe: full-entry squash-containment in the cited docs' text layers. **6/6 faithful_print** — every full entry sequence prints contiguously in its cited doc (page-cited): machine-design ref[5] @btech_au_syllabus_2020-21 p.26; additives-compounding tb[5]+ref[1] @btech_plastic_syllabus_2009-10 p.24; business-organisation ref[0] @mba-integrated_y2_2025-26 p.26; financial-derivatives ref[3] @mba-integrated_y5_2021-22 p.21; treasury-management ref[0] @mba_banking-fin-services_y2_2025-26 p.22. The "merged" look is AKTU's own print (Author; Title on one item).
- Disposition: recorded-honest flag drop (W9a/W9b semantics) — durable "W9c3 probe: faithful-print <col>[idx] @ cite" markers in notes; audit v23 scan-side skip per verified field. Zero data change.

## DISPLAY_MISSING (2) — honest deferral
- process-equipment-design + environmental-science-and-ethics are documented G6_CONTAINMENT_GAP rows (W7 zero-known-error report: unit text provable only in docs lost to workspace resets). A display-mirror field change trips the pre-existing G6 gap (reproduced live during this run's first apply attempt), so the mirror is DEFERRED: flags stay, durable deferral notes recorded. Fix blocked until the gap class is resolved (owner-facing).

## Audit v23
- BOOK_MERGED scan-side skip via notes marker (v21 W9a2 / v22 W9b2 class). First run missed because a `\b` after `]` in the marker regex never matches (non-word char) — fixed to lookahead `(?=\s|@|$)`; harness re-verified.

## Result
- Flags 900 → 894 (BOOK_MERGED 6→0); flagged rows 741 → 738. Notes-only diff verified cell-by-cell (7 cells, all `notes`, 0 out-of-scope). Gates G1/G2(6,412)/G3/G6 PASS (notes-only: probe set empty per the B74/B75 notes-are-not-content convention). w9c3_ckpt.json committed to runs/. CSV md5 c32cf5c0210f4f85ee24c6401ce8e856.
- T2T: 0 calls (deterministic local text-layer reads; mercury keys idle).

## Remaining flag classes (894)
TYPE_EMPTY 375, BOOK_TRUNC 144, CREDIT_FORMULA 129, SESS_SUM 123, MARKS_SUM 121, DISPLAY_MISSING 2 (G6-gap-blocked). Next candidates: BOOK_TRUNC OCR rounds (144), TYPE_EMPTY no-print page-image rounds (140), CREDIT/SESS/MARKS scheme page-image reads.
