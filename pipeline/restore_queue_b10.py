#!/usr/bin/env python3
"""restore_queue_b10.py — queue reconstruction after the 8th workspace reset
(2026-10-31 ~02:00 local state rolled back to the post-B02 snapshot AGAIN:
8 done entries, no B03+ knowledge locally, no repo_asleep, no PAT in .env).

GitHub state at recovery time (HEAD 8c4faf1 = B09) is AHEAD of every local
state:
  B03    CRON-20261028-B03           rows 196→204 (4 BCA rels)
  B04    CRON-20261028-B04           rows 204→402 (8 done + 2 failed regs)
  B04R   CRON-20261028-B04-repair    rows 402→402 (~81 field repairs)
  B05    CRON-20261028-B05           rows 402→526 (10 done)
  B06/B06R CRON-20261029-B06(-recovery) rows 526→647 (10 docs re-ingested)
  B07    CRON-20261030-B07           rows 647→744 (10 docs, BTech AG wave)
  B08    CRON-20261030-B08           rows 744→777 (8 done + 2 failed content-*)
  B09    CRON-20261031-B09           rows 777→875 (9 docs; B08 BCA-project §1b repair)

Reconstruction (evidence: syllabus_catalog/runs/ manifests, CHANGELOG.md,
sha16 citations inside the published 875-row CSV itself):
  1. done — every 5-course corpus rel whose md5-sha16 is cited in the
     published CSV (source_syllabus/source_history) — never re-process.
  2. failed(regulations-only) — the 2 B04 quarantine docs (B04 manifest).
  3. failed(content-*) — the 2 B08 corroborating-copy docs (B08 manifest).
  4. everything else stays pending; future batches.
  5. batch_counter = 9 → select_batch picks the next 10 as batch10 (B10).

Idempotent: statuses only set when different.
"""
import csv, glob, hashlib, json, os, sys
from datetime import datetime, timezone

QUEUE = "/home/z/my-project/work/pipeline_v2/queue.json"
CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
ROOT = "/home/z/my-project/work"
SCAN = os.path.join(ROOT, "repo_asleep/PDFs/5-course")

FAILED_REGULATIONS = [
    "bpharm_ordinances_2019-20.pdf",
    "bpharm_regulations-ordinances_2026-27.pdf",
]

# B08 manifest evidence (runs/20261030T142740Z_*): corroborating copies whose
# content was already ingested under another sha16 — never re-process.
FAILED_CONTENT_DUP = {
    "btech_ag_y4_syllabus_2016-17_2.pdf":
        "failed(content-equivalent-corroborating-copy)",
    "btech_ai-ml_y3_syllabus_2024-25.pdf":
        "failed(content-duplicate-corroborating-copy)",
}


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    cited = set()
    for r in csv.DictReader(open(CSV)):
        for col in ("source_syllabus", "source_history"):
            for tok in (r.get(col, "") or "").split("#")[1:]:
                tok = tok.strip()
                if len(tok) >= 16 and all(c in "0123456789abcdef" for c in tok[:16]):
                    cited.add(tok[:16])
    print(f"CSV cites {len(cited)} distinct sha16(s)")

    q = json.load(open(QUEUE))
    by_rel = {e["rel"]: e for e in q["entries"]}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    n_done = n_fail = n_still = 0
    for pdf in glob.glob(os.path.join(SCAN, "*", "*.pdf")):
        rel = os.path.relpath(pdf, ROOT)
        e = by_rel.get(rel)
        if not e:
            print(f"MISSING_QUEUE_REL|{rel}")
            continue
        if str(e["status"]).startswith("done") or str(e["status"]).startswith("failed"):
            continue
        sha = md5(pdf)[:16]
        base = os.path.basename(rel)
        if base in FAILED_REGULATIONS:
            e["status"] = "failed(regulations-only)"
            e["md5"] = md5(pdf)
            e["sha16"] = sha
            e["notes"] = ("RECONSTRUCTED 2026-10-31 (8th reset) from the published B04 "
                          "manifest (runs/20261028T190528Z_*): regulations-only doc, 0 "
                          "subjects, non_subject_rows preserved in that session's drafts; "
                          "no catalog content. evidence: syllabus_catalog/runs/.")
            n_fail += 1
        elif base in FAILED_CONTENT_DUP:
            e["status"] = FAILED_CONTENT_DUP[base]
            e["md5"] = md5(pdf)
            e["sha16"] = sha
            e["notes"] = ("RECONSTRUCTED 2026-10-31 (8th reset) from the published B08 "
                          "manifest (runs/20261030T142740Z_*): corroborating copy already "
                          "ingested under another sha16 (content-duplicate/equivalent "
                          "adjudication with recorded evidence); never re-process.")
            n_fail += 1
        elif sha in cited:
            e["status"] = "done"
            e["md5"] = md5(pdf)
            e["sha16"] = sha
            e["notes"] = ("RECONSTRUCTED 2026-10-31 (8th reset): this doc's sha16 is cited "
                          "in the published GitHub CSV (syllabus_catalog @ 8c4faf1, 875 "
                          "rows) — ingested by a prior run (B01-B09 per runs/ manifests); "
                          "never re-process.")
            n_done += 1
        else:
            n_still += 1
    q["meta"]["batch_counter"] = 9
    q["meta"].setdefault("history", []).append({
        "ts": now,
        "event": (f"queue reconstructed to B09-published state after 8th workspace reset: "
                  f"{n_done} rels newly marked done (sha16 cited in GitHub CSV @8c4faf1, "
                  f"875 rows), {n_fail} failed per B04/B08 manifests, "
                  f"{n_still} still pending; batch_counter=9 → next batch B10")})
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    from collections import Counter
    print("statuses:", Counter(e["status"] for e in q["entries"]))
    print(f"NEW_DONE|{n_done} FAILED|{n_fail} STILL_PENDING|{n_still}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
