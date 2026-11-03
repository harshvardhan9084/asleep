#!/usr/bin/env python3
"""debug_b03_g2g3.py — reproduce the live-commit G2/G3 failures locally."""
import csv, json, sys, os
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
from merge_draft import (CSV_PATH, ladder, norm_name, norm_code, row_owned_codes,
                         course_from_codes, canon_course)

rows = list(csv.DictReader(open(CSV_PATH)))
d = json.load(open("/home/z/my-project/work/pipeline_v2/drafts/02_bca_y1_syllabus_2025-26.draft.json"))

# emulate: information-systems (subject idx 01)
s = d["subjects"][1]
print("subject:", s["name"], s["codes"])
course_eff = "BCA"
tier, targets, info = ladder(s, rows, course_eff)
print("ladder:", tier, info, [t["subject_id"] for t in targets])

mf = next(r for r in rows if r["subject_id"] == "mathematical-foundation")
print("math-foundation all_codes:", repr(mf["all_codes"]), "primary:", repr(mf["primary_code"]))
inf = next(r for r in rows if r["subject_id"] == "information-systems")
print("information-systems all_codes:", repr(inf["all_codes"]), "primary:", repr(inf["primary_code"]))

# check what names+ids appended BCA rows would produce
slugs = {}
for r in rows:
    if r["row_kind"] == "subject":
        slugs.setdefault(r["subject_id"], []).append(r["course_name"])
print("\nexisting dup slugs:", {k: v for k, v in slugs.items() if len(v) > 1})
for nm in ("data-structure", "data-structure-lab", "digital-electronics", "web-technology",
           "web-technology-lab", "operating-systems", "technical-communication",
           "universal-human-values-and-professional-ethics", "sports-and-yoga"):
    print(f"  slug {nm!r}: exists={nm in slugs}")
