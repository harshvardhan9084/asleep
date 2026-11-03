#!/usr/bin/env python3
"""B25-D04 incremental draft appender (RULES §7/§8).
Usage: b25_d04_append.py <mode> <payload.json>
mode: subject | non_subject | quirk | flag
Appends items one at a time, saving DRAFT_OUT after every append.
"""
import json, sys, os

DRAFT = '/home/z/my-project/work/pipeline_v2/drafts/B25/04_btech_env_syllabus_2014-15.draft.json'
HEADERS = {
    "pdf_rel": "repo_asleep/PDFs/5-course/2014-15/btech_env_syllabus_2014-15.pdf",
    "session": "2014-15",
    "course": "BTech",
    "sha16": "bf7c400a47cff23f",
    "stem": "04_btech_env_syllabus_2014-15",
}

def load():
    if os.path.exists(DRAFT):
        with open(DRAFT) as f:
            return json.load(f)
    d = dict(HEADERS)
    d.update({"subjects": [], "non_subject_rows": [], "quirks": [], "flags": []})
    return d

def save(d):
    tmp = DRAFT + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, DRAFT)

def main():
    mode, path = sys.argv[1], sys.argv[2]
    key = {"subject": "subjects", "non_subject": "non_subject_rows",
           "quirk": "quirks", "flag": "flags"}[mode]
    with open(path) as f:
        items = json.load(f)
    if isinstance(items, dict):
        items = [items]
    d = load()
    for it in items:
        d.setdefault(key, []).append(it)
        save(d)
    print(f"appended {len(items)} -> {key}; total {len(d[key])}; subjects={len(d['subjects'])}")

if __name__ == '__main__':
    main()
