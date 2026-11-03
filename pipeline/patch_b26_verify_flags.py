#!/usr/bin/env python3
"""patch_b26_verify_flags.py — B26 verify-remedy patches (recorded classes, evidence-recorded).

Remedies the first-pass verify FAILs (all printed-design classes recorded in
B02/B08/B17/B24/B25 manifests; zero-guess: only what the print shows):

1. no-code slot prints (doc02 OE-II/III/IV, doc03 Mini-Project-or-Internship/
   Open-Elective-I): evidence quirk carrying the literal print truth
   "no code printed ..." → verifier v10 no-code downgrade (B06 class).
2. project/assessment subjects with printed CO tables but no unitwise theory
   (doc04 BFT752/753/754/851): flag `co_only_no_units_printed` (recorded B08
   v11 class) + evidence quirk.
3. sessional/prose rows (doc05 EFT652/753/754/851, doc06 NFT-652, doc07
   NFT752/753/851/852, doc08 RFT-654): flag `detailed_syllabus_not_printed`
   (unitwise syllabus genuinely not printed; heading/prose description only)
   + evidence quirk citing the printed locator/prose.
4. doc05 Food-Biochemistry-&-Biotechnology-Lab experiments 9-13: the draft
   prefixed each item with the printed GROUP heading "Application of enzymes:"
   (print emits it once, before item 9, as "9-13. Application of enzymes:");
   per-item verbatim texts restored (B02 v2 verbatim-join class) + quirk.
"""
import json, sys

D = "/home/z/my-project/work/pipeline_v2/drafts/B26"
PATCHED = []


def patch(stem, match, *, flags=(), quirks=(), notes=None, exp_fix=False):
    path = f"{D}/{stem}.draft.json"
    d = json.load(open(path))
    hits = 0
    for s in d.get("subjects", []):
        if match(s.get("name", "")):
            fl = s.setdefault("flags", [])
            for f in flags:
                if f not in fl:
                    fl.append(f)
            q = s.setdefault("quirks", [])
            for qq in quirks:
                if qq not in q:
                    q.append(qq)
            if notes:
                n = s.setdefault("notes", [])
                if isinstance(n, list):
                    for nn in notes:
                        if nn not in n:
                            n.append(nn)
                else:
                    s["notes"] = [str(n)] + list(notes)
            if exp_fix:
                fixed = 0
                for ex in s.get("experiments", []):
                    t = ex.get("exp", "")
                    for pre in ("Application of enzymes: ", "Application of enzymes:"):
                        if t.startswith(pre):
                            ex["exp"] = t[len(pre):]
                            fixed += 1
                if fixed:
                    q.append("Experiments 9-13 print under the grouped heading "
                             "'9-13. Application of enzymes:' (text layer emits the heading "
                             "once before item 9); per-item verbatim texts restored "
                             "(patch-b26 verify remedy, B02 v2 verbatim-join class)")
                PATCHED.append(f"{stem}::{s.get('name')} exp_fixed={fixed}")
            PATCHED.append(f"{stem}::{s.get('name')} flags+={list(flags)} quirks+={len(quirks)}")
            hits += 1
    if hits != 1:
        print(f"WARN|{stem}|matches={hits} for {match}")
    with open(path, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)


NOCODE = ("no code printed on this scheme row (slot/assessment-level program-structure "
          "print; the printed row carries the name and credits only) — patch-b26 verify "
          "remedy (verifier v10 no-code evidence rule, B06 recorded class)")
CO_ONLY_Q = ("project/assessment course: the printed Course-Details page carries a CO "
             "table (+ objectives prose) and NO unitwise theory anywhere in the document "
             "(recorded B08 v11 class; zero-guess forbids inventing units) — patch-b26 "
             "verify remedy")
PROSE_Q = ("sessional/prose row: the document prints a heading + prose description only; "
           "no unitwise detailed syllabus is printed anywhere in the document (recorded "
           "B17/B24 detailed_syllabus_prose class; zero-guess forbids inventing units) — "
           "patch-b26 verify remedy")

# doc02: Open Elective – II [Annexure – B(iv)] / III / IV (no codes, scheme-only flagged)
patch("02_btech_env_y4_syllabus_2021-22",
      lambda n: n.startswith("Open Elective"), quirks=[NOCODE])
# doc03: Mini Project or Internship Assessment* / Open Elective-I (no codes)
patch("03_btech_ft_s5-6_syllabus_2024-25",
      lambda n: n in ("Mini Project or Internship Assessment*", "Open Elective-I"),
      quirks=[NOCODE])
# doc04: BFT752/753/754/851 project/assessment rows (cos=6, objectives_print present)
patch("04_btech_ft_s7-8_syllabus_2025-26",
      lambda n: n in ("Mini Project of Internship Assessment", "Project - I",
                      "Startup and Entrepreneurial Activity Assessment", "Project - II"),
      flags=["co_only_no_units_printed"], quirks=[CO_ONLY_Q])
# doc05: sessional rows EFT652 Seminar (p.29), EFT753 Project (p.34 prose), EFT754
# IT Viva (p.34 heading), EFT851 Project (p.39 prose)
patch("05_btech_ft_syllabus-rev_2009-10",
      lambda n: n in ("Seminar", "Project ( Dissertation)", "Industrial Training Viva Voce**",
                      "Project"),
      flags=["detailed_syllabus_not_printed"], quirks=[PROSE_Q],
      notes=["Printed design: EFT-652 SEMINAR (p.29), EFT-753: PROJECT (p.34: 'The student(s) "
             "will be required to search literature pertaining to design of an equipment / "
             "processing of a food commodity / production of food product, comprehend it and "
             "prepare a report for assessment.'), EFT-754: INDUSTRIAL TRAINING (p.34 heading), "
             "EFT-851 PROJECT (p.39: 'prepare a detailed project report on fabrication of an "
             "equipment / establishment of a plant ... for assessment.') — prose only, no "
             "unitwise syllabus printed"])
# doc05: Food Biochemistry & Biotechnology Lab grouped-heading experiment fix
patch("05_btech_ft_syllabus-rev_2009-10",
      lambda n: "Food Biochemistry" in n and "Lab" in n, exp_fix=True)
# doc06: NFT-652 Seminar (p.13 printed description, in notes)
patch("06_btech_ft_syllabus_2015-16", lambda n: n == "Seminar",
      flags=["detailed_syllabus_not_printed"], quirks=[PROSE_Q])
# doc07: NFT752/753/851/852 (parent scheme rows already in notes)
patch("07_btech_ft_syllabus_2016-17",
      lambda n: n in ("Industrial Training", "Project", "Seminar"),
      flags=["detailed_syllabus_not_printed"], quirks=[PROSE_Q])
# doc08: RFT-654 CASE STUDY (p.12 prose, in notes)
patch("08_btech_ft_syllabus_2018-19", lambda n: n == "CASE STUDY",
      flags=["detailed_syllabus_not_printed"], quirks=[PROSE_Q])

print(f"PATCHED|{len(PATCHED)}")
for p in PATCHED:
    print("PATCH|", p)
