#!/usr/bin/env python3
"""select_batch.py — deterministically pick the next <=10 pending PDFs.

Order: pending-pinned first (filename ASC), then pending (session DESC,
no-session last, filename ASC). md5 content-dedup vs done/failed and within
the batch. Missing files skipped with SKIP_MISSING (status untouched).
Creates staging/batch<NN>/ with NN_<safe-stem>.pdf symlinks and prints:
  LN|<symlink>|<target>|<queue-rel>
  STEMS|<stem1>,<stem2>,...
  SKIP_DUPES|<rel>,...
  SKIP_MISSING|<rel>,...
  BATCH|<NN>   SELECTED|<n>   (exit 0)
Prints NO_PENDING and exits 0 when nothing qualifies.
"""
import json, os, sys, hashlib

BASE = "/home/z/my-project/work/pipeline_v2"
QUEUE = f"{BASE}/queue.json"
STAGING = f"{BASE}/staging"
MAX_BATCH = 10


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_stem(rel, n):
    base = os.path.basename(rel)[:-4] if rel.lower().endswith(".pdf") else os.path.basename(rel)
    stem = "".join(c if (c.isalnum() or c in "._-") else "_" for c in base)[:80]
    return f"{n:02d}_{stem}"


def main():
    q = json.load(open(QUEUE))
    entries = q["entries"]
    done_md5 = {e["md5"] for e in entries if e["status"] == "done" and e.get("md5")}
    failed_md5 = {e["md5"] for e in entries if str(e["status"]).startswith("failed") and e.get("md5")}

    pinned = [e for e in entries if e["status"] == "pending-pinned"]
    pend = [e for e in entries if e["status"] == "pending"]
    pend.sort(key=lambda e: (0 if e.get("session") else 1, e.get("session") or "", os.path.basename(e["rel"])), reverse=False)
    # session DESC: sort by session string descending, no-session last, then filename ASC
    pend.sort(key=lambda e: (e.get("session") or ""), reverse=True)
    pend.sort(key=lambda e: (0 if e.get("session") else 1, os.path.basename(e["rel"])))

    candidates = pinned + pend
    if not candidates:
        print("NO_PENDING")
        return 0

    batch_n = int(q.get("meta", {}).get("batch_counter", 0)) + 1
    bdir = f"{STAGING}/batch{batch_n:02d}"
    os.makedirs(bdir, exist_ok=True)

    chosen, skip_dupes, skip_missing = [], [], []
    for e in candidates:
        if len(chosen) >= MAX_BATCH:
            break
        if not os.path.isfile(e["file"]):
            skip_missing.append(e["rel"])
            print(f"SKIP_MISSING|{e['rel']}")
            continue
        m = md5(e["file"])
        if m in done_md5 or m in failed_md5 or m in {c["md5"] for c in chosen}:
            skip_dupes.append(e["rel"])
            print(f"SKIP_DUPES|{e['rel']}")
            continue
        e["md5"] = m
        e["sha16"] = m[:16]
        chosen.append(e)

    if not chosen:
        print("NO_PENDING")
        return 0

    stems = []
    for i, e in enumerate(chosen, 1):
        stem = safe_stem(e["rel"], i)
        link = os.path.join(bdir, stem + ".pdf")
        if os.path.lexists(link):
            os.remove(link)
        os.symlink(e["file"], link)
        e["status"] = "selected"
        e["batch"] = batch_n
        e["attempts"] = int(e.get("attempts", 0)) + 1
        e["staged_stem"] = stem
        stems.append(stem)
        print(f"LN|{link}|{e['file']}|{e['rel']}")

    print(f"STEMS|{','.join(stems)}")
    if skip_dupes:
        print("SKIP_DUPES|" + ",".join(skip_dupes))
    if skip_missing:
        print("SKIP_MISSING|" + ",".join(skip_missing))

    q.setdefault("meta", {})["batch_counter"] = batch_n
    q["meta"].setdefault("history", []).append(
        {"ts": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
         "event": f"batch{batch_n:02d} selected {len(chosen)} pdf(s)"})
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    print(f"BATCH|{batch_n:02d}")
    print(f"SELECTED|{len(chosen)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
