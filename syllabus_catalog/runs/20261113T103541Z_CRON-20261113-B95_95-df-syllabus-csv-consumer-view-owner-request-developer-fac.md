# B95 — Developer-facing consumer view `df_syllabus.csv` + dataset diversity stats

- Run: `CRON-20261113-B95` (owner request, interactive, 2026-11-13)
- Zero writes to the of-record CSV: `syllabus_extreme_rich.csv` byte-identical
  to B94 HEAD (md5 323ffc13eb5bfe5887fdd819bea63a19); audit-of-record 0/0.

## What was built

`syllabus_catalog/df_syllabus.csv` — 3,080 rows x 44 columns, the OPEN-SOURCE
CONSUMER VIEW. Owner rule: a developer building on the dataset should never
need evidence surfaces. Dropped 18 of 62 columns:

- print/evidence surfaces: subject_name_print, subject_name_display (verified
  = the printed name with caps/asterisk artifacts; differs from the canonical
  subject_name on 1,670 rows), subject_category_print, eligibility_print,
  objectives_print
- internal provenance/citations: source_syllabus, source_scheme_line,
  source_history, change_note_vs_previous, evaluation_note
- quality/bookkeeping (owner-named + same class): notes, quality_flags,
  corrections_json, verification_status
- redundant variants: subject_type (kept the cleaned subject_type_norm),
  code_family (trivially derivable from primary_code), row_kind (all
  'subject'), status (all 'latest')

Kept 44: identifiers (subject_id, subject_name, primary_code, all_codes,
code_history_all), program placement (course_name, branch_names, program_year,
semester_slots, effective/first sessions), teaching metadata
(subject_type_norm, L/T/P, credit, sessional_ct/ta/total, ese_te_pe,
total_marks), learning content (has_detailed_syllabus, prerequisites,
co_count, co1..6_text, co_kls, units_count, lectures_per_unit, unit1..5_text),
resources (textbooks/reference/experiments structured arrays), electives
(choice_group_id/policy). Structured arrays verified JSON-parseable on every
row; no evidence column leaked.

## Dataset diversity stats (computed, saved in b95_stats.json)

- Courses: BTech 2,227 / MBA 338 / BPharm 268 / MCA 201 / BCA 46 rows.
- Branches: 61 distinct printed BTech branch strings -> 48 after normalizing
  print variants ('&'/'and', 'Engg.'/'Engineering'); MCA 15. BCA/BPharm/MBA
  prints carry no branch field. 1,072/2,227 BTech rows have empty
  branch_names (older era schemes do not print the branch).
- Cross-course subjects: 121 subject names taught in >1 course; 'Cyber
  Security' and 'Universal Human Values & Professional Ethics' taught in ALL
  5 courses; Python Programming / Data Structure / Technical Communication in
  3. Widest in BTech: Internship/Mini-Project, Discrete Structures & Theory
  of Logic, Operating System (+Lab) in 15-16 branches.
- Codes/eras: 7,219 distinct printed codes mapped onto 3,080 subjects (avg
  2.35 codes/subject, max 67 on one subject); sessions span 2004-05 to
  2026-27 (19 distinct sessions).
- Semester breadth (BTech, distinct subjects offered): sem-1 79, sem-2 45,
  sem-3 216, sem-4 198, sem-5 399, sem-6 427, sem-7 413, sem-8 199 —
  electives concentrate in sems 5-7.
- Typical subject: 3 credits (mode, 1,026 rows) or 4 credits (755); labs 1-2
  credits; total_marks 100 (1,315) / 150 (574) / 50 (388); dominant L-T-P
  3-0-0 and 3-1-0. Per-student timetables are NOT exactly reconstructible
  from the deduplicated catalog (recorded honestly).
- Content: 2,313 rows with detailed syllabus (9,898 unit texts); 6,678
  course outcomes; 6,885 textbook + 7,874 reference entries (1,319/1,415
  rows); 8,808 experiment entries (816 rows); 750 departmental-elective and
  101 open-elective rows; 17 choice groups.

## Record integrity note

Mid-task the 38th workspace reset hit (foreign .env isolated, 7-key .env
rebuilt, repo re-cloned). A suspected B94 schema regression (57 cols) was
investigated and DISPROVED: git 3796b85 CSV = 62 cols == B93; the 57-col
artifact was the stale post-reset local download file + a reverted seed
scripts/ module (REF_HEADER 57); both re-synced from HEAD. Local CSV restored
md5-verified before the df build. Batch numbering unaffected: next = B96.
