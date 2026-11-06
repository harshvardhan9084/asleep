#!/usr/bin/env python3
"""b39_fix_inv_d03.py — correct 03_btech_y2_common-subjects-syllabus-rev_2014-15.inv.json.

Fixes (all print-anchored):
 - NAS301/NAS401 name anchored to the p.2 printed header 'MATHEMATICS –III'
   (the pairing had picked the L-T-P line);
 - NOE electives re-anchored to their REAL detail pages (last line-start
   occurrence scan; p.3 is the elective list page);
 - AUC-001 added: pp.14-22 are SCANNED IMAGE pages (text layer empty, 5 chars
   each) printing 'A Foundation Course in Human Values & Professional Ethics,
   Course Code: AUC-001' — transcribed from page images by a subagent (RULES
   §6: visible print authoritative) and spliced into the draft afterwards.
"""
import json

STEM = "03_btech_y2_common-subjects-syllabus-rev_2014-15"
P = f"/home/z/my-project/work/pipeline_v2/inv/{STEM}.inv.json"
inv = json.load(open(P))

DETAIL_PG = {
    "NOE031": (4, "INTRODUCTION TO SOFT COMPUTING"),
    "NOE032": (5, "NANO   SCIENCES"),
    "NOE033": (6, "LASER SYSTEMS AND APPLICATIONS"),
    "NOE034": (7, "SPACE SCIENCES"),
    "NOE035": (7, "POLYMER SCIENCE AND TECHNOLOGY"),
    "NOE036": (8, "NUCLEAR    SCIENCE"),
    "NOE037": (9, "MATERIAL SCIENCE"),
    "NOE038": (10, "DISCRETE   MATHEMATICS"),
    "NOE039": (11, "APPLIED LINEAR ALGEBRA"),
}
out = []
for e in inv:
    key = e["code_print"].replace("/", "").replace("-", "")
    base = key[:7]
    if base in DETAIL_PG:
        pg, nm = DETAIL_PG[base]
        out.append({"class": "detail", "code_print": e["code_print"], "name_print": nm, "page": pg})
    elif base == "NAS301":
        out.append({"class": "detail", "code_print": e["code_print"], "name_print": "MATHEMATICS –III", "page": 2})
    else:
        out.append(e)

# AUC-001 image-page subject (transcription spliced post-extraction)
out.append({"class": "detail", "code_print": "AUC-001",
            "name_print": "HUMAN VALUES & PROFESSIONAL ETHICS (image pages pp.14-22)",
            "page": 14})
json.dump(out, open(P, "w"), indent=1, ensure_ascii=False)
det = sum(1 for x in out if x["class"] == "detail")
print(f"doc03 inv fixed: {len(out)} entries (detail {det}, scheme {len(out)-det})")
