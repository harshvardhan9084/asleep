#!/usr/bin/env python3
"""restore_queue_b34.py — rebuild queue state after a workspace reset (40th).

GitHub HEAD (8e1e8ad, CSV md5 7bd4bd649dc511de3e55e42e94f5f3b8, 2094 data
rows x 57 cols) is the authoritative baseline. NOTE (incident, recorded): the
CRON-20261105-B29 instance pushed catalog(aed10a5) from a stale B28-era local
baseline (2034 rows) AFTER B30/B31/B32 had published 2196 rows — the repo CSV
regressed 2196→2094, losing the B30 (+31 appends), B31 (+33), B32 (+44)
merged content. Their verified drafts + adjudication blocks are durable in
pipeline/drafts_B30|B31|B32/ + adjudicate_b30|31|32.py, so the loss is
recoverable by re-selecting those docs and re-merging the durable drafts.

This restore:
  - scans PDFs/5-course, status by CONTENT (sha16 citations in the current
    GitHub CSV → done; recorded failed classes by basename);
  - the 9 plastic rels with durable drafts_B33 (in-flight parallel instance,
    wave-1+2 pushed 8e1e8ad, not yet merged) are marked `selected` batch=33
    so select_batch never double-claims them (recorded B28 open-item 6
    parallel-instance protocol);
  - batch_counter := 33 → the next select yields B34.
"""
import csv, hashlib, json, os, re
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

# B33 in-flight claims (pipeline/drafts_B33/ = 9 durable drafts, docs 01-09)
B33_CLAIMED = {
    "btech_plastic_syllabus_2009-10.pdf",
    "btech_plastic_syllabus_2018-19.pdf",
    "btech_plastic_syllabus_2020-21.pdf",
    "btech_plastic_y2_model-curriculum_2019-20.pdf",
    "btech_plastic_y2_scheme-syllabus_2017-18.pdf",
    "btech_plastic_y3_syllabus_2024-25.pdf",
    "btech_plastic_y4_syllabus-cbcs_2019-20.pdf",
    "btech_plastic_y4_syllabus_2016-17.pdf",
    "btech_plastic_y4_syllabus_2021-22.pdf",
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

    done = failed = claimed = 0
    for e in entries:
        base = os.path.basename(e["rel"])
        e["md5"] = md5_file(e["file"]); e["sha16"] = e["md5"][:16]
        if base in B33_CLAIMED:
            e["status"] = "selected"; e["batch"] = 33
            e["notes"] += (" | selected: claimed by in-flight parallel instance B33 "
                           "(drafts_B33 durable @8e1e8ad, not yet merged) — select_batch "
                           "must not double-claim (B28 open-item 6 protocol)")
            claimed += 1
            continue
        cls = (FAILED_REGULATIONS.get(base) or FAILED_CONTENT_DUP.get(base)
               or FAILED_POLICY.get(base))
        if cls:
            e["status"] = cls
            e["notes"] += " | reset-restore: recorded failed class (B19/B23/B31 manifests; RULES §9)"
            failed += 1
            continue
        if e["sha16"] in cited:
            e["status"] = "done"
            e["notes"] += (" | done: sha16 cited in GitHub CSV @8e1e8ad (reset-restore; "
                           "covers B28/B29-2nd waves; NOTE B30/B31/B32 content lost by "
                           "the CRON-20261105-B29 stale-baseline push — their docs scan "
                           "as pending for re-processing)")
            done += 1

    q = {"meta": {
            "batch_counter": 33,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": ("reset rebuild (40th): fresh scan of PDFs/5-course; status by content "
                     "against GitHub @8e1e8ad (2094 rows). INCIDENT recorded: catalog "
                     "regressed 2196→2094 (CRON-20261105-B29 stale-baseline push aed10a5) — "
                     "B30/B31/B32 merged content lost, durable drafts recoverable; 9 plastic "
                     "rels selected-batch-33 for the in-flight B33 instance; "
                     "next select yields B34"),
            "history": [{
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "event": (f"reset recovery to GitHub @8e1e8ad: {len(entries)} in-scope PDFs; "
                          f"{done} done by CSV citation ({len(cited)} cited sha16s); "
                          f"{failed} failed-class; {claimed} selected=B33-claimed; "
                          f"batch_counter=33; next select yields B34")}]},
        "entries": entries}
    os.makedirs(os.path.dirname(QUEUE), exist_ok=True)
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    c = Counter(e["status"] for e in entries)
    print("STATUS|", dict(c))
    by_course = Counter(e["course"] for e in entries if e["status"] == "pending")
    print("PENDING_BY_COURSE|", dict(by_course))
    print(f"TOTAL|{len(entries)}")
    # spot-check the three lost-wave docs are pending again (recoverable)
    spot = {"btech_mfg-tech_syllabus_2010-11.pdf": None,
            "btech_mining_y3_syllabus_2025-26.pdf": None,
            "btech_pe-ipe_y4_syllabus_2025-26.pdf": None}
    for e in entries:
        b = os.path.basename(e["rel"])
        if b in spot:
            spot[b] = e["status"]
    print("SPOT|", spot)
    ok = all(v == "pending" for v in spot.values()) and claimed == 9
    print("EXPECTED_MATCH|" + ("OK" if ok else f"MISMATCH spot={spot} claimed={claimed}"))
    return 0 if ok else 2


if __name__ == "__main__":
    sys_exit = main()
    import sys
    sys.exit(sys_exit)
