#!/usr/bin/env python3
"""explore_b37.py — reconstruct the B37 in-flight batch from durable state.
Baseline: GitHub HEAD CSV (B36 push, 2208 data rows). Classify every PDF in
PDFs/5-course: done (sha16 cited in CSV) / failed-class / B33-claimed /
pending; print the select_batch-ordered pending frontier (first 15) and where
the 5 known B37 durable-draft docs sit."""
import csv, hashlib, json, os, re

CSV = "/home/z/my-project/work/repo_asleep/syllabus_catalog/syllabus_extreme_rich.csv"
SCAN = "/home/z/my-project/work/repo_asleep/PDFs/5-course"
DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"

FAILED_REGULATIONS = {
    "bpharm_ordinances_2019-20.pdf": "failed(regulations-not-syllabus)",
    "bpharm_regulations-ordinances_2026-27.pdf": "failed(regulations-not-syllabus)",
}
FAILED_CONTENT_DUP = {
    "btech_ag_y4_syllabus_2016-17_2.pdf": "failed(content-equivalent-corroborating-copy)",
    "btech_ai-ml_y3_syllabus_2024-25.pdf": "failed(content-duplicate-corroborating-copy)",
    "btech_ce_y3_syllabus_2024-25.pdf": "failed(content-equivalent-corroborating-copy)",
}
FAILED_POLICY = {
    "btech_model-curriculum_2019-20.pdf": "failed(policy-scheme-docs-not-syllabus)",
    "btech_moocs-nptel-honours_2018-19.pdf": "failed(policy-moocs-nptel-rules-not-syllabus)",
}
B33_CLAIMED = {
    "btech_plastic_syllabus_2009-10.pdf", "btech_plastic_syllabus_2018-19.pdf",
    "btech_plastic_syllabus_2020-21.pdf", "btech_plastic_y2_model-curriculum_2019-20.pdf",
    "btech_plastic_y2_scheme-syllabus_2017-18.pdf", "btech_plastic_y3_syllabus_2024-25.pdf",
    "btech_plastic_y4_syllabus-cbcs_2019-20.pdf", "btech_plastic_y4_syllabus_2016-17.pdf",
    "btech_plastic_y4_syllabus_2021-22.pdf",
}

def md5_file(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

cited = set()
n_rows = 0
with open(CSV, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        n_rows += 1
        for cell in row.values():
            if cell and "#" in cell:
                cited.update(re.findall(r"#([0-9a-f]{16})", cell))
print(f"CSV data rows: {n_rows}; cited sha16s: {len(cited)}")

entries = []
for sd in sorted(os.listdir(SCAN)):
    sdir = os.path.join(SCAN, sd)
    if not os.path.isdir(sdir):
        continue
    session = "" if sd == "no_session_found" else sd
    for fn in sorted(os.listdir(sdir)):
        if not fn.lower().endswith(".pdf"):
            continue
        entries.append({"rel": f"repo_asleep/PDFs/5-course/{sd}/{fn}",
                        "file": os.path.join(sdir, fn), "session": session, "base": fn})

for e in entries:
    e["md5"] = md5_file(e["file"])
    e["sha16"] = e["md5"][:16]
    if e["base"] in FAILED_REGULATIONS or e["base"] in FAILED_CONTENT_DUP or e["base"] in FAILED_POLICY:
        e["cls"] = "failed"
    elif e["sha16"] in cited:
        e["cls"] = "done"
    elif e["base"] in B33_CLAIMED:
        e["cls"] = "b33-claimed"
    else:
        e["cls"] = "pending"

from collections import Counter
print("CLASSES|", dict(Counter(e["cls"] for e in entries)))

# select_batch effective order: (0 if session else 1, basename) ASC, stable
pend = [e for e in entries if e["cls"] == "pending"]
pend.sort(key=lambda e: (0 if e["session"] else 1, e["base"]))
# md5 dedup vs done/failed md5s
done_md5 = {e["md5"] for e in entries if e["cls"] == "done"}
fail_md5 = {e["md5"] for e in entries if e["cls"] == "failed"}
frontier, dupes = [], []
for e in pend:
    if len(frontier) >= 15:
        break
    if e["md5"] in done_md5 or e["md5"] in fail_md5:
        dupes.append(e["rel"]); continue
    frontier.append(e)
print("\nFRONTIER (pending, select-order, first 15):")
for i, e in enumerate(frontier, 1):
    print(f"  {i:2d}. {e['rel']}  sha16={e['sha16']}")

# the 5 known B37 durable drafts
known = {}
for dp in sorted(os.listdir(DRAFTS)):
    if not dp.endswith(".draft.json"):
        continue
    d = json.load(open(os.path.join(DRAFTS, dp)))
    if dp[0] in "0123456789" and (d.get("sha16") or ""):
        known[dp] = d
print("\nKNOWN B37 DRAFTS — frontier membership:")
for dp, d in sorted(known.items()):
    hit = next((i for i, e in enumerate(frontier, 1) if e["sha16"] == d.get("sha16")), None)
    # also check done/claimed status by sha16
    st = next((e["cls"] for e in entries if e["sha16"] == d.get("sha16")), "SHA-NOT-FOUND")
    print(f"  {dp}: frontier#{hit} class-by-sha16={st} draft.session={d.get('session','')!r} course={d.get('course','')!r} pdf_rel={d.get('pdf_rel','')!r}")
