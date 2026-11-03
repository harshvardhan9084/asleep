#!/usr/bin/env python3
"""Diagnose verify containment failures: locate the first divergent window."""
import json, re

P = "/home/z/my-project/work/pipeline_v2"


def norm_al(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


d = json.load(open(f"{P}/drafts/08_bpharm_scheme-syllabus_2026-27.draft.json"))
rec = json.load(open(f"{P}/parsed/08_bpharm_scheme-syllabus_2026-27.json"))
full = norm_al("\n".join(p["text"] for p in rec["pages"]))

CASES = [("Basics of Python Programming for Pharmaceutical Sciences", "1"),
         ("Human Anatomy, Physiology and Pathophysiology I", "4"),
         ("Pharmacognosy and Phytochemistry", "5"),
         ("Clinical Pharmacotherapeutics (Theory)", "1"),
         ("Scientific Writing (Theory)", "2"),
         ("Drug Store and Business Management (Theory)", "2"),
         ("Bio-similars, Vaccines and Macromolecule Sciences (Theory)", "1"),
         ("Industrial Safety and Waste Management (Theory)", "1")]

for name, uk in CASES:
    sub = next(s for s in d["subjects"] if s["name"] == name)
    ut = sub["units"][uk]
    na = norm_al(ut)
    # walk: find longest prefix of needle present in haystack, then show context
    lo, hi = 0, len(na)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if na[:mid] in full:
            lo = mid
        else:
            hi = mid - 1
    print(f"=== {name} unit{uk} | needle len {len(na)} | contiguous prefix match {lo}")
    print("  draft ctx : ...", na[max(0, lo - 40):lo + 80])
    i = full.find(na[:lo]) if lo else full.find(na[:40])
    if i >= 0:
        print("  full  ctx : ...", full[max(0, i + lo - 40):i + lo + 80])
    # the very next draft chars not found right there
    print("  next draft:", na[lo:lo + 120])
    print()
