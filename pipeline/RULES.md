# RULES.md — AKTU Syllabus Catalog Pipeline v2 (Constitution)

Restored 2026-10-27 from the recorded project spec after a workspace reset wiped
the original pipeline session artifacts. The rules below are the constitution;
every script and every subagent obeys them. Batch 01 of the original run
(CRON-20261027-B01) executed end-to-end before the reset; nothing it wrote
survived, so the restored pipeline re-runs deterministically from the same rules.

## §1 Directive

- Project: the official structured syllabus catalog for the whole internet —
  an open-source dataset (owner: harshvardhan9084).
- Scope: 5 courses — BTech, BPharm, BCA, MCA, MBA — course → branch →
  year/semester → five code generations (A/B/K/R/M) → verbatim unit-level
  syllabi.
- Primary registry: `/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv`
  (currently 97 rows × 57 cols; 4 row_kinds: subject / elective_pool /
  program_rule / semester_summary).
- Invariants: zero-guessing; zero GAP (extra rows are acceptable, missing
  subjects are not); full provenance; subject-first define-once registry
  WITHIN a course (see §1b); idempotency (one row per subject per course);
  `rr_sid` is assigned by the owner at the very end — NEVER by the pipeline;
  the two released companion PDFs
  (Common-Subjects-2nd-Year-AKTU-08092023.pdf, Open-Elective-BTech-2nd-year-2023-08092023.pdf)
  MUST be included (owner release recorded in the project charter; their earlier
  quarantine predates the release).

## §1b Course boundary (HARD RULE, owner directive 2026-10-28)

- Course boundaries are REAL. `course_name` is part of a subject's identity:
  the same (or very similar) subject name appearing in two different courses
  is TWO DIFFERENT subjects and MUST be two different rows.
