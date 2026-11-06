#!/usr/bin/env python3
"""b45_repair2.py — second-pass REX for the 3 stubborn empty rows with
tighter slices + verification; hand-transcribe only if the model fails again."""
import json, re, sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
INV = "/home/z/my-project/work/pipeline_v2/inv"
DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"


def norm(c):
    return re.sub(r"[^A-Z0-9]", "", (c or "").upper())


def pg(ft, pn):
    m = re.search(r"===== PAGE %d =====\n(.*?)(?=\n===== PAGE|\Z)" % pn, ft, re.S)
    return m.group(1) if m else ""


JOBS = [
    ("03_mba_tourism-mgmt_y2_model-curriculum_2019-20", "KMT402", 17, 19),
    ("10_mba_y2_model-curriculum-rev-aicte_2019-20", "KMBIB04", 53, 55),
    ("10_mba_y2_model-curriculum-rev-aicte_2019-20", "KMBOM05", 72, 75),
]

for stem, code, p0, p1 in JOBS:
    meta = json.load(open(f"{PARSED}/{stem}.json"))
    meta = meta.get("meta", meta)
    pdf_name = meta.get("file", stem.split("_", 1)[1] + ".pdf")
    ft = open(f"{PARSED}/{stem}.fulltext.txt").read()
    inv = json.load(open(f"{INV}/{stem}.inv.json"))
    sub = next(s for s in inv if norm(s.get("code_print")) == code)
    slice_txt = "\n\n".join(pg(ft, p) for p in range(p0, p1))
    print(f"--- {code}: slice p{p0}-{p1-1} ({len(slice_txt)} chars) ---")
    try:
        _, obj = me.extract_one(pdf_name, slice_txt, meta, sub, "2019-20", "MBA")
        name = (obj.get("name") or obj.get("name_print") or "").strip()
        nu = len(obj.get("units") or {})
        print(f"REX2|{code}|name={name[:50]!r}|units={nu}")
        if name and nu:
            draft = json.load(open(f"{DRAFTS}/{stem}.draft.json"))
            idx = next(i for i, s in enumerate(draft["subjects"]) if code in [norm(c) for c in (s.get("codes") or [])])
            draft["subjects"][idx] = obj
            json.dump(draft, open(f"{DRAFTS}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)
            print(f"REX2-SAVED|{stem}|{code}")
    except Exception as e:
        print(f"REX2-FAIL|{code}|{repr(e)[:120]}")
