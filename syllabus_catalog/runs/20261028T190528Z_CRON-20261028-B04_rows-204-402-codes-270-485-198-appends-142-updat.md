# Run manifest — CRON-20261028-B04 — batch B04 — 2026-10-29

Summary: B04 (resumed after a full workspace reset rolled local files back to the Oct-27 B02 state; rebuilt from GitHub baseline 2f551ad per RULES §1c): rows 204→402, codes 270→485 exact-owned, +198 BCA/BPharm subject-row appends, ~142 BPharm updates across 4 code eras, 2 regulations-only docs quarantined as failed(non-syllabus), G2/G3 pool+code-reuse evolutions, PUSH FAILED (no GitHub PAT in restored workspace — recorded per RULES §1c, exit non-zero).

Registry deltas: rows 204→402; subjects by course: BTech 122→122, BCA 30→46, BPharm 40→222; codes 270→485; backup pre_commit_2026-10-28T183915p0000.csv

---

# Run manifest — CRON-20261028-B04 — batch 04 (BCA y3 2026-27 + BPharm corpus wave)

Task ID: CRON-20261028-B04 — Job 480444 — owner directives executed this run:
§1b course boundaries + §1c GitHub-referenced tracking + hourly cron.

## Context (workspace reset recovery)

The 2026-10-29 cron fire found the workspace rolled back to the Oct-27 B02
snapshot: work/repo_asleep, RULES §1b/§1c, push_catalog.sh, enqueue_corpus.py,
the course-scoped G2/RESOLVE_APPEND adjudications, the B03 worklog section and
all B04 wave-1 drafts were gone; .env held only DATABASE_URL (no GitHub PAT).
Recovery performed BEFORE any batch work, GitHub treated as authoritative
(RULES §1c):
- re-cloned github.com/harshvardhan9084/asleep → work/repo_asleep (644 files;
  re-cloned a second time mid-run after the directory was found emptied again)
- restored download/art_d_final/syllabus_extreme_rich.csv FROM GitHub (2f551ad,
  204 rows × 57 cols, codes 270) — verified census BTech 122 / BCA 30 / BPharm 40
- rewrote RULES §1b (course boundary hard rule) + §1c (GitHub-referenced
  change tracking) from the B03 runs/ manifests
- rebuilt enqueue_corpus.py (idempotent; rels relative to work/; 448 PDFs
  enqueued: BTech 352, MBA 50, MCA 25, BPharm 16, BCA 5) and push_catalog.sh
- re-applied the B03 merge_draft.py hardening: course-scoped G2, per-subject
  course_eff (COURSE-META-FROM-CODES defense), CROSS-COURSE-KEEP-SEPARATE
  crossref notes, append subject_id collision suffixing, RESOLVE_APPEND entries
  (COURSE-META-FROM-CODES / CROSS-COURSE-KEEP-SEPARATE / CODE-REASSIGNED-ACROSS-SESSIONS)
- pre-marked the 4 BCA rels already committed in B03 as done (never re-process)
- rebuilt the B03 worklog section from syllabus_catalog/runs/ (GitHub manifests)
- aligned queue batch_counter to 3 (B03 exists on GitHub) so this run selected
  as BATCH 04; 10 PDFs selected (session DESC): bca_y3 2026-27 + 9 BPharm docs

## Batch (10 PDFs: 1 BCA + 9 BPharm)

| # | doc (session) | pages | draft subjects |
|---|---------------|-------|----------------|
| 01 | bca_y3_syllabus_2026-27 (2026-27) | 27 | 16 (BBC501-652 + elective pool BBC011-015) |
| 02 | bpharm_ordinances_2019-20 (2019-20) | 25 | 0 — regulations-only; 61 non_subject_rows |
| 03 | bpharm_regulations-ordinances_2026-27 (2026-27) | 28 | 0 — regulations-only; 58 non_subject_rows |
| 04 | bpharm_scheme-syllabus_2026-27 (2026-27) | 295 | 121 (BP101T-BP816P + appendix elective pools) |
| 05 | bpharm_y1-2_syllabus_2013-14 (2013-14) | 51 | 40 (BOP-111…BOP-245P, old-era codes) |
| 06 | bpharm_y1-4_syllabus_2019-20 (2019-20) | 149 | 83 (BP101T-BP816P, PCI era) |
| 07 | bpharm_y1_scheme_2016-17 (2016-17) | 25 | 20 (RPH-101…RPH-210P era) |
| 08 | bpharm_y1_syllabus_2017-18 (2017-18) | 46 | 23 (BP101T-BP210P, early-PCI era) |
| 09 | bpharm_y2_scheme-syllabus_2017-18 (2017-18) | 33 | 17 (BP301T-BP409P) |
| 10 | bpharm_y2_scheme-syllabus_2017-18_2 (2017-18) | 22 | 20 (RPH301-410 + RCA305 + RVE401) |

