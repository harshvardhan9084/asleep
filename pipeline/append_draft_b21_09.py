#!/usr/bin/env python3
"""Incremental draft appender (RULES §7/§8): loads DRAFT_OUT, appends each JSONL
subject, and rewrites the file after EVERY subject so a crash loses nothing."""
import json, sys, os

DRAFT = '/home/z/my-project/work/pipeline_v2/drafts/09_btech_ece_y3_syllabus_2018-19.draft.json'

def load():
    if os.path.exists(DRAFT):
        with open(DRAFT) as f:
            return json.load(f)
    return {
        "pdf_rel": "repo_asleep/PDFs/5-course/2018-19/btech_ece_y3_syllabus_2018-19.pdf",
        "session": "2018-19",
        "course": "BTech",
        "sha16": "c631ec6e28ce78f9",
        "stem": "09_btech_ece_y3_syllabus_2018-19",
        "subjects": [],
        "non_subject_rows": [],
        "quirks": [],
        "flags": []
    }

for path in sys.argv[1:]:
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            d = load()
            d["subjects"].append(obj)
            with open(DRAFT, 'w') as out:
                json.dump(d, out, indent=1, ensure_ascii=False)
            print(f"{os.path.basename(path)} line {i}: appended '{obj.get('name')}' -> subjects={len(d['subjects'])}")
