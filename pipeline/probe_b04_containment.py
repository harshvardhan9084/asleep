#!/usr/bin/env python3
"""probe_b04_containment.py — root-cause the unit-containment failures of
draft 04: for each failing (subject, unit), show the longest missing span so
the failure class is visible (text-layer drop / image-embedded / furniture)."""
import json, re

P = "/home/z/my-project/work/pipeline_v2/parsed/04_bpharm_scheme-syllabus_2026-27.json"
D = "/home/z/my-project/work/pipeline_v2/drafts/04_bpharm_scheme-syllabus_2026-27.draft.json"

CASES = [
    ("Human Anatomy, Physiology and Pathophysiology I (Theory)", "4"),
    ("Pharmacognosy and Phytochemistry (Theory)", "5"),
    ("Pharmaceutical Analysis (Theory)", "1"),
    ("AI in Clinical applications (Theory)", "4"),
    ("Scientific Writing (Theory)", "2"),
    ("Drug Store and Business Management (Theory)", "2"),
    ("Bio-similars, Vaccines and Macromolecule Sciences (Theory)", "1"),
    ("Industrial Safety and Waste Management (Theory)", "1"),
]


def norm_al(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


rec = json.load(open(P))
pages = [p["text"] for p in rec["pages"]]
hay = norm_al(re.sub(r"(?m)^\s*\d{1,4}\s*$", "", "\n".join(pages)))
d = json.load(open(D))
byname = {}
for s in d["subjects"]:
    byname.setdefault(s.get("name", ""), s)

for name, uk in CASES:
    s = byname.get(name)
    if not s:
        print(f"MISS|{name}")
        continue
    a = norm_al((s.get("units") or {}).get(uk, ""))
    # longest missing spans: slide 60-char probes over the needle
    miss_spans = []
    i = 0
    while i < len(a):
        probe = a[i:i + 60]
        if probe and probe not in hay:
            j = i + 60
            # extend
            while j < len(a) and a[i:j + 10] not in hay:
                j += 10
            miss_spans.append((i, min(j, len(a))))
            i = j
        else:
            i += 20
    print(f"CASE|{name[:44]}|unit{uk}|len={len(a)}|miss_spans={[(x, y) for x, y in miss_spans[:6]]}")
    for x, y in miss_spans[:2]:
        print(f"   MISS[{x}:{y}] {a[x:y][:110]}")