Subagent protocol: cap-5 waves; 04 (295pp) hit the context deadline but its
incremental on-disk draft survived COMPLETE (121 subjects, 686 KB) — no re-run
needed (§8: lost final ≠ lost draft); 05 needed the single §8 retry; 06 was
stopped once and resumed from its own on-disk partial (78→83 subjects).

## Verify (step 5) — every hard failure investigated

- 02/03 "no subjects" = regulations-only docs (correct zero-subject output;
  both quarantined failed(regulations-only) at step 7 with non_subject_rows
  preserved in their drafts for the owner's migration instruction).
- 04: 15 containment/GAP findings → (a) 8 page-break-junction pseudo-failures
  cured by verify v3 remedy (strip the repeated running header "B. Pharm.
  Syllabus" from containment haystacks — haystack-side only); (b) 3 subjects
  whose PyMuPDF text layer DROPPED printed bullet content (Bio-similars
  BP708T, Drug Store BP607T, Industrial Safety BP806T) — units re-transcribed
  VERBATIM from PAGE IMAGEs (RULES §6, visible print authoritative), evidence
  quirks recorded; (c) 4 no-units subjects = detail-header-only rows (Internship
  BP411I/BP612I, Research Project BP710RP) or appendix list rows (Professional
  Skills BP611P) — flagged scheme-only. Re-run: PASS.
- 06: 6 practice/training subjects (Hospital Training I/II, Practice School,
  Industrial Training/Tour reports, Project Work) print course content as
  PROSE with no Unit-I..V headings — prose keyed verbatim as unit 1 per the
  B03 BVA251 precedent; Practice School's 10 domains + 9 books transcribed.
  Re-run: PASS.
- 10: 1 scheme-paired-alternative project row (Pharmaceutical Jurisprudence
  Project RPH304P/RPH309P) — scheme-only flag. Re-run: PASS.

## Merge (live ladder, course-scoped) — COMMIT OK

PLANS 340: UPDATE 142, APPEND 198, TIE 0, SKIP 0. FLAGS 92, all adjudicated
with recorded reasoning. Gates: G1 PASS (57 cols), G2 PASS (course-scoped,
485 exact-owned codes), G3 PASS, G6 PASS (containment 119). rows 204 → 402.

New adjudications (all in merge_draft.py with recorded evidence):
1. DECISION_OVERRIDES (14 case-by-case entries): TIEs resolved on serial
   numeral + semester + printed-name semantics (A&P-I/II, Pharmaceutical
   Analysis-I, BP209P organic practical sem-2); 2 TIER2 fuzzy candidates
   rejected then FORCE-redirected to the true same-course ancestor (BP104T /
   RPH-101 inorganic chem-I → BOP-111 row); 4 TIER2 serial-subject candidates
   rejected to APPEND (organic-II/III must never merge into the organic-I row).
2. TIER2_ACCEPTED (4): same-course fuzzy matches with per-key evidence
   (BP202T=BOP-121 organic-I sem-2; RPH-206/202=BOP-121 overlap 95;
   RPH301 chem-IV heterocyclic=BOP-231 renumbered, overlap 85).
3. R1 PRACTICAL-KEEP-SEPARATE: a practical draft subject never merges into a
   theory/pool row (printed BPxxxT/BPxxxP split is law); a shared P-suffix
   code + name ratio ≥ 85 still allows the cross-era same-practical UPDATE.
4. R2 POOL-MEMBER-APPEND + G2 pool exception: AKTU's 2026-27 BPharm APPENDIX
   (p.220 "List of Recommended Electives (AEC/SEC/VAC courses to be prescribed
   by HEI)") assigns ONE code (BP212P/BP312P/BP607T/BP610P/BP611P/BP708T/
   BP806T/BP809P) to SEVERAL candidate courses, each detailed later in the
   appendix. Pool slot rows + every member append as separate rows; G2
   accepts a same-course multi-owner code when every owner carries the
   elective-pool marker (members' units/experiments preserved verbatim).
5. CODE-REUSE-APPEND + G2/G3 marker exception: AKTU REUSES BP1xx codes across
   curricula with different subjects (2017-18 BP107P=A&P practical vs 2019-20
   BP107P=General Pharmacy practical vs 2026-27 BP107P=General Pharmacy
   practical — three different print realities; likewise BP108P-BP111P,
   BP207P-BP210P). Era-distinct rows append with code-reuse evidence notes;
   G2/G3 accept a multi-owner code / era-duplicate name pair when either row
   carries the adjudication marker. 2017-18 TIEs (BP110P/BP207P/BP208P/BP210P)
   adjudicated case-by-case onto the 2019-20 same-subject rows (backfill only).

## Quirks (print evidence recorded in rows)

- 2026-27 BPharm text layer drops printed bullet lines on several elective
  pages (pp.265-266 etc.) — page-image re-transcriptions recorded.
- 2013-14 era prints "BOP- 244"/"BOP 245"/"BOP-232 P" spacing variants;
  BOP-122P's detail page omits its code line; dual "Chemistry-III" titles.
- 2019-20 heading "COMMU IUCATION SKILLS" typo (2017-18 "COMMUNIUCATION
  SKILLS") kept verbatim; 'Sodium nitrite333'; BP206T prints only Units I-III.
- BP411I/BP612I/BP710RP print as header-tables only (no syllabus content).
- Elective-slot codes BP611P VAC* and BP610P SEC* carry footnote "Only 1
  course shall be selected from each elective".

## Queue + census

- 8 rels marked done; 2 regulations-only docs failed(regulations-only).
- Postcommit census: 402 rows × 57 cols; subjects BTech 122 / BCA 46 /
  BPharm 222; JSON columns clean; 17 branches.
- 438 PDFs remain pending (next batches: MBA 50, MCA 25, BPharm 6, BCA 0,
  BTech 352 remaining + no_session_found).

## PUSH FAILURE (RULES §1c) — recorded, batch exits non-zero

push_catalog.sh could not authenticate: the workspace reset lost the GitHub
PAT (.env holds only DATABASE_URL; no GH_TOKEN/GITHUB_TOKEN in env; no
credential helper, no ~/.netrc, no ~/.ssh; the historical token in
scripts/verify_repo_sync.py is stored redacted). Push attempted per protocol
and retried once — both attempts fail with "could not read Username" (no
credentials). The local commit exists in work/repo_asleep; the REMOTE was NOT
updated. OWNER ACTION NEEDED: provide a fresh fine-grained PAT (GITHUB_PAT= in
.env) and re-run push_catalog.sh for B04 — the manifest (this file) and
CHANGELOG entry are prepared locally in syllabus_catalog/runs/.

## Open items

1. PUSH BLOCKED on owner PAT (above) — B04's registry changes are local-only
   until pushed; GitHub baseline remains 2f551ad.
2. Elective-pool member rows (AKTU 2026-27 appendix) share one code per pool —
   owner may want a visible pool/slot column or rr_sid grouping policy.
3. Cross-era code reuse (BP1xx in 2017-18/2019-20/2026-27) means "primary_code"
   is era-scoped; owner may want an era column or the code_history narratives
   reviewed (all reuse rows carry code-reuse notes).
4. 2016-17 RPH-era doc (07) prints COs never — rows carry units/experiments
   only (print-faithful).
5. non_subject_rows of this batch (245+ entries across 10 drafts incl. the two
   full ordinances docs) remain in drafts pending the owner's migration
   instruction (RULES §11 layout frozen).
6. rr_sid remains owner-assigned at the very end.
