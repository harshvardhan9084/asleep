#!/usr/bin/env python3
"""fix_draft_flags_b03.py — B03 post-verify remediations with recorded evidence.

1) draft 03 "Elementary Mathematics Bridge Course" (BBC107/BBC207): the document
   prints no units/CO/books for it anywhere (subject quirk records this; the
   detail pages live in the separate bridge-course doc 01). Add the canonical
   verifier flags "scheme-only" + "detailed_syllabus_not_printed" — truthful,
   matches the printed reality of THIS document.
2) draft 04 "Sports and Yoga-II" (BVA451): subject quirk records "No CO table,
   no Unit-I..V syllabus and no book list printed for this course" (p.38-39
   print is guideline body, not unit syllabus). Add the same two flags.
3) draft 09 "Pharmaceutical Jurisprudence Project (Case Studies)" (BOP-245P)
   and "Human Value & Professional Ethics/Cyber Security" (AUC-001/AUC-002):
   fulltext audit shows both print ONLY as scheme rows (BOP-245P: 0-2 periods,
   30/70/100, credit 2; AUC-001/002: compulsory audit course footnote "*Human
   values & Professional Ethics /Cyber Security will be offered as a compulsory
   audit course..."). No units/COs/experiments printed. Add the two flags.
"""
import json

BASE = "/home/z/my-project/work/pipeline_v2/drafts"
FLAGS = ["scheme-only", "detailed_syllabus_not_printed"]


def add_flags(stem, match_name, note):
    p = f"{BASE}/{stem}.draft.json"
    d = json.load(open(p))
    hit = False
    for s in d["subjects"]:
        if s.get("name", "").lower() == match_name:
            fl = s.setdefault("flags", [])
            for f in FLAGS:
                if f not in fl:
                    fl.append(f)
            s.setdefault("quirks", []).append(note)
            hit = True
    json.dump(d, open(p, "w"), ensure_ascii=False, indent=1)
    print(f"FIX|{stem}|{match_name}|{'OK' if hit else 'NOT FOUND'}")


add_flags("03_bca_y1_syllabus_2025-26", "elementary mathematics bridge course",
          "verifier flag added: this document prints no units/CO/books for the bridge course "
          "(scheme rows in both semester tables only, credit '-'); its detail pages are printed "
          "in the separate 2pp bridge-course document (queue rel repo_asleep/PDFs/5-course/"
          "2025-26/bca_s1-2_bbc107-207-non-credit-bridge-course_2025-26.pdf, ingested in this batch)")
add_flags("04_bca_y2_syllabus_2025-26", "sports and yoga-ii",
          "verifier flag added: no CO table, no Unit-I..V syllabus and no book list printed for "
          "this course in this document (p.2 scheme row + p.38-39 guideline body only; the "
          "guideline body is program-structure print, not a unit syllabus)")
add_flags("09_bpharm_y1-2_syllabus_2013-14", "pharmaceutical jurisprudence project (case studies)",
          "verifier flag added: prints only as semester-IV scheme rows (pp.4-5: 0-2 periods, "
          "30/70/100, credit 2); no unit/CO/experiment print anywhere in the document")
add_flags("09_bpharm_y1-2_syllabus_2013-14", "human value & professional ethics/cyber security",
          "verifier flag added: compulsory audit course printed only as scheme rows (pp.4-5) + "
          "audit footnote '*Human values & Professional Ethics /Cyber Security will be offered "
          "as a compulsory audit course...'; one row carries both printed code alternatives "
          "AUC-001/AUC-002 (the '/' alternative print is the subject's printed identity)")
