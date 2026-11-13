# B94 — W12a noted-typo fix pass (owner directive D2, 2026-11-13)

- Run: `CRON-20261113-B94` (owner interactive message, same day)
- Trigger: owner read the `notes` column, asked what it is and why noted
  typos/errors were still stale ("should OBVIOUSLY have been fixed later").

## What the notes are (answer on record)

`notes` (3,070/3,080 filled) is the provenance/quirk-evidence surface written
during drafting+verification: printed-glue repairs, cross-document artifacts,
scheme-vs-detailed-syllabus heading conflicts, and printed-typo documentation
("'Warshal'/'Dijikstra' kept as-is"). §6b keeps notes verbatim forever.

## Root cause of the staleness (honest)

RULES §6b (owner directive D1, 2026-11-08) already said: FIX known
misspellings in PRIMARY fields, keep the printed form in evidence surfaces +
corrections_json "before". The drafting-era notes said "kept as-is" (pre-D1
convention), and no cascade wave (W9a/W11a/B91-B92 audited truncation,
emptiness, CO-duplication — not spelling compliance) ever reconciled the two.
Result: 1,600 rows' notes documented typos that §6b required fixed. Owner
directive D2 (2026-11-13) closed the gap.

## What D2/B94 changed (W12a)

- Curated map of 76 fix patterns (59 hit): famous algorithm/author names
  (Ardunio→Arduino x8, Tannenbaum→Tanenbaum x10+3 Tenanuanbaum, willey/Wiely
  →Wiley x30, Addision→Addison x18, Schieldt→Schildt x4, Warshal→Warshall,
  Dijikstra→Dijkstra, Halestead→Halstead, Apaydin→Alpaydin, Normal Maltoff→
  Norman Matloff, Siman Haykin→Simon Haykin, MOFET→MOSFET, ...), unambiguous
  English/domain words (Paranayama→Pranayama, Mitrochondria→Mitochondria,
  Debantures→Debentures, serializablity→serializability, ...), casing fixes
  (SQl→SQL, Lscm→LSCM).
- Context-dependent token Deprecation→Depreciation row-gated to the row whose
  own notes flag it (KMBAI204, accounting context — same line already prints
  "Causes of Depreciation").
- Excluded as legitimate (checked with word boundaries): 'fundamental',
  'lab', 'SQL' (correct casing), 'ad hoc'/'Adhoc', 'convertor' (accepted
  variant), 'Prentice Hall', 'Cardiovascular', 'ligand', etc.
- 125 rows changed, 159 corrections_json entries
  (rule=W12A_NOTED_TYPO_FIXED, before = printed spelling, evidence = D2).
- Notes: ONE appended clause per changed row ("W12a (owner directive D2
  2026-11-13): noted typo(s) ... FIXED in primary fields per RULES §6b ...");
  historical note text untouched (§6b evidence surface stays verbatim).
- G6 guard: no fix touched any unit1_text[:40] needle region (0 skips).

## Gates + audit

- G1 PASS (3,080×62) | G2 PASS codes=6412 (unchanged) | G3 PASS |
  G6 PASS containment_checks=123 (3 recorded OCR_PRIOR_SKIP rows unchanged).
- audit_rules.py post-write: **0 rows / 0 flags** (BOOK_TRUNC 0, TYPE_EMPTY 0).
- Post-sweep leftover scan over all 76 patterns in unit/co/structured text:
  0 occurrences remain. 'perceptron'/'SQL' etc. correct-form counts unchanged.
- Post-reset restore discipline held: 37th reset recovered this run (foreign
  .env isolated; 7-key .env rebuilt; repo HEAD 5e7fc2d = B93 verified vs
  remote; CSV re-synced md5-verified BEFORE the B94 write).

## CSV state

- download/art_d_final/syllabus_extreme_rich.csv: 3,080 rows × 62 cols.
- First apply attempt was rolled back via backup (unit/co write-back bug:
  structured fixes landed, unit/co computed-but-not-assigned). Root-caused,
  script fixed (row[c] = new write-back), CSV restored from
  work/pipeline_v2/backup/syllabus_preB94.csv (md5 e21e81fb…), re-applied
  once from clean state. No double corrections entries (rebuilt from pre-state).
- Registry: flags-of-record 0/0; next batch B95.
