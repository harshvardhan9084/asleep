#!/usr/bin/env python3
"""restore_queue_b48.py — rebuild queue state for the 2026-11-07 15:59 +08 fire
of Job 509551 (continuation of the B44-B48 same-Job lineage).

GitHub HEAD (B48-pushed CSV, 3081 data rows x 57 cols, commit da94b90) is the
authoritative baseline. B48 is COMPLETE (catalog(B48) pushed, 10/10 docs done;
plain-MCA completion + full BPharm + AE/AG waves via the 5-key mercury-3 pool).
NO in-flight batch remains: this restore leaves all non-done, non-failed PDFs
`pending` and sets batch_counter=48 so the next select yields B49 (B48 manifest:
"queue 16 pending — next select yields B49 (16 no-session/BTech docs: 14 BTech
+ 2 no-session books per the pending split)").

  - scans PDFs/5-course, status by CONTENT (sha16 citations in the current
    GitHub CSV -> done; recorded failed classes by basename);
  - B47's 10 rels are cited in the B47 CSV -> classified done naturally;
  - failed classes = the 8 recorded by B19/B23/B31/B44 manifests (2
    regulations + 4 content-dup + 2 policy).
B47-end live counts (manifest): 414 done / 26 pending / 8 failed = 448.
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
    "mba_syllabus_2017-18_2.pdf": "failed(content-equivalent-corroborating-copy)",
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
                    cited.update(re.findall(r"#([0-9a-f]{16})", cell))
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
        e["md5"] = md5_file(e["file"]); e["sha16"] = e["md5"][:16]
        cls = (FAILED_REGULATIONS.get(base) or FAILED_CONTENT_DUP.get(base)
               or FAILED_POLICY.get(base))
        if cls:
            e["status"] = cls
            e["notes"] += " | reset-restore: recorded failed class (B19/B23/B31/B44 manifests; RULES §9)"
            failed += 1
            continue
        if e["sha16"] in cited:
            e["status"] = "done"
            e["notes"] += (" | done: sha16 cited in GitHub CSV @B48 head da94b90 "
                           "(reset-restore; covers B01-B47 waves incl. B41-repair + "
                           "B42-B47 MBA/MCA waves + FIRST FULL PLAIN-MCA WAVE)")
            done += 1

    q = {"meta": {
            "batch_counter": 48,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": ("reset rebuild (2026-11-07 15:59 +08 fire of Job 509551): fresh scan of "
                     "PDFs/5-course; status by content against GitHub @da94b90 (3081 rows, B48 push). "
                     "B48 (09:30 +08 fire lineage) complete and pushed; "
                     "no in-flight batch; next select yields B49"),
            "history": [{
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "event": (f"reset recovery to GitHub @da94b90: {len(entries)} in-scope PDFs; "
                          f"{done} done by CSV citation ({len(cited)} cited sha16s); "
                          f"{failed} failed-class; batch_counter=48")}]},
        "entries": entries}
    os.makedirs(os.path.dirname(QUEUE), exist_ok=True)
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    c = Counter(e["status"] for e in entries)
    print("STATUS|", dict(c))
    # B48-end live counts (B48 manifest): 424 done / 16 pending / 8 failed = 448
    ok = (done == 424 and failed == 8 and len(entries) == 448)
    print("EXPECTED_MATCH|" + ("OK" if ok else f"MISMATCH done={done} failed={failed} total={len(entries)}"))
    return 0 if ok else 2


if __name__ == "__main__":
    import sys
    sys.exit(main())
