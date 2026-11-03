#!/usr/bin/env python3
"""Bootstrap queue.json from the asleep repo syllabus pool + 2 owner-approved local PDFs.

Scope: PDFs/5-course/<session>/<file>  (448 files) + 2 local pinned PDFs.
Ordering for 'next-batch' selection is by session descending (2025-26 first per
the newest-wins batch strategy), then filename. Owner-approved pinned PDFs get
status 'pending-pinned'.

Statuses: pending-pinned | pending | done | failed | skipped
"""
import hashlib, json, os, re, sys

REPO   = "/home/z/my-project/work/repo_asleep/PDFs"
LOCAL2 = "/home/z/my-project/work/artd_v3/sources"
QUEUE  = "/home/z/my-project/work/pipeline_v2/queue.json"

CODE_RE = re.compile(r"^[a-z]{2,6}(_[a-z0-9\-]+)*_[a-z0-9\-]+.*\.pdf$", re.I)
NON_SYLLABUS_HINTS = ("regulations-ordinances", "course-structure", "datesheet", "result", "notice")

def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]

def main():
    entries = []
    # 1) repo PDFs (5-course only — the catalog scope is BTech/BPharm/BCA/MCA/MBA;
    #    other_courses/ holds out-of-scope programme docs, quarantined from queueing)
    root = os.path.join(REPO, "5-course")
    for dp, _dn, fn in os.walk(root):
        for f in sorted(fn):
            if not f.lower().endswith(".pdf"):
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, REPO)
            parts = rel.split(os.sep)
            session = parts[0] if len(parts) == 2 else "no_session_found"
            entries.append({
                "rel": f"5-course/{session}/{f}",
                "repo_path": p,
                "session": session,
                "status": "pending",
                "sha16": sha16(p),
                "bytes": os.path.getsize(p),
                "pinned": False,
                "note": "",
            })
    # 2) owner-approved local PDFs (pinned: "run on these 2 too this run")
    for f in sorted(os.listdir(LOCAL2)):
        if f.lower().endswith(".pdf"):
            p = os.path.join(LOCAL2, f)
            entries.append({
                "rel": f"local/{f}",
                "repo_path": p,
                "session": "2023-24",
                "status": "pending-pinned",
                "sha16": sha16(p),
                "bytes": os.path.getsize(p),
                "pinned": True,
                "note": "owner-approved 2026-10 run ('run on these 2 too this run')",
            })

    entries.sort(key=lambda e: (e["pinned"] is not True, e["session"] == "no_session_found",
                                e["session"], e["rel"]), reverse=False)
    # custom order: pinned first, then sessions desc (newest first), no_session last
    def key(e):
        sess = e["session"]
        sess_rank = 0 if e["pinned"] else (1 if sess != "no_session_found" else 2)
        try:
            y = int(sess[:4]); y = -y
        except ValueError:
            y = 9999
        return (sess_rank, y, e["rel"])
    entries.sort(key=key)

    with open(QUEUE, "w", encoding="utf-8") as f:
        json.dump({"built_by": "make_queue.py", "built_on": "2026-10-27",
                   "scope": "5-course (BTech/BPharm/BCA/MCA/MBA) + 2 owner-approved local",
                   "count": len(entries), "entries": entries}, f, indent=1)
    print(f"queue built: {len(entries)} entries -> {QUEUE}")
    from collections import Counter
    print(Counter(e["status"] for e in entries))

if __name__ == "__main__":
    main()
