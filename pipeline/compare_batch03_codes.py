#!/usr/bin/env python3
"""compare_batch03_codes.py — evidence table for the CODE-SLOT-ERA-REUSE
adjudication: lists every code token printed for one subject in the 2026-27
BPharm scheme+syllabus doc AND for a DIFFERENT-named subject in the 2019-20
BPharm doc (AKTU re-issued the BP101T-BP816P namespace in the revision)."""
import json, re

BASE = "/home/z/my-project/work/pipeline_v2"


def norm(c):
    return re.sub(r"[^A-Z0-9]", "", c.upper())


def cmap(stem):
    d = json.load(open(f"{BASE}/drafts/{stem}.draft.json"))
    m = {}
    for s in d["subjects"]:
        for c in s.get("codes", []):
            m.setdefault(norm(c), set()).add(s["name"])
    return m


m08 = cmap("08_bpharm_scheme-syllabus_2026-27")
m10 = cmap("10_bpharm_y1-4_syllabus_2019-20")
coll = sorted(set(m08) & set(m10))
diff = [c for c in coll if not (m08[c] & m10[c])]
print(f"shared tokens: {len(coll)}; different-subject (era-reuse): {len(diff)}")
for c in diff:
    print(f"{c}: 2026-27={sorted(m08[c])[0][:48]!r} | 2019-20={sorted(m10[c])[0][:48]!r}")
