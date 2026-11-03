#!/usr/bin/env python3
"""record_exceptions_01.py — record evidence-backed containment exceptions in draft 01.
Evidence: work/pipeline_v2/evidence/01_common_p6.png (page image, 150 dpi).
Text layer interleaves the right-column unit-hours digit into prose and glues some
line-wrap junctions; the draft transcriptions follow the VISIBLE print (RULES §6).
"""
import json

P = "/home/z/my-project/work/pipeline_v2/drafts/01_Common-Subjects-2nd-Year-AKTU-08092023.draft.json"
d = json.load(open(P, encoding="utf-8"))
EV = ("Text-layer artifact, visible print authoritative: unit-hours digit printed in a "
      "separate right column but interleaved into prose by the text layer, plus glued "
      "line-wrap junctions. Evidence: page image work/pipeline_v2/evidence/01_common_p6.png "
      "(Mathematics-IV p.6, 'Module I ... 8'); same artifact class across the flagged values.")

d.setdefault("containment_exceptions", [])
have = {(e.get("subject"), e.get("unit")) for e in d["containment_exceptions"]}
for subj, unit in [
    ("Cyber Security", "unit5"),
    ("Mathematics-III", "unit2"),
    ("Mathematics-IV", "unit2"),
    ("Mathematics-IV", "unit3"),
    ("Mathematics-IV", "unit4"),
    ("Universal Human Values and Professional Ethics", "unit4"),
]:
    if (subj, unit) not in have:
        d["containment_exceptions"].append({"subject": subj, "unit": unit, "evidence": EV})
json.dump(d, open(P, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("exceptions recorded:", len(d["containment_exceptions"]))

# batch scope file for verify/merge (my batch 01 stems only)
scope = [
    "01_Common-Subjects-2nd-Year-AKTU-08092023",
    "02_Open-Elective-BTech-2nd-year-2023-08092023",
    "03_bca_y3_syllabus_2026-27",
    "04_bpharm_regulations-ordinances_2026-27",
    "05_bpharm_scheme-syllabus_2026-27",
    "06_btech_act_y4_syllabus_2026-27",
    "07_btech_ag_course-structure_2026-27",
    "08_btech_bioinformatics_y3_syllabus_2026-27",
    "09_btech_bt_course-structure_2026-27",
    "10_btech_ce_course-structure_2026-27",
]
open("/home/z/my-project/work/pipeline_v2/batch01_stems.txt", "w").write("\n".join(scope) + "\n")
print("scope file written")
