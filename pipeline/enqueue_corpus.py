#!/usr/bin/env python3
"""enqueue_corpus.py — idempotently enqueue the repo corpus (asleep PDFs) into
the pipeline queue as `pending`, so every hourly cron run has work.

Scan root: work/repo_asleep/PDFs/5-course/<session>/<file>.pdf
  - course inferred from the filename (bca->BCA, bpharm->BPharm, mca->MCA,
    mba->MBA, else BTech); the draft-time course_from_codes() guard (RULES §1b)
    overrides it from printed codes at merge time.
  - session from the parent directory name (no_session_found -> "").
  - md5 computed lazily at selection time (select_batch), not here.
Idempotent: rels already in the queue are untouched.
"""
import json, os, re, sys
from datetime import datetime, timezone

QUEUE = "/home/z/my-project/work/pipeline_v2/queue.json"
ROOT = "/home/z/my-project/work"
SCAN = os.path.join(ROOT, "repo_asleep/PDFs/5-course")


def course_from_filename(name):
    n = name.lower()
    if re.search(r"(^|[\W_])bca([\W_]|$)", n) or n.startswith("bca"):
        return "BCA"
    if "bpharm" in n or "b-pharm" in n or "b.pharm" in n:
        return "BPharm"
    if re.search(r"(^|[\W_])mca([\W_]|$)", n) or n.startswith("mca"):
        return "MCA"
    if re.search(r"(^|[\W_])mba([\W_]|$)", n) or n.startswith("mba"):
        return "MBA"
    return "BTech"


def main():
    q = json.load(open(QUEUE))
    have = {e["rel"] for e in q["entries"]}
    added = {}
    for session_dir in sorted(os.listdir(SCAN)):
        sdir = os.path.join(SCAN, session_dir)
        if not os.path.isdir(sdir):
            continue
        session = "" if session_dir == "no_session_found" else session_dir
        for fn in sorted(os.listdir(sdir)):
            if not fn.lower().endswith(".pdf"):
                continue
            rel = f"repo_asleep/PDFs/5-course/{session_dir}/{fn}"
            if rel in have:
                continue
            course = course_from_filename(fn)
            q["entries"].append({
                "rel": rel, "file": os.path.join(sdir, fn), "session": session,
                "course": course, "status": "pending", "md5": "", "sha16": "",
                "attempts": 0, "batch": 0,
                "notes": "corpus enqueue (asleep repo, 5-course tree)"})
            added[course] = added.get(course, 0) + 1
    if added:
        q["meta"].setdefault("history", []).append({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event": f"corpus enqueue: {sum(added.values())} new PDF(s) {added}"})
        with open(QUEUE, "w") as f:
            json.dump(q, f, indent=1, ensure_ascii=False)
    print(f"ENQUEUED|{sum(added.values())}|{added}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
