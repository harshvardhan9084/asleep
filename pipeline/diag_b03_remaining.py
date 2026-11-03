#!/usr/bin/env python3
"""Diagnose REMAINING verify containment failures after the B3 furniture
remedy — show the divergence with both sides furniture-stripped."""
import json, re, sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
from verify_draft import norm_al, strip_unit_table_furniture, strip_furniture_deep

P = "/home/z/my-project/work/pipeline_v2"

d = json.load(open(f"{P}/drafts/08_bpharm_scheme-syllabus_2026-27.draft.json"))
rec = json.load(open(f"{P}/parsed/08_bpharm_scheme-syllabus_2026-27.json"))
pages = rec["pages"]

CASES = [("Clinical Pharmacotherapeutics (Theory)", "1"),
         ("Scientific Writing (Theory)", "2"),
         ("Drug Store and Business Management (Theory)", "2"),
         ("Bio-similars, Vaccines and Macromolecule Sciences (Theory)", "1"),
         ("Industrial Safety and Waste Management (Theory)", "1")]

full2 = norm_al(strip_unit_table_furniture(strip_furniture_deep("\n".join(p["text"] for p in pages))))

for name, uk in CASES:
    sub = next(s for s in d["subjects"] if s["name"] == name)
    ut = sub["units"][uk]
    na = norm_al(strip_unit_table_furniture(ut))
    lo, hi = 0, len(na)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if na[:mid] in full2:
            lo = mid
        else:
            hi = mid - 1
    print(f"=== {name} unit{uk} | stripped needle len {len(na)} | prefix match {lo}")
    print("  draft ctx : ...", na[max(0, lo - 50):lo + 100])
    i = full2.find(na[:max(lo, 40)])
    if i >= 0:
        print("  full  ctx : ...", full2[max(0, i + lo - 50):i + lo + 100])
    print("  next draft:", na[lo:lo + 140])
    print()
