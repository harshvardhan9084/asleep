#!/usr/bin/env python3
"""build_queue.py — build work/pipeline_v2/queue.json from the repo PDF pool + pinned companions.
Deterministic. Idempotent: existing statuses are preserved on rebuild (only new files added).
"""
import csv, hashlib, json, os, sys

REPO = "/home/z/my-project/work/repo_asleep/PDFs/5-course"
PINNED = [
    ("/home/z/my-project/work/artd_v3/sources/Common-Subjects-2nd-Year-AKTU-08092023.pdf",
     "Common-Subjects-2nd-Year-AKTU-08092023.pdf", "2023-24"),
    ("/home/z/my-project/work/artd_v3/sources/Open-Elective-BTech-2nd-year-2023-08092023.pdf",
     "Open-Elective-BTech-2nd-year-2023-08092023.pdf", "2023-24"),
]
QUEUE = "/home/z/my-project/work/pipeline_v2/queue.json"
FPRINT = "/home/z/my-project/work/pipeline_v2/content_fingerprints.json"


def sha16(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def course_of(name):
    n = name.lower()
    for c in ("btech", "bpharm", "bca", "mca", "mba"):
        if n.startswith(c) or n.startswith(c + "-"):
            base = {"btech": "B.Tech", "bpharm": "B.Pharm", "bca": "BCA", "mca": "MCA", "mba": "MBA"}[c]
            return base
    return "unknown"


def main():
    entries = {}
    if os.path.exists(QUEUE):
        with open(QUEUE, encoding="utf-8") as f:
            for e in json.load(f)["entries"]:
                entries[e["rel"]] = e

    # pinned companions (owner-authorized)
    for path, fname, session in PINNED:
        if not os.path.exists(path):
            print(f"[err] pinned missing: {path}", file=sys.stderr); sys.exit(2)
        rel = f"PINNED/{fname}"
        if rel not in entries:
            entries[rel] = {
                "rel": rel, "path": path, "session": session, "course": "B.Tech",
                "status": "pending-pinned", "sha16": sha16(path),
            }

    n_repo = 0
    for session in sorted(os.listdir(REPO)):
        sdir = os.path.join(REPO, session)
        if not os.path.isdir(sdir):
            continue
        for fname in sorted(os.listdir(sdir)):
            if not fname.lower().endswith(".pdf"):
                continue
            rel = f"5-course/{session}/{fname}"
            if rel in entries:
                continue
            path = os.path.join(sdir, fname)
            entries[rel] = {
                "rel": rel, "path": path, "session": session,
                "course": course_of(fname), "status": "pending", "sha16": sha16(path),
            }
            n_repo += 1

    data = {"entries": list(entries.values())}
    with open(QUEUE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    with open(FPRINT, "w", encoding="utf-8") as f:
        json.dump({e["sha16"]: e["rel"] for e in data["entries"]}, f, indent=1)

    st = {}
    for e in data["entries"]:
        st[e["status"]] = st.get(e["status"], 0) + 1
    print(f"queue entries={len(data['entries'])} new_repo={n_repo} statuses={st}")


if __name__ == "__main__":
    main()
