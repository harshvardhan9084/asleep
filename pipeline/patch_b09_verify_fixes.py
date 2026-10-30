#!/usr/bin/env python3
"""patch_b09_verify_fixes.py — B09 verify-failure remedies (evidence-recorded).

(a) doc06 (btech_au_syllabus_2009-10): the draft subagent inserted editorial
    bracketed notes INTO unit text — violates §7 verbatim discipline (the
    evidence already lives in the subjects' quirks, added at extraction time
    after page-image checks):
      - Mathematics-III unit1: '[formula dropped by text layer]' ×2 (p.8
        integral formulas dropped by PyMuPDF; quirk already records them).
      - Optimization for Engineering Design unit2: '[continuation of Unit-I
        sentence in print; printed as UNIT-II]' (quirk already records the
        printed sentence split).
    Remedy: strip the insertions from unit text (verbatim words only).

(b) doc01/doc02 project & mini-project subjects (KCS354/KCS554/KCS752,
    KCS753/KCS851, BCS752, BCS753/BCS851): print a real CO table (CO1-CO5 +
    KL, containment-verified against fulltext) and NO unit theory anywhere —
    the B08 v11 remedy class co_only_no_units_printed. Fulltext evidence:
    'Course Outcome (CO) / Bloom's Knowledge Level (KL)' tables at the
    detailed sections; no UNIT headings on those pages.

(c) doc09 'Advanced Welding Technology': no code printed anywhere — elective
    pool prints '5. Advanced welding Technology' (name only, numbers 1-5, no
    code column) and the detail heading 'ADVANCED WELDING TECHNOLOGY' carries
    Unit-I..V + Books with no code line (2018-19 format: no COs either).
    v10 no-code remedy: flag must carry the 'no-code' evidence string.
"""
import json, os, sys

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"


def load(stem):
    p = os.path.join(DRAFTS, stem + ".draft.json")
    return json.load(open(p)), p


def save(d, p):
    with open(p, "w") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def fix_doc06():
    stem = "06_btech_au_syllabus_2009-10"
    d, p = load(stem)
    n = 0
    for s in d["subjects"]:
        if s.get("name") == "Mathematics-III":
            u1 = s["units"].get("1", "")
            if "[formula dropped by text layer]" in u1:
                s["units"]["1"] = u1.replace(
                    "the type [formula dropped by text layer] and [formula dropped by text layer].",
                    "the type and .")
                s.setdefault("quirks", []).append(
                    "B09 verify fix: bracketed '[formula dropped by text layer]' editor notes "
                    "removed from unit1 text per §7 verbatim discipline (evidence quirk above; "
                    "print p.8 shows two integral formulas PyMuPDF drops — patch_b09_verify_fixes.py).")
                n += 1
        if s.get("name") == "Optimization for Engineering Design":
            u2 = s["units"].get("2", "")
            if "[continuation of Unit-I sentence in print" in u2:
                s["units"]["2"] = u2.split(" [continuation of Unit-I sentence in print")[0]
                s.setdefault("quirks", []).append(
                    "B09 verify fix: bracketed '[continuation of Unit-I sentence...]' editor note "
                    "removed from unit2 text per §7 verbatim discipline (evidence quirk above re the "
                    "printed UNIT-I/UNIT-II sentence split — patch_b09_verify_fixes.py).")
                n += 1
    save(d, p)
    print(f"doc06 fixed_units|{n}")


def add_co_only(stem, names):
    d, p = load(stem)
    n = 0
    for s in d["subjects"]:
        if s.get("name") in names:
            fl = s.setdefault("flags", [])
            if "co_only_no_units_printed" not in fl:
                fl.append("co_only_no_units_printed")
                s.setdefault("quirks", []).append(
                    "B09 verify fix: flagged co_only_no_units_printed — detailed section prints a real "
                    "CO table (CO1-CO5 with Bloom's KL) and NO unit theory anywhere in the document "
                    "(B08 v11 remedy class; fulltext containment-verified — patch_b09_verify_fixes.py).")
                n += 1
    save(d, p)
    print(f"{stem} co_only_flagged|{n}")


def fix_doc09():
    stem = "09_btech_au_y3_syllabus_2018-19"
    d, p = load(stem)
    n = 0
    for s in d["subjects"]:
        if s.get("name") == "Advanced Welding Technology":
            fl = s.setdefault("flags", [])
            if not any("no-code" in str(f).lower() or "no code" in str(f).lower() for f in fl):
                fl.append("no-code-printed-anywhere")
                s.setdefault("quirks", []).append(
                    "B09 verify fix: flagged no-code-printed-anywhere — elective pool prints "
                    "'5. Advanced welding Technology' (name only, no code column) and the detail "
                    "heading 'ADVANCED WELDING TECHNOLOGY' carries Unit-I..V + Books with no code "
                    "line (2018-19 format, no COs printed either) — patch_b09_verify_fixes.py.")
                n += 1
    save(d, p)
    print(f"{stem} no_code_flagged|{n}")


def main():
    fix_doc06()
    add_co_only("01_btech_ai-ml_y4_syllabus_2024-25",
                {"Mini Project or Internship Assessment", "Project"})
    add_co_only("02_btech_ai-ml_y4_syllabus_2025-26",
                {"Project", "Mini Project or Internship Assessment"})
    fix_doc09()
    return 0


if __name__ == "__main__":
    sys.exit(main())
