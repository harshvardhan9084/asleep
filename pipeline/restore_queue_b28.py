#!/usr/bin/env python3
"""restore_queue_b28.py — rebuild queue state after a workspace reset (35th).

GitHub (=B27, CSV 1983 data rows) is the authoritative baseline.
Repo PDF tree (owner uniform-name layout):
  PDFs/5-course/<session>/<uniform-name>.pdf  (in-scope PDFs)
  PDFs/other_courses/...                      (out-of-scope — NOT enqueued)
This script CREATES a fresh queue by scanning the 5-course tree and
restores status by CONTENT:
  - md5/sha16 computed per file (rename-stable);
  - every `#<sha16>` token in ANY column of the GitHub CSV marks that PDF done
    (never re-process ingested docs — RULES §9);
  - the 5 recorded failed classes (B19/B23 manifests) marked by basename;
  - the legacy 8 done uploads live outside the 5-course tree — out of queue;
  - batch_counter := 27 so the next select_batch yields B28
    (B27 manifest: 244 done / 199 pending / 5 failed @ end of B27).
"""
import csv, hashlib, json, os, re, sys
from datetime import datetime, timezone
from collections import Counter

QUEUE = "/home/z/my-project/work/pipeline_v2/queue.json"
REPO_CSV = "/home/z/my-project/work/repo_asleep/syllabus_catalog/syllabus_extreme_rich.csv"
CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
ROOT = "/home/z/my-project/work"
SCAN = os.path.join(ROOT, "repo_asleep/PDFs/5-course")

FAILED_REGULATIONS = {
    "bpharm_ordinances_2019-20.pdf": "failed(regulations-not-syllabus)",
    "bpharm_regulations-ordinances_2026-27.pdf": "failed(regulations-not-syllabus)",
}
FAILED_CONTENT_DUP = {
    "btech_ag_y4_syllabus_2016-17_2.pdf": "failed(content-equivalent-corroborating-copy)",
    "btech_ai-ml_y3_syllabus_2024-25.pdf": "failed(content-duplicate-corroborating-copy)",
    "btech_ce_y3_syllabus_2024-25.pdf": "failed(content-equivalent-corroborating-copy)",
}


def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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
    if md5_file(CSV) != md5_file(REPO_CSV):
        print("ABORT: local baseline CSV md5 != repo CSV md5")
        return 2
    cited = set()
    with open(REPO_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for cell in row.values():
                if cell and "#" in cell:
                    for m in re.findall(r"#([0-9a-f]{16})", cell):
                        cited.add(m)
    print(f"cited sha16s: {len(cited)}")

    entries = []
    for session_dir in sorted(os.listdir(SCAN)):
        sdir = os.path.join(SCAN, session_dir)
        if not os.path.isdir(sdir):
            continue
        session = "" if session_dir == "no_session_found" else session_dir
        for fn in sorted(os.listdir(sdir)):
            if not fn.lower().endswith(".pdf"):
                continue
            rel = f"repo_asleep/PDFs/5-course/{session_dir}/{fn}"
            entries.append({
                "rel": rel, "file": os.path.join(sdir, fn), "session": session,
                "course": course_from_filename(fn), "status": "pending",
                "md5": "", "sha16": "", "attempts": 0, "batch": 0,
                "notes": "corpus enqueue (asleep repo, 5-course tree, uniform-name layout)"})

    done = failed = 0
    for e in entries:
        base = os.path.basename(e["rel"])
        cls = FAILED_REGULATIONS.get(base) or FAILED_CONTENT_DUP.get(base)
        if cls:
            e["status"] = cls
            e["notes"] += " | reset-restore: recorded failed class (B19/B23 manifests; RULES §9)"
            e["md5"] = md5_file(e["file"]); e["sha16"] = e["md5"][:16]
            failed += 1
            continue
        e["md5"] = md5_file(e["file"])
        e["sha16"] = e["md5"][:16]
        if e["sha16"] in cited:
            e["status"] = "done"
            e["notes"] += " | done: sha16 cited in GitHub B27 CSV (reset-restore)"
            done += 1

    q = {"meta": {
            "batch_counter": 27,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": ("reset rebuild: fresh scan of PDFs/5-course (owner uniform-name "
                     "layout); status restored by md5 content — GitHub B27 CSV citations + "
                     "recorded failed classes; legacy 8 done uploads outside the tree are "
                     "already ingested and stay out of the work queue"),
            "history": [{
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "event": (f"reset recovery to GitHub (=B27): {len(entries)} in-scope PDFs "
                          f"scanned; {done} done by CSV citation ({len(cited)} cited sha16s); "
                          f"{failed} failed-class docs; batch_counter=27; next select yields B28")}]},
        "entries": entries}
    os.makedirs(os.path.dirname(QUEUE), exist_ok=True)
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    c = Counter(e["status"] for e in entries)
    print("STATUS|", dict(c))
    by_course = Counter(e["course"] for e in entries if e["status"] == "pending")
    print("PENDING_BY_COURSE|", dict(by_course))
    print(f"TOTAL|{len(entries)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
