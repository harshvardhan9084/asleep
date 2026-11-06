#!/usr/bin/env python3
"""restore_queue_b38.py — rebuild queue state after a workspace reset (42nd).

GitHub HEAD (7e80baa, B37-pushed CSV, 2346 data rows x 57 cols) is the
authoritative baseline. B37 is COMPLETE (catalog(B37) pushed, 10/10 docs done).
The B33 plastic wave (9 rels, durable drafts_B33 @8e1e8ad) remains the only
in-flight batch: this restore keeps those 9 rels `selected` batch=33 so this
run completes B33 without re-selection (B28 open-item 6 protocol; B37
precedent). All sha16s of the 9 durable drafts verified against the local PDFs
before this script was written.

  - scans PDFs/5-course, status by CONTENT (sha16 citations in the current
    GitHub CSV -> done; recorded failed classes by basename);
  - B37's 10 rels are now cited in the B37 CSV -> classified done naturally
    (spot-asserted below);
  - batch_counter := 37 (B37 completed by the previous run; next select
    yields B38; this run completes the in-flight B33).
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
# B33 in-flight batch (durable drafts_B33, sha16-verified against local PDFs):
B33_BATCH = {
    1: ("2009-10", "btech_plastic_syllabus_2009-10.pdf"),
    2: ("2018-19", "btech_plastic_syllabus_2018-19.pdf"),
    3: ("2020-21", "btech_plastic_syllabus_2020-21.pdf"),
    4: ("2019-20", "btech_plastic_y2_model-curriculum_2019-20.pdf"),
    5: ("2017-18", "btech_plastic_y2_scheme-syllabus_2017-18.pdf"),
    6: ("2024-25", "btech_plastic_y3_syllabus_2024-25.pdf"),
    7: ("2019-20", "btech_plastic_y4_syllabus-cbcs_2019-20.pdf"),
    8: ("2016-17", "btech_plastic_y4_syllabus_2016-17.pdf"),
    9: ("2021-22", "btech_plastic_y4_syllabus_2021-22.pdf"),
}
B37_BATCH = {
    "2020-21/btech_s5-6_non-credit-courses_2020-21.pdf",
    "2009-10/btech_syllabus_2009-10.pdf",
    "2013-14/btech_syllabus_2013-14.pdf",
    "2009-10/btech_textile-chem-texteng-mmft_y2_syllabus_2009-10.pdf",
    "2019-20/btech_textile-chemistry_y2_model-curriculum_2019-20.pdf",
    "2017-18/btech_textile-chemistry_y2_scheme-syllabus_2017-18.pdf",
    "2018-19/btech_textile-chemistry_y3_syllabus_2018-19.pdf",
    "2019-20/btech_textile-chemistry_y4_syllabus-cbcs_2019-20.pdf",
    "2026-27/btech_textile-tech_course-structure_2026-27.pdf",
    "2018-19/btech_textile-tech_syllabus_2018-19.pdf",
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

    b33_lookup = {(sd, fn): slot for slot, (sd, fn) in B33_BATCH.items()}
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
    b37_done_missing = []
    for e in entries:
        base = os.path.basename(e["rel"])
        e["md5"] = md5_file(e["file"]); e["sha16"] = e["md5"][:16]
        slot = b33_lookup.get((os.path.basename(os.path.dirname(e["rel"])), base))
        if slot is not None:
            e["status"] = "selected"; e["batch"] = 33; e["attempts"] = 1
            e["staged_stem"] = f"{slot:02d}_{base[:-4]}"
            e["notes"] += (" | in-flight B33 resume (slot 0%d; durable draft "
                           "drafts_B33 @8e1e8ad adopted this run) — select_batch "
                           "must not double-claim (B28 open-item 6 protocol)" % slot)
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
            e["notes"] += (" | done: sha16 cited in GitHub CSV @7e80baa (reset-restore; "
                           "covers B01–B32 waves + B34/B35/B36 recovery replay + B37)")
            done += 1
            sd = os.path.basename(os.path.dirname(e["rel"]))
            if f"{sd}/{base}" in B37_BATCH:
                b37n += 1
        elif f"{os.path.basename(os.path.dirname(e['rel']))}/{base}" in B37_BATCH:
            b37_done_missing.append(e["rel"])

    q = {"meta": {
            "batch_counter": 37,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": ("reset rebuild (42nd): fresh scan of PDFs/5-course; status by content "
                     "against GitHub @7e80baa (2346 rows, B37 push). B37 complete: 10/10 "
                     "rels classified done by citation. 9 plastic rels stay selected-batch-33 "
                     "(in-flight B33, durable drafts_B33); this run completes B33; "
                     "next select yields B38"),
            "history": [{
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "event": (f"reset recovery to GitHub @7e80baa: {len(entries)} in-scope PDFs; "
                          f"{done} done by CSV citation ({len(cited)} cited sha16s; incl. "
                          f"{b37n}/10 B37 rels); {failed} failed-class; {claimed} "
                          f"selected=B33 in-flight; batch_counter=37")}]},
        "entries": entries}
    os.makedirs(os.path.dirname(QUEUE), exist_ok=True)
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    c = Counter(e["status"] for e in entries)
    print("STATUS|", dict(c))
    b33_rels = sorted(e["rel"] for e in entries if e["batch"] == 33)
    print(f"B33|{claimed} rels")
    for r in b33_rels:
        print("  B33REL|" + r)
    for r in b37_done_missing:
        print("  B37_NOT_CITED|" + r)
    # 305 = 294 (B36-era state) + 10 B37 docs + 1 md5-twin of B37 doc-01
    # (btech_y3s5-6_non-credit-courses_2020-21.pdf, identical content, cited by
    # the same sha16 07fa7e05... — content-based classification marks it done;
    # RULES §9 md5 content-dedup).
    ok = (claimed == 9 and failed == 7 and b37n == 10 and done == 305 and not b37_done_missing)
    print("EXPECTED_MATCH|" + ("OK" if ok else f"MISMATCH claimed={claimed} failed={failed} b37done={b37n} done={done}"))
    return 0 if ok else 2


if __name__ == "__main__":
    import sys
    sys.exit(main())
