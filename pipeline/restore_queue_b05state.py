#!/usr/bin/env python3
"""restore_queue_b05state.py — one-off queue reconstruction after the
2026-10-29 (2nd) workspace reset rolled local files back to the Oct-27 B02
snapshot. GitHub HEAD 12819c8 holds B05-complete state (526 rows x 57 cols).

Evidence chain (syllabus_catalog/runs/ manifests in the clone):
- B03 (2f551ad): 4 BCA rels re-ingested per RULES 1b (b04 manifest context
  records them as "pre-marked done") + bpharm_y1-2_2013-14 was ingested by
  the 18:30 run (8cabc73) and RE-drafted in B04 (#05).
- B04 (189ba64): 10 docs — 8 done (bca_y3 + 7 BPharm syllabi) + 2 failed
  regulations-only (bpharm_ordinances_2019-20, bpharm_regulations-ordinances_2026-27).
- B04-repair (43cea6a): field repairs only — no queue impact.
- B05 (12819c8): 10 docs — 4 BPharm + 6 BTech ACT/AE, all done.

Idempotent: keyed by rel; re-running does nothing.
"""
import json, hashlib, os
from datetime import datetime, timezone

QUEUE = "/home/z/my-project/work/pipeline_v2/queue.json"
ROOT = "/home/z/my-project/work"
REPO = "repo_asleep/PDFs/5-course"

