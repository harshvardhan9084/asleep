#!/usr/bin/env python3
"""probe_b28_flags2.py — targeted evidence for remaining B28 adjudications."""
import csv, json, re, glob, os
from difflib import SequenceMatcher

CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
D = "/home/z/my-project/work/pipeline_v2/drafts/B28"

rows = {}
with open(CSV, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r.get("row_kind") == "subject":
            rows[r["subject_id"]] = r

drafts = {os.path.basename(p).replace(".draft.json", ""): json.load(open(p))
          for p in glob.glob(f"{D}/*.draft.json")}


def show_row(sid):
    r = rows.get(sid)
    if not r:
        print(f"  ROW {sid}: NOT IN CSV")
        return
    print(f"  ROW {sid}: name={r.get('subject_name')!r} codes={r.get('primary_code')}/{r.get('all_codes')} "
          f"session={r.get('effective_session_latest')} branch={r.get('branch_names','')[:40]!r}")
    u1 = (r.get("unit1_text") or "")[:150].replace("\n", " ")
    print(f"    u1: {u1!r}")


def draft_units(stem, idx):
    s = drafts[stem]["subjects"][idx]
    return s


print("== A. ITC triangle: draft05::14 vs draft06::08 vs row information-theory-coding")
s5 = draft_units("05_btech_it_y2_scheme-syllabus_2017-18", 14)
s6 = draft_units("06_btech_it_y2_syllabus-rev_2014-15", 8)
print(f"  d05::14 codes={s5.get('codes')} u1={ (s5.get('units') or {}).get('1','')[:130]!r}")
print(f"  d06::08 codes={s6.get('codes')} u1={ (s6.get('units') or {}).get('1','')[:130]!r}")
u5 = [re.sub(r'[^a-z0-9]', '', v.lower()) for v in (s5.get('units') or {}).values() if v]
u6 = [re.sub(r'[^a-z0-9]', '', v.lower()) for v in (s6.get('units') or {}).values() if v]
best = 0.0
for a in u5:
    for b in u6:
        best = max(best, SequenceMatcher(None, a, b).ratio())
print(f"  draft-vs-draft best unit similarity: {best:.2f}")
show_row("information-theory-coding")

print("\n== B. 09::00 CAD: draft units vs row computer-aided-design units")
s9 = draft_units("09_btech_me-ind-pe-ipe_y4_syllabus_2016-17", 0)
print(f"  draft name={s9.get('name')!r} codes={s9.get('codes')} session={drafts['09_btech_me-ind-pe-ipe_y4_syllabus_2016-17']['session']}")
for k, v in sorted((s9.get("units") or {}).items())[:2]:
    print(f"    d-u{k}: {v[:140]!r}")
show_row("computer-aided-design")

print("\n== C. 09::03 QUALITY CONTROL draft units (FORCE_APPEND evidence)")
s93 = draft_units("09_btech_me-ind-pe-ipe_y4_syllabus_2016-17", 3)
print(f"  draft name={s93.get('name')!r} codes={s93.get('codes')}")
for k, v in sorted((s93.get("units") or {}).items())[:2]:
    print(f"    d-u{k}: {v[:140]!r}")
show_row("food-quality-control")

print("\n== D. 01::15 modelling-and-simulation vs process-modelling-and-simulation")
s115 = draft_units("01_btech_it_syllabus_2015-16", 15)
print(f"  draft name={s115.get('name')!r} codes={s115.get('codes')}")
for k, v in sorted((s115.get("units") or {}).items())[:2]:
    print(f"    d-u{k}: {v[:140]!r}")
show_row("process-modelling-and-simulation")

print("\n== E. 04::04 object-oriented-systems vs object-oriented-systems-and-c")
s44 = draft_units("04_btech_it_y2_scheme-syllabus_2009-10", 4)
print(f"  draft name={s44.get('name')!r} codes={s44.get('codes')}")
for k, v in sorted((s44.get("units") or {}).items())[:2]:
    print(f"    d-u{k}: {v[:140]!r}")
show_row("object-oriented-systems-and-c")

print("\n== F. fragment rows for CODE-REASSIGNED transfers")
for sid in ("data-structure-using-c-lab", "data-structures-using-c-lab",
            "internship-assessment-mini-project", "mini-project-or-internship-assessment",
            "micro-and-smart-systems", "mobile-application-development",
            "engg-mathematics-iii", "mathematics-iii-science-based-open-elective",
            "science-based-open-elective", "science-based-open-elective-mathematics-iii",
            "engineering-science-course-maths-v", "maths-v-engineering-science-course",
            "gp", "ngp", "general-proficiency", "general-proficiency-lab"):
    show_row(sid)

print("\n== G. draft codes for the transfer-flagged subjects")
for stem, idx in [("06_btech_it_y2_syllabus-rev_2014-15", 15),
                  ("06_btech_it_y2_syllabus-rev_2014-15", 19),
                  ("04_btech_it_y2_scheme-syllabus_2009-10", 12),
                  ("02_btech_it_syllabus_2016-17", 4)]:
    s = drafts[stem]["subjects"][idx]
    print(f"  {stem[:2]}::{idx:02d} name={s.get('name')!r} codes={s.get('codes')} flags={s.get('flags')}")
