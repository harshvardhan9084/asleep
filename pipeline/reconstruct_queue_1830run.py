#!/usr/bin/env python3
"""reconstruct_queue_1830run.py — one-off queue reconstruction after the
2026-10-28 workspace reset.

The 18:30 cron run ingested 5 corpus docs and pushed commit 8cabc73 before
the reset wiped the local queue/parsed/drafts state. This script restores
their queue entries from the push's recorded provenance (evidence: the 62
appended rows' source_syllabus citations in 8cabc73):

  - bpharm_y1-2_syllabus_2013-14.pdf  -> done (40 BPharm rows verified intact
    by the §1b repair pass: sources BPharm-only, course canon clean)
  - bca_y1_syllabus_2024-25.pdf       -> pending-pinned (RE-DRAFT: its same-name
    subjects were merged into BTech rows and reverted per §1b; the 12 existing
    BCA rows from this doc will Tier-match; the missing subjects re-append)
  - bca_y1_syllabus_2025-26.pdf       -> pending-pinned (same)
  - bca_y2_syllabus_2025-26.pdf       -> pending-pinned (same)
  - bca_s1-2_bbc107-207-non-credit-bridge-course_2025-26.pdf -> pending-pinned

Idempotent: entries are keyed by rel; re-running does nothing.
"""
import json, hashlib, os, sys
from datetime import datetime, timezone

QUEUE = "/home/z/my-project/work/pipeline_v2/queue.json"
ROOT = "/home/z/my-project/work"
REPO = "repo_asleep/PDFs/5-course"

DOCS = [
    ("2013-14/bpharm_y1-2_syllabus_2013-14.pdf", "done", "2013-14", "BPharm",
     "RECONSTRUCTED 2026-10-28: ingested by the 18:30 run (evidence: 40 BPharm rows' source_syllabus cite this doc in push 8cabc73); rows verified intact during the RULES §1b repair (course canon, BPharm-only sources); no re-draft needed."),
    ("2024-25/bca_y1_syllabus_2024-25.pdf", "pending-pinned", "2024-25", "BCA",
     "RECONSTRUCTED 2026-10-28: the 18:30 run ingested this doc (evidence: BCA rows + cross-course contamination in push 8cabc73) but its same-name subjects were merged into BTech rows and REVERTED per RULES §1b; 12 BCA rows from this doc remain valid (Tier-match on re-draft); missing subjects re-append as BCA rows. Re-draft required with correct course=BCA."),
    ("2025-26/bca_y1_syllabus_2025-26.pdf", "pending-pinned", "2025-26", "BCA",
     "RECONSTRUCTED 2026-10-28: cited in 8cabc73 contamination; same §1b re-draft rationale as bca_y1_syllabus_2024-25."),
    ("2025-26/bca_y2_syllabus_2025-26.pdf", "pending-pinned", "2025-26", "BCA",
     "RECONSTRUCTED 2026-10-28: cited in 8cabc73 contamination (operating-systems, technical-communication, universal-human-values, web-technology(+lab) BTech rows were polluted from this doc and reverted); 10 BCA y2 rows remain valid; missing subjects re-append. Re-draft required with correct course=BCA."),
    ("2025-26/bca_s1-2_bbc107-207-non-credit-bridge-course_2025-26.pdf", "pending-pinned", "2025-26", "BCA",
     "RECONSTRUCTED 2026-10-28: cited in 8cabc73 (elementary-mathematics-bridge-course row BBC107;BBC207); re-draft corroborates existing row and surfaces any remaining bridge subjects."),
]


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    q = json.load(open(QUEUE))
    have = {e["rel"] for e in q["entries"]}
    added, updated = [], []
    for rel, status, session, course, note in DOCS:
        full = os.path.join(ROOT, REPO, rel)
        if not os.path.isfile(full):
            print(f"MISSING|{rel}")
            continue
        m = md5(full)
        if rel in have:
            e = next(e for e in q["entries"] if e["rel"] == rel)
            if e.get("status") == status:
                continue
            e["status"] = status
            e.setdefault("notes", "")
            e["notes"] += " | " + note
            updated.append(rel)
        else:
            q["entries"].append({
                "rel": f"{REPO}/{rel}", "file": full, "session": session,
                "course": course, "status": status, "md5": m, "sha16": m[:16],
                "attempts": 0, "batch": 0, "notes": note})
            added.append(rel)
    q["meta"].setdefault("history", []).append({
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": ("queue reconstruction after workspace reset: 5 docs of the 18:30 run "
                  "restored from push 8cabc73 provenance; bpharm done, 4 BCA docs "
                  "pending-pinned for §1b-compliant re-draft")})
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    print(f"ADDED|{len(added)}|UPDATED|{len(updated)}")
    for r in added + updated:
        print(" ", r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
