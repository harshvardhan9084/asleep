#!/usr/bin/env python3
"""restore_queue_b50.py — citation-based queue rebuild vs GitHub B50 head a1c5b64.
Re-created after the 44th workspace reset (owner audit turn, 2026-11-07)."""
import csv, hashlib, json, os, re
from datetime import datetime, timezone
from collections import Counter

QUEUE = "/home/z/my-project/work/pipeline_v2/queue.json"
REPO_CSV = "/home/z/my-project/work/repo_asleep/syllabus_catalog/syllabus_extreme_rich.csv"
CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
SCAN = "/home/z/my-project/work/repo_asleep/PDFs/5-course"
FAILED_REGULATIONS = {"bpharm_ordinances_2019-20.pdf": "failed(regulations-not-syllabus)", "bpharm_regulations-ordinances_2026-27.pdf": "failed(regulations-not-syllabus)"}
FAILED_CONTENT_DUP = {"btech_ag_y4_syllabus_2016-17_2.pdf": "failed(content-equivalent-corroborating-copy)", "btech_ai-ml_y3_syllabus_2024-25.pdf": "failed(content-duplicate-corroborating-copy)", "btech_ce_y3_syllabus_2024-25.pdf": "failed(content-equivalent-corroborating-copy)", "mba_syllabus_2017-18_2.pdf": "failed(content-equivalent-corroborating-copy)", "btech_en_y4_syllabus_2.pdf": "failed(content-equivalent-corroborating-copy)", "btech_ras402-environment-ecology.pdf": "failed(content-equivalent-corroborating-copy)", "btech_s3-4_kas302-402h-maths-iv-pde-probability-statistics_2.pdf": "failed(content-duplicate-corroborating-copy)", "btech_s4_kve401-universal-human-values-professional-ethics.pdf": "failed(content-duplicate-corroborating-copy)"}
FAILED_POLICY = {"btech_model-curriculum_2019-20.pdf": "failed(policy-scheme-docs-not-syllabus)", "btech_moocs-nptel-honours_2018-19.pdf": "failed(policy-moocs-nptel-rules-not-syllabus)", "btech_moocs.pdf": "failed(policy-moocs-nptel-rules-not-syllabus)"}
FAILED_NONSYLLABUS = {"btech_ece_syllabus.pdf": "failed(non-syllabus-lecture-notes)"}

def md5_file(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def course_from_filename(n):
    n = n.lower()
    if re.search(r"(^|[\W_])bca([\W_]|$)", n) or n.startswith("bca"): return "BCA"
    if "bpharm" in n or "b-pharm" in n or "b.pharm" in n: return "BPharm"
    if re.search(r"(^|[\W_])mca([\W_]|$)", n) or n.startswith("mca"): return "MCA"
    if re.search(r"(^|[\W_])mba([\W_]|$)", n) or n.startswith("mba"): return "MBA"
    return "BTech"

def main():
    if md5_file(CSV) != md5_file(REPO_CSV):
        print("ABORT: local baseline CSV md5 != repo CSV md5"); return 2
    cited = set()
    with open(REPO_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for cell in row.values():
                if cell and "#" in cell:
                    cited.update(re.findall(r"#([0-9a-f]{16})", cell))
    entries = []
    for sd in sorted(os.listdir(SCAN)):
        sdir = os.path.join(SCAN, sd)
        if not os.path.isdir(sdir): continue
        session = "" if sd == "no_session_found" else sd
        for fn in sorted(os.listdir(sdir)):
            if not fn.lower().endswith(".pdf"): continue
            entries.append({"rel": f"repo_asleep/PDFs/5-course/{sd}/{fn}", "file": os.path.join(sdir, fn),
                            "session": session, "course": course_from_filename(fn), "status": "pending",
                            "md5": "", "sha16": "", "attempts": 0, "batch": 0,
                            "notes": "corpus enqueue (asleep repo, 5-course tree, uniform-name layout)"})
    done = failed = uncited = 0
    for e in entries:
        base = os.path.basename(e["rel"])
        e["md5"] = md5_file(e["file"]); e["sha16"] = e["md5"][:16]
        cls = (FAILED_REGULATIONS.get(base) or FAILED_CONTENT_DUP.get(base) or FAILED_POLICY.get(base) or FAILED_NONSYLLABUS.get(base))
        if cls:
            e["status"] = cls; e["notes"] += " | restore: recorded failed class (manifests B19-B50; RULES Â§9)"; failed += 1; continue
        if e["sha16"] in cited:
            e["status"] = "done"; e["notes"] += " | done: sha16 cited in GitHub CSV @B50 head a1c5b64"; done += 1
        else:
            uncited += 1; print("UNCITED:", e["rel"])
    q = {"meta": {"batch_counter": 50, "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "note": ("reset rebuild (44th reset, 2026-11-07 owner audit turn): fresh scan; status by content "
                           "against GitHub @a1c5b64 (3097 rows, B50 push); corpus fully processed; next select NO_PENDING"),
                  "history": [{"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "event": f"reset recovery to GitHub @a1c5b64: {len(entries)} PDFs; {done} done by citation ({len(cited)} cited sha16s); {failed} failed-class; {uncited} uncited; batch_counter=50"}]},
         "entries": entries}
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    print("STATUS|", dict(Counter(e["status"] for e in entries)))
    ok = (done == 434 and failed == 14 and len(entries) == 448)
    print("EXPECTED_MATCH|" + ("OK" if ok else f"MISMATCH done={done} failed={failed} total={len(entries)}"))
    return 0 if ok else 2

if __name__ == "__main__":
    import sys; sys.exit(main())
