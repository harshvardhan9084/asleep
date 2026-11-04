#!/usr/bin/env python3
"""restore_queue_b32.py — rebuild queue state after a workspace reset (39th).

GitHub (=B31, CSV 2152 data rows, md5 b2451ff3b1edec5c0c4abe5134d55bd7,
commit 95e90bd) is the authoritative baseline. The 02:30 +08:00 cron trigger
(2026-11-05, trace ...202611050230) found the local workspace reset again:
work/repo_asleep wiped, .env GITHUB_PAT stripped, queue.json emptied,
worklog reduced to the B28 section. Recorded protocol applies (B28 open-item
6 / B29 open-item 9 / B30 open-item 8 / B31 restore class): rebuild the queue
by scanning PDFs/5-course, restore status by CONTENT (md5/sha16):
  - every `#<sha16>` token in ANY column of the GitHub B31 CSV marks that
    PDF done (this covers the B29/B30/B31 parallel-instance batches too —
    their docs are cited in the current CSV);
  - the recorded failed classes marked by basename (B19/B23 manifests +
    B31 manifest: 2 policy docs);
  - batch_counter := 31 so the next select_batch yields B32
    (B31 manifest end-state: 282 done / 159 pending / 7 failed).
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
FAILED_POLICY = {
    "btech_model-curriculum_2019-20.pdf": "failed(policy-scheme-docs-not-syllabus)",
    "btech_moocs-nptel-honours_2018-19.pdf": "failed(policy-moocs-nptel-rules-not-syllabus)",
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
        cls = (FAILED_REGULATIONS.get(base) or FAILED_CONTENT_DUP.get(base)
               or FAILED_POLICY.get(base))
        if cls:
            e["status"] = cls
            e["notes"] += " | reset-restore: recorded failed class (B19/B23/B31 manifests; RULES §9)"
            e["md5"] = md5_file(e["file"]); e["sha16"] = e["md5"][:16]
            failed += 1
            continue
        e["md5"] = md5_file(e["file"])
        e["sha16"] = e["md5"][:16]
        if e["sha16"] in cited:
            e["status"] = "done"
            e["notes"] += " | done: sha16 cited in GitHub B31 CSV (reset-restore; covers B29/B30/B31 parallel batches)"
            done += 1

    q = {"meta": {
            "batch_counter": 31,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": ("reset rebuild (39th): fresh scan of PDFs/5-course (owner uniform-name "
                     "layout); status restored by md5 content — GitHub B31 CSV citations + "
                     "recorded failed classes (incl. the 2 B31 policy docs); "
                     "next select yields B32"),
            "history": [{
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "event": (f"reset recovery to GitHub (=B31 @95e90bd): {len(entries)} in-scope PDFs "
                          f"scanned; {done} done by CSV citation ({len(cited)} cited sha16s); "
                          f"{failed} failed-class docs; batch_counter=31; next select yields B32")}]},
        "entries": entries}
    os.makedirs(os.path.dirname(QUEUE), exist_ok=True)
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    c = Counter(e["status"] for e in entries)
    print("STATUS|", dict(c))
    by_course = Counter(e["course"] for e in entries if e["status"] == "pending")
    print("PENDING_BY_COURSE|", dict(by_course))
    print(f"TOTAL|{len(entries)}")
    exp = {"done": 282, "pending": 159}
    failed_total = sum(v for k, v in c.items() if k.startswith("failed("))
    ok = c.get("done") == exp["done"] and c.get("pending") == exp["pending"] and failed_total == 7
    print("EXPECTED_MATCH|" + ("OK" if ok else
          f"MISMATCH expected done=282/pending=159/failed=7, got done={c.get('done')}/pending={c.get('pending')}/failed={failed_total}"))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
