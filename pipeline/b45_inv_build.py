#!/usr/bin/env python3
"""b45_inv_build.py — build model inventories for batch 45 (all MBA) via the
mercury engine's inventory() call, cached to work/pipeline_v2/inv/<stem>.inv.json.
Runs docs SEQUENTIALLY (1 API call at a time); inventory cache means a re-run
never re-pays a call (bounded-round/resume class)."""
import json, os, sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
INV = "/home/z/my-project/work/pipeline_v2/inv"
STEMS = [
    "01_mba_tourism-mgmt_syllabus_2016-17",
    "02_mba_tourism-mgmt_syllabus_2017-18",
    "03_mba_tourism-mgmt_y2_model-curriculum_2019-20",
    "04_mba_tourism_syllabus_2014-15",
    "05_mba_travel-tourism_y1_syllabus_2020-21",
    "06_mba_travel-tourism_y2_syllabus_2021-22",
    "07_mba_y1_model-curriculum_2018-19",
    "08_mba_y1_scheme_2008-09",
    "09_mba_y1_scheme_2016-17",
    "10_mba_y2_model-curriculum-rev-aicte_2019-20",
]

for stem in STEMS:
    out = f"{INV}/{stem}.inv.json"
    if os.path.exists(out):
        try:
            n = len(json.load(open(out)))
            print(f"SKIP|{stem}|cached {n}")
            continue
        except Exception:
            pass
    meta = json.load(open(f"{PARSED}/{stem}.json"))
    pdf_name = (meta.get("meta") or meta).get("file", stem + ".pdf")
    fulltext = open(f"{PARSED}/{stem}.fulltext.txt").read()
    session, course = "", "MBA"
    q = json.load(open("/home/z/my-project/work/pipeline_v2/queue.json"))
    for e in q["entries"]:
        if e["rel"].endswith("/" + pdf_name):
            session, course = e.get("session", ""), e.get("course", "MBA")
            break
    try:
        inv, subs = me.inventory(pdf_name, fulltext, session, course)
        os.makedirs(INV, exist_ok=True)
        json.dump(subs, open(out, "w"), indent=1, ensure_ascii=False)
        nd = sum(1 for s in subs if s.get("class") == "detail")
        print(f"INV|{stem}|{len(subs)} entries (detail {nd}, scheme_only {len(subs)-nd})")
    except Exception as e:
        print(f"JUNK|{stem}|{repr(e)[:120]}")
