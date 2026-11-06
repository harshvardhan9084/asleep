#!/usr/bin/env python3
"""b39_resume_d07.py — mercury-3 extraction for doc 07's TWO CODE-LESS
non-credit subjects (COMPUTER SYSTEM SECURITY p.2, PYTHON PROGRAMMING p.3;
no codes are printed anywhere in the doc — the recorded code-less class).
b37_resume.py's missing-detail filter drops empty-code entries, so this
runner calls me.extract_one directly. Incremental draft writes (RULES §7)."""
import json, os, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

stem = "07_btech_y2_non-credit-courses_2018-19"
parsed_dir = "/home/z/my-project/work/pipeline_v2/parsed"
drafts_dir = sys.argv[1] if len(sys.argv) > 1 else "/home/z/my-project/work/pipeline_v2/drafts"
rec = json.load(open(f"{parsed_dir}/{stem}.json"))
pdf_name = rec.get("file", stem + ".pdf")
fulltext = open(f"{parsed_dir}/{stem}.fulltext.txt").read()
q = json.load(open("/home/z/my-project/work/pipeline_v2/queue.json"))
session = course = pdf_rel = ""
for e in q["entries"]:
    if e["rel"].endswith("/" + os.path.basename(pdf_name)):
        pdf_rel, session, course = e["rel"], e.get("session", ""), e.get("course", "BTech")
        break
else:
    pdf_rel, session, course = "", rec.get("session", ""), "BTech"

P = f"{drafts_dir}/{stem}.draft.json"
if os.path.exists(P):
    draft = json.load(open(P))
else:
    draft = {"pdf_rel": pdf_rel, "session": session, "course": course,
             "sha16": rec.get("sha16", ""), "stem": stem, "subjects": [],
             "non_subject_rows": [], "quirks": [], "flags": []}

have = {re.sub(r"[^A-Z0-9]", "", (c or "").upper()) for s in draft["subjects"] for c in (s.get("codes") or [""])}

def save():
    json.dump(draft, open(P, "w"), indent=1, ensure_ascii=False)

save()
for sub in [{"class": "detail", "code_print": "", "name_print": "COMPUTER SYSTEM SECURITY", "page": 2},
            {"class": "detail", "code_print": "", "name_print": "PYTHON PROGRAMMING", "page": 3}]:
    if "" in have and len(draft["subjects"]) >= 2:
        break
    code, obj = me.extract_one(pdf_name, fulltext, rec, sub, session, course)
    obj.setdefault("name", obj.get("name_print", ""))
    obj.setdefault("codes", [])
    obj.setdefault("quirks", [])
    obj.setdefault("flags", [])
    if obj.get("units") is None:
        obj["units"] = {}
    draft["subjects"].append(obj)
    save()
    print("SUBJ|", obj.get("name", "")[:45], "| units:", len(obj.get("units") or {}))
print("DRAFT|", stem, "|", len(draft["subjects"]), "subjects ->", P)
