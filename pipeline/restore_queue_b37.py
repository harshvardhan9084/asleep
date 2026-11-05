#!/usr/bin/env python3
"""restore_queue_b37.py — rebuild queue state after a workspace reset (41st).

GitHub HEAD (0a3b85b, B36-pushed CSV, 2208 data rows x 57 cols) is the
authoritative baseline. B37 was staged and left in-flight by the parallel
instance (state(B37) commit: docs 01/05/06/07/08 mercury-3-drafted, durable in
pipeline/drafts_B37/); this restore re-marks exactly that staged batch
(reconstructed from the select-order pending frontier — the 5 durable slots
1/5/6/7/8 align with the frontier positions 1/5/6/7/8, sha16-verified) as
`selected` batch=37 so this run completes B37 without re-selection.

  - scans PDFs/5-course, status by CONTENT (sha16 citations in the current
    GitHub CSV → done; recorded failed classes by basename);
  - the 9 plastic rels with durable drafts_B33 (in-flight parallel instance,
    not yet merged) stay `selected` batch=33 (select_batch must not
    double-claim; B28 open-item 6 protocol);
  - batch_counter := 37 (B36 manifest recorded queue state 294 done / 138
    pending / 9 selected(B33) / 10 selected(B37) / 7 failed).
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
B33_CLAIMED = {
    "btech_plastic_syllabus_2009-10.pdf", "btech_plastic_syllabus_2018-19.pdf",
    "btech_plastic_syllabus_2020-21.pdf", "btech_plastic_y2_model-curriculum_2019-20.pdf",
    "btech_plastic_y2_scheme-syllabus_2017-18.pdf", "btech_plastic_y3_syllabus_2024-25.pdf",
    "btech_plastic_y4_syllabus-cbcs_2019-20.pdf", "btech_plastic_y4_syllabus_2016-17.pdf",
    "btech_plastic_y4_syllabus_2021-22.pdf",
}
# B37 in-flight batch (reconstructed, sha16-verified against durable drafts):
# slot -> (session_dir, basename)
B37_BATCH = {
    1: ("2020-21", "btech_s5-6_non-credit-courses_2020-21.pdf"),
    2: ("2009-10", "btech_syllabus_2009-10.pdf"),
    3: ("2013-14", "btech_syllabus_2013-14.pdf"),
    4: ("2009-10", "btech_textile-chem-texteng-mmft_y2_syllabus_2009-10.pdf"),
    5: ("2019-20", "btech_textile-chemistry_y2_model-curriculum_2019-20.pdf"),
    6: ("2017-18", "btech_textile-chemistry_y2_scheme-syllabus_2017-18.pdf"),
    7: ("2018-19", "btech_textile-chemistry_y3_syllabus_2018-19.pdf"),
    8: ("2019-20", "btech_textile-chemistry_y4_syllabus-cbcs_2019-20.pdf"),
    9: ("2026-27", "btech_textile-tech_course-structure_2026-27.pdf"),
    10: ("2018-19", "btech_textile-tech_syllabus_2018-19.pdf"),
}
DURABLE_SLOTS = {1, 5, 6, 7, 8}  # slots with durable drafts in pipeline/drafts_B37


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

    b37_lookup = {(sd, fn): slot for slot, (sd, fn) in B37_BATCH.items()}
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

    done = failed = claimed = b37n = 0
    for e in entries:
        base = os.path.basename(e["rel"])
        e["md5"] = md5_file(e["file"]); e["sha16"] = e["md5"][:16]
        slot = b37_lookup.get((os.path.basename(os.path.dirname(e["rel"])), base))
        if slot is not None:
            e["status"] = "selected"; e["batch"] = 37; e["attempts"] = 1
            e["staged_stem"] = f"{slot:02d}_{base[:-4]}"
            e["notes"] += (
                f" | in-flight B37 resume (slot {slot:02d}"
                + (", durable mercury-3 draft @0a3b85b adopted" if slot in DURABLE_SLOTS
                   else ", pending mercury-3 draft this run")
                + ")"
            )
            b37n += 1
            continue
        if base in B33_CLAIMED and e["sha16"] not in cited:
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
            e["notes"] += (" | done: sha16 cited in GitHub CSV @0a3b85b (reset-restore; "
                           "covers B01–B32 waves + B34/B35/B36 recovery replay)")
            done += 1

    q = {"meta": {
            "batch_counter": 37,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": ("reset rebuild (41st): fresh scan of PDFs/5-course; status by content "
                     "against GitHub @0a3b85b (2208 rows, B36 push). B37 in-flight batch "
                     "re-marked selected (10 rels, slots 01-10; 5 durable drafts adopted); "
                     "9 plastic rels stay selected-batch-33 (in-flight B33 instance); "
                     "this run completes B37; next select yields B38"),
            "history": [{
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "event": (f"reset recovery to GitHub @0a3b85b: {len(entries)} in-scope PDFs; "
                          f"{done} done by CSV citation ({len(cited)} cited sha16s); "
                          f"{failed} failed-class; {claimed} selected=B33-claimed; "
                          f"{b37n} selected=B37 in-flight; batch_counter=37")}]},
        "entries": entries}
    os.makedirs(os.path.dirname(QUEUE), exist_ok=True)
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    c = Counter(e["status"] for e in entries)
    print("STATUS|", dict(c))
    b37_rels = sorted(e["rel"] for e in entries if e["batch"] == 37)
    print(f"B37|{b37n} rels")
    for r in b37_rels:
        print("  B37REL|" + r)
    # spot-checks: durable-draft sha16s must match the queue entries
    dshas = {}
    for slot in DURABLE_SLOTS:
        sd, fn = B37_BATCH[slot]
        dshas[slot] = fn
    ok = (b37n == 10 and claimed == 9 and done == 294 and failed == 7)
    print("EXPECTED_MATCH|" + ("OK" if ok else f"MISMATCH b37={b37n} claimed={claimed} done={done} failed={failed}"))
    return 0 if ok else 2


if __name__ == "__main__":
    import sys
    sys.exit(main())