DONE = [
    # --- B03 (2f551ad): BCA re-ingestion per RULES 1b ---
    ("2024-25/bca_y1_syllabus_2024-25.pdf", "2024-25", "BCA",
     "RECONSTRUCTED 2026-10-29 (2nd reset): ingested by B03 re-ingestion (2f551ad) per RULES 1b; BCA rows verified course-clean in B04 run; never re-process."),
    ("2025-26/bca_y1_syllabus_2025-26.pdf", "2025-26", "BCA",
     "RECONSTRUCTED 2026-10-29 (2nd reset): ingested by B03 re-ingestion (2f551ad) per RULES 1b; never re-process."),
    ("2025-26/bca_y2_syllabus_2025-26.pdf", "2025-26", "BCA",
     "RECONSTRUCTED 2026-10-29 (2nd reset): ingested by B03 re-ingestion (2f551ad) per RULES 1b; never re-process."),
    ("2025-26/bca_s1-2_bbc107-207-non-credit-bridge-course_2025-26.pdf", "2025-26", "BCA",
     "RECONSTRUCTED 2026-10-29 (2nd reset): ingested by B03 re-ingestion (2f551ad); elementary-mathematics-bridge-course row BBC107;BBC207 corroborated; never re-process."),
    # --- B04 (189ba64): 1 BCA + 7 BPharm done, 2 failed ---
    ("2026-27/bca_y3_syllabus_2026-27.pdf", "2026-27", "BCA",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B04 #01 (189ba64) 16 subjects BBC501-652 + elective pool BBC011-015; never re-process."),
    ("2013-14/bpharm_y1-2_syllabus_2013-14.pdf", "2013-14", "BPharm",
     "RECONSTRUCTED 2026-10-29 (2nd reset): first ingested 18:30 run (8cabc73), re-drafted as B04 #05 (189ba64) 40 subjects BOP-111..BOP-245P; never re-process."),
    ("2026-27/bpharm_scheme-syllabus_2026-27.pdf", "2026-27", "BPharm",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B04 #04 (189ba64) 121 subjects BP101T-BP816P + appendix elective pools; never re-process."),
    ("2019-20/bpharm_y1-4_syllabus_2019-20.pdf", "2019-20", "BPharm",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B04 #06 (189ba64) 83 subjects BP101T-BP816P PCI era; never re-process."),
    ("2016-17/bpharm_y1_scheme_2016-17.pdf", "2016-17", "BPharm",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B04 #07 (189ba64) 20 subjects RPH-101..RPH-210P era; never re-process."),
    ("2017-18/bpharm_y1_syllabus_2017-18.pdf", "2017-18", "BPharm",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B04 #08 (189ba64) 23 subjects BP101T-BP210P early-PCI era; never re-process."),
    ("2017-18/bpharm_y2_scheme-syllabus_2017-18.pdf", "2017-18", "BPharm",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B04 #09 (189ba64) 17 subjects BP301T-BP409P; never re-process."),
    ("2017-18/bpharm_y2_scheme-syllabus_2017-18_2.pdf", "2017-18", "BPharm",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B04 #10 (189ba64) 20 subjects RPH301-410 + RCA305 + RVE401; never re-process."),
    # --- B05 (12819c8): 4 BPharm + 6 BTech ---
    ("2019-20/bpharm_y2_syllabus_2019-20.pdf", "2019-20", "BPharm",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B05 #01 (12819c8) 18 subjects; never re-process."),
    ("2019-20/bpharm_y3_syllabus_2019-20.pdf", "2019-20", "BPharm",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B05 #02 (12819c8) 17 subjects; never re-process."),
    ("2019-20/bpharm_y4_syllabus-cbcs_2019-20.pdf", "2019-20", "BPharm",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B05 #03 (12819c8) 28 subjects; never re-process."),
    ("2020-21/bpharm_y4_syllabus-rev_2020-21.pdf", "2020-21", "BPharm",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B05 #04 (12819c8) 22 subjects; never re-process."),
    ("2025-26/btech_act_y3_syllabus-rev_2025-26.pdf", "2025-26", "BTech",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B05 #05 (12819c8) 31 subjects; never re-process."),
    ("2026-27/btech_act_y4_syllabus_2026-27.pdf", "2026-27", "BTech",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B05 #06 (12819c8) 6 subjects + 14 nsr; never re-process."),
    ("2020-21/btech_ae_syllabus_2020-21.pdf", "2020-21", "BTech",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B05 #07 (12819c8) 32 subjects; never re-process."),
    ("2019-20/btech_ae_y2_model-curriculum_2019-20.pdf", "2019-20", "BTech",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B05 #08 (12819c8) 13 subjects; never re-process."),
    ("2018-19/btech_ae_y3_syllabus_2018-19.pdf", "2018-19", "BTech",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B05 #09 (12819c8) 27 subjects; never re-process."),
    ("2024-25/btech_ae_y3_syllabus_2024-25.pdf", "2024-25", "BTech",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B05 #10 (12819c8) 26 subjects; never re-process."),
]

FAILED = [
    ("2019-20/bpharm_ordinances_2019-20.pdf", "2019-20", "BPharm",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B04 #02 (189ba64) --failed regulations-only doc, 0 subjects, 61 non_subject_rows preserved in draft."),
    ("2026-27/bpharm_regulations-ordinances_2026-27.pdf", "2026-27", "BPharm",
     "RECONSTRUCTED 2026-10-29 (2nd reset): B04 #03 (189ba64) --failed regulations-only doc, 0 subjects, 58 non_subject_rows preserved in draft."),
]


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    q = json.load(open(QUEUE))
    entries = q["entries"]
    have = {e["rel"] for e in entries}
    now = datetime.now(timezone.utc).isoformat()
    added, skipped = 0, 0
    for rel, session, course, note in DONE + FAILED:
        status = "done" if (rel, session, course, note) in DONE else "failed"
        full = os.path.join(ROOT, REPO, rel)
        if not os.path.isfile(full):
            print(f"MISSING|{rel}")
            continue
        if rel in have:
            skipped += 1
            continue
        m = md5(full)
        entries.append({
            "rel": f"{REPO}/{rel}",
            "file": full,
            "session": session,
            "course": course,
            "status": status,
            "notes": note,
            "md5": m,
            "sha16": m[:16],
            "batch": 3 if rel.startswith(("2024-25/", "2025-26/")) and "bca" in rel else 4,
            "attempts": 1,
            "done_ts" if status == "done" else "failed_ts": now,
        })
        added += 1
    # batch_counter: B05 exists on GitHub -> next selection is batch 6
    q["meta"]["batch_counter"] = 5
    q["meta"]["history"] = q["meta"].get("history", [])
    q["meta"]["history"].append(
        "2026-10-29 (2nd reset): local queue rolled back to Oct-27 B02 snapshot; "
        "reconstructed B03/B04/B05 done-set from GitHub runs manifests (2f551ad/189ba64/43cea6a/12819c8); "
        "batch_counter aligned to 5; next selection = batch 6.")
    json.dump(q, open(QUEUE, "w"), indent=1, ensure_ascii=False)
    print(f"added={added} skipped={skipped} total={len(entries)} batch_counter=5")


if __name__ == "__main__":
    main()
