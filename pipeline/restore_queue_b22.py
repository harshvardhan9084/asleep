#!/usr/bin/env python3
"""restore_queue_b22.py — 21st-reset reconstruction (recorded b13..b21 pattern).

GitHub @673fc6c = B21 is the authoritative shipped state (runs/ manifests B20+B21,
CSV 1615 data rows x 57 cols). Rebuild the queue so the next un-run batch is B22:
  - enqueue_corpus.py already appended the 448 5-course corpus PDFs as pending
    (8 legacy done entries preserved);
  - compute md5/sha16 for every entry lacking them (content dedup + citations);
  - sha16 cited in the published CSV (#<sha16> tokens in any cell) -> done
    (never re-process shipped work);
  - the 5 failed rels recorded by the published B04/B08/B15 manifests stay failed
    (2 regulations-only + 3 content-duplicate corroborating copies);
  - everything else stays pending;
  - batch_counter = 21 (B21 shipped) -> select_batch picks batch 22.
Never re-assigns done/failed that the citations justify; append-only history.
"""
import csv, json, os, re, hashlib
from datetime import datetime, timezone

BASE = "/home/z/my-project/work/pipeline_v2"
QUEUE = f"{BASE}/queue.json"
CSV = "/home/z/my-project/work/repo_asleep/syllabus_catalog/syllabus_extreme_rich.csv"
ROOT = "/home/z/my-project"

FAILED_REGULATIONS = [
    "bpharm_ordinances_2019-20.pdf",
    "bpharm_regulations-ordinances_2026-27.pdf",
]
FAILED_CONTENT_DUP = {
    "btech_ag_y4_syllabus_2016-17_2.pdf": "failed(content-equivalent-corroborating-copy)",
    "btech_ai-ml_y3_syllabus_2024-25.pdf": "failed(content-duplicate-corroborating-copy)",
    "btech_ce_y3_syllabus_2024-25.pdf": "failed(content-equivalent-corroborating-copy)",
}


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    q = json.load(open(QUEUE))

    # 1. compute md5/sha16 where missing
    for e in q["entries"]:
        if not e.get("md5") and os.path.isfile(e.get("file", "")):
            m = md5(e["file"])
            e["md5"] = m
            e["sha16"] = m[:16]

    # 2. collect cited sha16 tokens from the published CSV (any cell, #<16hex>)
    cited = set()
    with open(CSV, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            for cell in row:
                for tok in re.findall(r"#([0-9a-f]{16})", cell or ""):
                    cited.add(tok)
    print(f"CITED_SHAS|{len(cited)}")

    # 3. classify non-done entries
    counts = {"done": 0, "failed": 0, "pending": 0, "other": 0}
    for e in q["entries"]:
        st = e["status"]
        if st == "done":
            counts["done"] += 1
            continue
        base = os.path.basename(e["rel"])
        if e.get("sha16") in cited:
            e["status"] = "done"
            e.setdefault("notes", "")
            if "cited-in-published-csv" not in e["notes"]:
                e["notes"] = (e["notes"] + " | cited-in-published-csv (restore b22)").strip(" |")
            counts["done"] += 1
        elif base in FAILED_REGULATIONS:
            e["status"] = "failed(regulations-only-non-syllabus)"
            counts["failed"] += 1
        elif base in FAILED_CONTENT_DUP:
            e["status"] = FAILED_CONTENT_DUP[base]
            counts["failed"] += 1
        elif str(st).startswith("failed"):
            e["status"] = st
            counts["failed"] += 1
        else:
            e["status"] = "pending"
            counts["pending"] += 1
    print("COUNTS|" + json.dumps(counts))

    # 4. batch_counter = 21 (B21 shipped) -> next batch B22
    q["meta"]["batch_counter"] = 21
    q["meta"].setdefault("history", []).append({
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": ("restore_queue_b22: 21st-reset reconstruction to GitHub B21 state "
                  f"@673fc6c; cited->done {counts['done']}, failed {counts['failed']}, "
                  f"pending {counts['pending']}; batch_counter=21")})
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    print("RESTORED|batch_counter=21")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
