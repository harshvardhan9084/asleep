#!/usr/bin/env python3
"""patch_draft_counts.py — persist printed lecture-count evidence into draft 02.

Zero-GAP fix: the printed per-row lecture-count column was seen but not
recorded for BOE312 (bracketed per-unit) and BOE313 (per-sub-item + total).
Evidence recorded as subject-level quirks; unit prose untouched (counts are
table-column values, not sentence content).
"""
import json

P = "/home/z/my-project/work/pipeline_v2/drafts/02_Open-Elective-BTech-2nd-year-2023-08092023.draft.json"
d = json.load(open(P))
q312 = ("Printed per-unit lecture counts bracketed at unit ends (p.16): "
        "Unit-I [8], Unit-II [9], Unit-III [6], Unit-IV [9], Unit-V [10]; total 42")
q313 = ("Printed per-sub-item lecture-count column (p.17), row order: 5,4,5,4,6,6,4,4,4,3 "
        "(sum 45 = printed total 45); column digits excluded from unit prose transcription")
for s in d["subjects"]:
    c0 = s["codes"][0]
    if c0 == "BOE312":
        if q312 not in s["quirks"]:
            s["quirks"].append(q312)
    if c0 == "BOE313":
        if q313 not in s["quirks"]:
            s["quirks"].append(q313)
with open(P, "w") as f:
    json.dump(d, f, ensure_ascii=False, indent=1)
print("patched:", [s["codes"][0] for s in d["subjects"] if s["codes"][0] in ("BOE312", "BOE313")])
