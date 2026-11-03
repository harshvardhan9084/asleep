#!/usr/bin/env python3
"""B27 doc 08 incremental draft appender (RULES §7/§8).
Loads DRAFT_OUT (creates header on first write), appends each JSON file's
content, and REWRITES the draft after EVERY item so a crash loses nothing.
Item routing: dict with "__section__" in {non_subject_rows, quirks, flags}
goes to that doc-level list (extend); everything else appends to subjects.
"""
import json, os, sys

DRAFT = '/home/z/my-project/work/pipeline_v2/drafts/B27/08_btech_handloom-textile_y4_syllabus_2025-26.draft.json'

HEADER = {
    "pdf_rel": "repo_asleep/PDFs/5-course/2025-26/btech_handloom-textile_y4_syllabus_2025-26.pdf",
    "session": "2025-26",
    "course": "BTech",
    "sha16": "b35463e306e82a00",
    "stem": "08_btech_handloom-textile_y4_syllabus_2025-26",
    "subjects": [],
    "non_subject_rows": [],
    "quirks": [],
    "flags": [],
}


def load():
    if os.path.exists(DRAFT):
        with open(DRAFT) as f:
            return json.load(f)
    return json.loads(json.dumps(HEADER))


def dump(d):
    tmp = DRAFT + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(tmp, DRAFT)


def main():
    d = load()
    for path in sys.argv[1:]:
        with open(path) as f:
            items = json.load(f)
        if isinstance(items, dict):
            items = [items]
        for item in items:
            sec = item.pop("__section__", None) if isinstance(item, dict) else None
            if sec in ("non_subject_rows", "quirks", "flags"):
                if isinstance(item, dict) and set(item.keys()) <= {"rows", "items"}:
                    item = item.get("rows") or item.get("items")
                if isinstance(item, list):
                    d[sec].extend(item)
                else:
                    d[sec].append(item)
            else:
                d["subjects"].append(item)
            dump(d)  # durable after EVERY item
            print(f"appended -> {sec or 'subjects'} (subjects={len(d['subjects'])}, nsr={len(d['non_subject_rows'])})")


if __name__ == '__main__':
    main()