- NEVER merge, UPDATE, or Tier-0/1/2-match a draft subject into a row of a
  DIFFERENT course — not on code identity, not on name identity, not on
  content evidence. (Supersedes the former "cross-course merges require
  content evidence" carve-out in §3.)
- Cross-course collisions (same/similar name, same/related code) are recorded
  as a note on the newly appended row (`same name as <course> subject_id
  <sid> — kept separate per course-boundary rule`); the existing row of the
  other course is never modified.
- Canonical course names (every row, every write): BTech, BPharm, BCA, MCA,
  MBA. Variants in source prints ("B.Tech", "B.Tech.", "B Tech") normalize to
  the canonical form in the data; the verbatim print stays in a `*_print`
  column or notes.

## §1c GitHub-referenced change tracking (owner directive 2026-10-28)

- The GitHub repo (harshvardhan9084/asleep) is the durable record of every
  run; local state can be lost to workspace resets, GitHub cannot.
- Every successful batch commit is pushed to `syllabus_catalog/` with:
  1. the updated `syllabus_extreme_rich.csv`,
  2. `CHANGELOG.md` — one append-only entry per push: run id, UTC time,
     batch, rows/codes/subjects delta (computed from the git diff), updates
     vs appends vs repairs, flags adjudicated, gate results,
  3. `runs/<UTC-ts>_<batch>_<slug>.md` — the run manifest (the worklog
     batch section, so run narratives survive resets),
  4. `pipeline/` — the versioned toolchain (RULES.md + scripts) actually
     used by the run, so each run's exact logic is referenced.
- Commit message format: `catalog(<batch>) run=<run-id>: rows A→B, codes
  X→Y (+a appends, ~u updates, !r repairs)`; the run id is the worklog Task
  ID (e.g. CRON-20261028-B03). GitHub `git log` + CHANGELOG.md are then the
  authoritative per-run change history.

## §2 Deterministic matching ladder

Applied per draft subject against the current CSV. Stop at the first tier that
resolves uniquely. `norm(code)` = uppercase, strip spaces/dashes. Tier 0
identity matching considers ONLY exact codes present in a row's
`primary_code | all_codes | code_history_all` (semicolon-separated tokens) —
never wildcard patterns (`BOE3**`) or ranges (`KOE031-038`) which live in
`k_era_pool_codes`.

- **Tier 0 — code identity**: any draft code (normalized) equals a token in a
  row's all_codes/code_history/k_era_pool exact-token set → UPDATE that row.
  HARD GUARD (§1b): only if `canon_course(draft) == canon_course(row)`.
- **Tier 1 — exact name within course**: normalized subject_name equals the
  row's normalized subject_name and course_name matches → UPDATE.
- **Tier 2 — fuzzy**: same course, token-set-ratio(name) ≥ 85 AND unit/CO
  vocabulary overlap: score ≥ 92, or score ≥ 85 with overlap ≥ 3 shared
  distinctive terms → UPDATE.
- **Tier 3 — APPEND**: no tier resolved. If the normalized name (or a
  normalized code) of a Tier-3 subject matches a row of a DIFFERENT course,
  emit flag `CROSS-COURSE-KEEP-SEPARATE` and record the cross-reference note
  on the appended row (§1b) — never update the other course's row.
- 2+ equally-scoring candidates at Tier 1/2 → flag `needs_review` (never guess).

## §3 Complete + Latest field policies

- Newer-session documents win FIELD-WISE (units, COs, books, L-T-P, credits,
  marks): when draft.session ≥ row.effective_session_latest, draft text
  replaces row text; else the draft may only BACKFILL fields that are empty.
- Older documents never overwrite; they corroborate and extend
  `code_history_all` / `source_history`.
- Printed forms live in the `*_print` columns verbatim (subject_name_print,
  eligibility_print, objectives_print, evaluation_note).
- Every change to a row appends to `change_note_vs_previous` and
  `source_history` with the document identity + locator.
- Labs are distinct rows (a lab subject is not merged into its theory pair).
- **NEVER merge across courses** (§1b): course boundaries are real; identical
  names in different courses are different subjects. Cross-course similarity
  is documented as a cross-reference note, never as a merge or update.

## §4 Brain clause

- When evidence is CONCLUSIVE, change the data immediately and keep the printed
  evidence in a `*_print` column or notes ("determine-then-fix, keep proof").
- When evidence is inconclusive, do NOT guess: put the row's question in
  `notes` with `needs_review`, and continue.

## §5 Gates (commit blockers)

- **G1 schema**: header equals the 57-column reference header exactly (order
  preserved). No column may be added/removed/reordered by the pipeline.
- **G2 code idempotency** (scoped per course, §1b): within each course, every
  specific code token (regex `^[A-Z]{2,4}[0-9]{3}[A-Z]?$`) is owned by
  EXACTLY ONE row across primary_code + all_codes. The SAME printed code may
  be owned by one row in EACH course when both courses' schemes print it
  (recorded B3 evidence: BVE301 Universal Human Values in BTech 2nd-yr common
  AND BCA y2 2025-26). Wildcards/pool ranges are exempt.
- **G3 subject idempotency**: subject_id unique; (subject_name, course_name)
  unique; every row's primary_code ∈ its own all_codes.
- **G6 provenance**: every touched row has non-empty source_syllabus and
  source_scheme_line; spot-check containment: unit1's first 40 normalized
  characters must appear in the parsed fulltext of the cited source PDF.
- Commit aborts (exit 2) on any gate failure or any unadjudicated
  `needs_review` flag. Fix drafts/decisions and re-run until COMMIT OK.

## §6 Text-layer policy

- The text layer (PyMuPDF) is the primary source. If it is garbled, check the
  PAGE IMAGE (Read tool renders PDF pages): the visible print is authoritative.
- PyMuPDF may silently drop off-page fragments; transcribe the visible print
  and record dropped/garbled fragments in the row's notes as print-quirk
  evidence.
- Keep printed typos verbatim ('SQl', 'HandlingHTTP', etc.) — record a quirk
  note; never silently correct print.

## §7 Draft spec (drafts/NN_<stem>.draft.json)

```json
{
  "pdf_rel": "<queue rel>", "session": "<YYYY-YY>", "course": "<BTech|...>",
  "sha16": "<first 16 hex of md5>", "stem": "<NN_stem>",
  "subjects": [
    { "name": "...", "name_print": "...", "codes": ["BCC301","BCC401"],
      "semester": 3, "ltp": {"l":3,"t":1,"p":0}, "credit": 4,
      "marks": {"sessional_ct":15,"sessional_ta":10,"sessional_total":25,
                 "ese_te_pe":75,"total":100},
      "subject_type": "core|value-added|open-elective|...",
      "units": {"1": "<verbatim unit text>", "...": "..."},
      "lectures_per_unit": 8,
      "cos": [{"no":1,"text":"...","kl":"K1"}],
      "textbooks": [{"no":1,"book":"..."}],
      "reference_books": [{"no":1,"book":"..."}],
      "experiments": [{"no":1,"exp":"..."}],
      "objectives_print": ["..."], "eligibility_print": "...",
      "prerequisites": "...", "quirks": ["..."], "flags": [] }
  ],
  "non_subject_rows": [ {"kind":"...","print":"...","locator":"..."} ],
  "quirks": ["..."], "flags": []
}
```

- Every extracted string is verbatim from the PDF (units, COs, books,
  eligibility, objectives). Zero guessing; blank means printed-blank.
- Subagents append subjects to the draft INCREMENTALLY (python json rewrite
  after each subject) so a lost final message never loses extracted data.

## §8 Subagent protocol

- One general-purpose subagent per PDF, cap 5 concurrent.
- The subagent reads `draft_prompt.md` with variables filled: PDF_PATH,
  PDF_REL, PARSED_JSON, FULLTEXT, DRAFT_OUT, SESSION.
- Work incrementally; keep the FINAL MESSAGE ≤ 6-10 lines (long finals have
  caused transport timeouts; a lost final ≠ a lost draft — check DRAFT_OUT).
- If a Task call fails with 'response is empty' / 'context deadline exceeded',
  retry ONCE with the same prompt.

## §9 Queue state machine

`pending-pinned → pending → selected → done | failed(<reason>)`
- select_batch: pending-pinned first (filename ASC), then pending (session
  DESC, no-session last, filename ASC); md5 content-dedup vs done/failed and
  within the batch; ≤ 10 per batch; missing files are skipped with SKIP_MISSING
  (status untouched).
- mark_done: exact queue rels printed by select_batch; failures recorded as
  `failed(<reason>)` (e.g. non-syllabus regulations/datesheet docs).
- All decisions append-only in queue meta.history.

## §10 Provenance

- Every fact carries its document: `source_syllabus` =
  `<pdf filename>#<sha16> pp.<locator>`; `source_scheme_line` = the verbatim
  printed scheme row; `source_history` accumulates every corroborating doc.
- The two released companion PDFs cite
  `work/artd_v3/sources/<file>#<sha16>`.

## §11 Prohibitions

- NEVER assign rr_sid. NEVER invent codes, names, units, COs, books, marks.
- NEVER merge two different subjects to save a row; never split one subject
  into two rows.
- NEVER merge or update across courses (§1b) — course boundaries are real.
- NEVER write a non-canonical course_name (§1b canon: BTech/BPharm/BCA/MCA/
  MBA); apply_update never overwrites course_name.
- NEVER silently skip a flagged subject — adjudicate via RESOLVE_APPEND or
  flag needs_review in row notes and continue.
- NEVER ask the user anything during an automated batch run — flag and
  continue.
- NEVER write rows of row_kind other than `subject` (non-subject rows stay in
  drafts pending the owner's migration instruction; the existing 97-row layout
  is frozen until then).
