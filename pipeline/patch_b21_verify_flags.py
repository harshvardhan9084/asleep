#!/usr/bin/env python3
"""patch_b21_verify_flags.py — B21 draft patches for the 2 first-run verifier
hard failures, each with the printed evidence recorded (B20 patch precedent:
patch at draft level, never invent, re-run verifier after).

FAIL 1 — doc 03 `General Proficiency: no units` (AGP151/AGP251, 2026-27
  course-structure doc): the 101-page print carries NO unit-wise course
  content and NO Course Outcomes for General Proficiency anywhere — its only
  detail is a dedicated "STANDARD OPERATING PROCEDURE (SoP) for General
  Proficiency" (pp.94-96) whose printed objectives (5 items), assessment
  components (5x10 marks), scope, evaluation process, grading and NEP-2020
  alignment were transcribed verbatim under objectives_print / *_print keys
  and containment-checked by the draft subagent. This is the recorded v14/B19
  print class `objectives_only_no_units_printed` ("detailed page whose entire
  content is an Objectives list — NO unit theory and NO experiment list
  anywhere in the document"): zero-guess forbids inventing units; verifier
  downgrades to WARN with the flag cited when objectives_print is non-empty
  (it is — 5 verbatim items). Existing flags no_unit_syllabus_printed /
  sop_only_detail stay (they name the SoP detail class); the B19 class flag
  is added so the verifier cites the documented print class.

FAIL 2 — doc 04 `Departmental Elective-I**: no codes` (2009-10 ECE, p.5
  S.No. 6 pool row): the printed Course Code cell is BLANK (draft subagent
  verified via word coordinates) — the row prints a name, L-T-P 3-1-0,
  credit 3, marks 25/50/75 and NO code; the printed "LIST OF ELECTIVES:
  Elective – I**" on the same page resolves the slot to EEC 011 / EEC 012 /
  EEC 013 / EIC 601, all four detailed elsewhere in the document as separate
  subjects. This is the recorded v10/B06 no-code print class ("a row printing
  NO codes anywhere; zero-guess forbids inventing codes; WARN with the flag
  cited"). The draft quirks said "Course Code cell is printed BLANK" but not
  the literal downgrade phrase — patch adds flag `no-code-printed` and extends
  the pool quirk with the "no code printed against this pool row" evidence
  phrase so the verifier cites the documented class (v10 remedy text).

Both patches are idempotent (flags/quirks only added when absent).
"""
import json, sys

D3 = "/home/z/my-project/work/pipeline_v2/drafts/03_btech_ece_course-structure_2026-27.draft.json"
D4 = "/home/z/my-project/work/pipeline_v2/drafts/04_btech_ece_syllabus_2009-10.draft.json"

n_patched = 0

d = json.load(open(D3))
for s in d.get("subjects", []):
    if s.get("name", "") == "General Proficiency":
        fl = s.setdefault("flags", [])
        if "objectives_only_no_units_printed" not in fl:
            fl.append("objectives_only_no_units_printed")
            s.setdefault("quirks", []).append(
                "Print-evidence class objectives_only_no_units_printed (B19 v14 "
                "remedy): NO unit-wise course content and NO CO table printed "
                "anywhere in the 101-page document for General Proficiency; the "
                "only printed detail is the SoP (pp.94-96) whose Objectives list "
                "(5 items, transcribed verbatim under objectives_print) is the "
                "entire course-content print. Zero-guess: units/cos omitted, not "
                "invented.")
            n_patched += 1
json.dump(d, open(D3, "w"), indent=1, ensure_ascii=False)

d = json.load(open(D4))
for s in d.get("subjects", []):
    if s.get("name", "").startswith("Departmental Elective-I"):
        fl = s.setdefault("flags", [])
        if "no-code-printed" not in fl:
            fl.append("no-code-printed")
            s.setdefault("quirks", []).append(
                "Print-evidence class no-code-printed (B06 v10 remedy): NO code "
                "printed against this pool row anywhere (scheme Course Code cell "
                "blank, verified via word coordinates); the slot resolves to the "
                "printed LIST OF ELECTIVES members EEC 011/EEC 012/EEC 013/EIC "
                "601, all detailed as separate subjects in this document. "
                "Zero-guess: no code invented.")
            n_patched += 1
json.dump(d, open(D4, "w"), indent=1, ensure_ascii=False)

print(f"PATCHED|{n_patched}")
sys.exit(0)
