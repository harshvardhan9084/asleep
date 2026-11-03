#!/usr/bin/env python3
"""restore_queue_b25.py — rebuild queue state after a workspace reset (28th).

GitHub (=B24, CSV 1787 data rows) is the authoritative baseline.
Citations: every `#<sha16>` token in ANY column of the repo CSV marks the
corpus PDF with that sha16 as done (never re-process ingested docs — RULES §9).
Failed classes carried from the recorded B19/B23 manifests (5 docs).
Legacy 8 done entries (2 companions + 6 B02 uploads) preserved from the
surviving stale queue. batch_counter := 24 so select_batch yields B25.
"""
import csv, hashlib, json, os, re, sys
from datetime import datetime, timezone

QUEUE = "/home/z/my-project/work/pipeline_v2/queue.json"
REPO_CSV = "/home/z/my-project/work/repo_asleep/syllabus_catalog/syllabus_extreme_rich.csv"
CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
ROOT = "/home/z/my-project/work"

FAILED_REGULATIONS = {
    "bpharm_ordinances_2019-20.pdf": "failed(regulations-not-syllabus)",
    "bpharm_regulations-ordinances_2026-27.pdf": "failed(regulations-not-syllabus)",
}
FAILED_CONTENT_DUP = {
    "btech_ag_y4_syllabus_2016-17_2.pdf": "failed(content-equivalent-corroborating-copy)",
    "btech_ai-ml_y3_syllabus_2024-25.pdf": "failed(content-duplicate-corroborating-copy)",
    "btech_ce_y3_syllabus_2024-25.pdf": "failed(content-equivalent-corroborating-copy)",
}


def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if md5_file(CSV) != md5_file(REPO_CSV):
        print("ABORT: local baseline CSV md5 != repo CSV md5")
        return 2
    cited = set()
    with open(REPO_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for cell in row.values():
                if cell and "#" in cell:
                    for m in re.findall(r"#([0-9a-f]{16})", cell):
                        cited.add(m)
    print(f"cited sha16s: {len(cited)}")

    q = json.load(open(QUEUE))
    legacy_done = sum(1 for e in q["entries"] if e["status"] == "done")
    done = failed = 0
    for e in q["entries"]:
        if e["status"] == "done":
            continue  # legacy 8 stay done
        base = os.path.basename(e["rel"])
        cls = FAILED_REGULATIONS.get(base) or FAILED_CONTENT_DUP.get(base)
        if cls:
            e["status"] = cls
            e["notes"] = (e.get("notes", "") + " | reset-restore: recorded failed class "
                          "(B19/B23 manifests; not re-processed per RULES §9)").strip(" |")
            failed += 1
            continue
        path = os.path.join(ROOT, e["rel"])
        if not os.path.isfile(path):
            e["notes"] = (e.get("notes", "") + " | SKIP_MISSING at restore").strip(" |")
            continue
        if not e.get("md5"):
            e["md5"] = md5_file(path)
        e["sha16"] = e["md5"][:16]
        if e["sha16"] in cited:
            e["status"] = "done"
            e["notes"] = (e.get("notes", "") +
                          " | done: sha16 cited in GitHub B24 CSV (reset-restore)").strip(" |")
            done += 1
    q["meta"]["batch_counter"] = 24
    q["meta"]["history"].append({
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": ("workspace reset recovery to GitHub (=B24): "
                  f"legacy {legacy_done} done preserved; {done} corpus docs marked done by "
                  f"CSV citation ({len(cited)} cited sha16s); {failed} failed-class docs; "
                  "batch_counter=24; next select yields B25")})
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    from collections import Counter
    c = Counter(e["status"] for e in q["entries"])
    print("STATUS|", dict(c))
    print(f"TOTAL|{len(q['entries'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
