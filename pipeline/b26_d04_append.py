#!/usr/bin/env python3
"""B26-D04 incremental draft appender (RULES §7/§8).
Usage: b26_d04_append.py <mode> <payload.json>
mode: subject | non_subject | quirk | flag | verify
Appends items one at a time, saving DRAFT_OUT after every append.
"""
import json, sys, os

DRAFT = '/home/z/my-project/work/repo_asleep/pipeline/drafts_B26/04_btech_ft_s7-8_syllabus_2025-26.draft.json'
HEADERS = {
    "pdf_rel": "repo_asleep/PDFs/5-course/2025-26/btech_ft_s7-8_syllabus_2025-26.pdf",
    "session": "2025-26",
    "course": "BTech",
    "sha16": "7537580daa99b640",
    "stem": "04_btech_ft_s7-8_syllabus_2025-26",
}

def load():
    if os.path.exists(DRAFT):
        with open(DRAFT, encoding='utf-8') as f:
            return json.load(f)
    d = dict(HEADERS)
    d.update({"subjects": [], "non_subject_rows": [], "quirks": [], "flags": []})
    return d

def save(d):
    os.makedirs(os.path.dirname(DRAFT), exist_ok=True)
    tmp = DRAFT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, DRAFT)

def main():
    mode = sys.argv[1]
    if mode == 'verify':
        d = load()
        print(f"header={ {k:v for k,v in d.items() if k not in ('subjects','non_subject_rows','quirks','flags')} }")
        print(f"subjects={len(d['subjects'])} non_subject_rows={len(d['non_subject_rows'])} quirks={len(d['quirks'])} flags={len(d['flags'])}")
        for s in d['subjects']:
            print(f"  {s.get('codes')} {s.get('name')} sem={s.get('semester')} units={len(s.get('units',{}))} cos={len(s.get('cos',[]))} flags={s.get('flags')}")
        return
    path = sys.argv[2]
    key = {"subject": "subjects", "non_subject": "non_subject_rows",
           "quirk": "quirks", "flag": "flags"}[mode]
    with open(path, encoding='utf-8') as f:
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
