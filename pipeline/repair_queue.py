#!/usr/bin/env python3
"""repair_queue.py — rebuild queue.json with correct session detection.

Bug being fixed: make_queue computed rel from REPO root (3 parts) but its session
logic expected 2 parts, so ALL repo entries were labeled 'no_session_found'.

Repair:
- session = folder under 5-course/ (parts[1] of the repo-root rel)
- statuses migrated from the old queue by sha16 (path-independent)
- duplicate-content entries (same sha16 appearing under several folders) collapse
  to ONE canonical entry (the newest-session path); others recorded in 'dup_of'
- already-processed sha16s keep status done
"""
import hashlib, json, os, re, sys

REPO = "/home/z/my-project/work/repo_asleep/PDFs"
LOCAL2 = "/home/z/my-project/work/artd_v3/sources"
QUEUE = "/home/z/my-project/work/pipeline_v2/queue.json"

def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]

def main():
    old = json.load(open(QUEUE, encoding="utf-8"))
    old_by_sha = {}
    for e in old["entries"]:
        old_by_sha.setdefault(e.get("sha16"), e["status"])

    # enumerate repo files with correct sessions
    raw = {}
    root = os.path.join(REPO, "5-course")
    for dp, _dn, fn in os.walk(root):
        for f in sorted(fn):
            if not f.lower().endswith(".pdf"):
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, REPO)  # 5-course/<session>/<file>
            parts = rel.split(os.sep)
            session = parts[1] if len(parts) == 3 and parts[0] == "5-course" else "no_session_found"
            key = f"5-course/{session}/{f}"
            raw[key] = {"rel": key, "repo_path": p, "session": session, "f": f}

    # collapse duplicate content: same sha16 -> canonical = newest session path
    by_sha = {}
    for key in sorted(raw):
        info = raw[key]
        s = sha16(info["repo_path"])
        info["sha16"] = s
        sess_rank = -int(session_year(info["session"]) or 0)
        prev = by_sha.get(s)
        if prev is None or sess_rank < prev[0]:
            by_sha[s] = (sess_rank, key, info)
    entries = []
    for s, (_rank, key, info) in by_sha.items():
        status = old_by_sha.get(s, "pending")
        entries.append({
            "rel": info["rel"], "repo_path": info["repo_path"], "session": info["session"],
            "status": status, "sha16": s, "bytes": os.path.getsize(info["repo_path"]),
            "pinned": False, "note": "",
        })
    # local pinned PDFs
    for f in sorted(os.listdir(LOCAL2)):
        if f.lower().endswith(".pdf"):
            p = os.path.join(LOCAL2, f)
            s = sha16(p)
            status = old_by_sha.get(s, "pending-pinned")
            entries.append({"rel": f"local/{f}", "repo_path": p, "session": "2023-24",
                            "status": status, "sha16": s, "bytes": os.path.getsize(p),
                            "pinned": True, "note": "owner-approved 2026-10 run"})

    def key(e):
        sess_rank = 0 if e["pinned"] else (1 if e["session"] != "no_session_found" else 2)
        y = session_year(e["session"])
        return (sess_rank, -(y or 0), e["rel"])
    entries.sort(key=key)

    q = {"built_by": "repair_queue.py", "built_on": "2026-10-27",
         "scope": "5-course deduped-by-sha16 + 2 owner-approved local",
         "count": len(entries), "entries": entries,
         "count_done": sum(1 for e in entries if e["status"] == "done"),
         "count_failed": sum(1 for e in entries if e["status"].startswith("failed")),
         "count_pending": sum(1 for e in entries if e["status"].startswith("pending"))}
    json.dump(q, open(QUEUE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"queue repaired: {len(entries)} canonical entries "
          f"(done={q['count_done']} pending={q['count_pending']})")
    # report statuses of the batch-01 rels
    for rel in ("local/Common-Subjects-2nd-Year-AKTU-08092023.pdf",
                "local/Open-Elective-BTech-2nd-year-2023-08092023.pdf",
                "5-course/2025-26/bca_y1_syllabus_2025-26.pdf",
                "5-course/2025-26/btech_y4s7_open-electives_2025-26.pdf"):
        e = next((x for x in entries if x["rel"] == rel), None)
        print(f"  {rel}: {e['status'] if e else 'MISSING'}")

def session_year(sess):
    m = re.match(r"^(\d{4})-", str(sess))
    return int(m.group(1)) if m else None

if __name__ == "__main__":
    main()
