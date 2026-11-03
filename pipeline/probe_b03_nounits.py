#!/usr/bin/env python3
"""Zero-guess probe: for each no-units draft subject, inspect the printed
context around its code in the parsed fulltext — is any unit/detailed
syllabus actually printed? Also check BP111P practice list presence."""
import json, re

P = "/home/z/my-project/work/pipeline_v2"

CASES = [
    ("04_bca_y2_syllabus_2025-26", "BVA451"),
    ("09_bpharm_y1-2_syllabus_2013-14", "BOP-245P"),
    ("10_bpharm_y1-4_syllabus_2019-20", "BP111P"),
    ("10_bpharm_y1-4_syllabus_2019-20", "BP509P"),
    ("10_bpharm_y1-4_syllabus_2019-20", "BP706PS"),
    ("10_bpharm_y1-4_syllabus_2019-20", "BP707P"),
    ("10_bpharm_y1-4_syllabus_2019-20", "BP815PW"),
    ("10_bpharm_y1-4_syllabus_2019-20", "BP510P"),   # REPORT ON INDUSTRIAL TRAINING? find by name below
]

parsed = {}
drafts = {}
for stem in ("04_bca_y2_syllabus_2025-26", "09_bpharm_y1-2_syllabus_2013-14",
             "10_bpharm_y1-4_syllabus_2019-20"):
    parsed[stem] = json.load(open(f"{P}/parsed/{stem}.json"))
    drafts[stem] = json.load(open(f"{P}/drafts/{stem}.draft.json"))

# map codes->names from drafts (10 has the report subjects; find their codes)
for stem in ("10_bpharm_y1-4_syllabus_2019-20",):
    for s in drafts[stem]["subjects"]:
        if s["name"].startswith(("REPORT ON", "HOSPITAL TRAINING", "PRACTICE SCHOOL", "PROJECT WORK")):
            print("DRAFT-ROW:", s["name"], s["codes"], "sem", s.get("semester"))

for stem, code in CASES:
    rec = parsed[stem]
    full = "\n".join(p["text"] for p in rec["pages"])
    c = code.replace("-", "")
    idx = full.find(code)
    if idx < 0:
        m = re.search(re.escape(code[:3]) + r"\s?-?" + re.escape(code[3:]), full)
        idx = m.start() if m else -1
    print(f"\n===== {stem[:22]} {code} (idx {idx}) =====")
    if idx >= 0:
        print(full[idx:idx + 700].replace("\n", " | ")[:700])
