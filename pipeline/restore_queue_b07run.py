#!/usr/bin/env python3
"""restore_queue_b07run.py — queue reconstruction after the 2026-10-29 20:40
workspace reset (5th reset; local state rolled back to the post-B02 snapshot:
queue held only B01×2 + B02×6 done, repo clone lost, .env without PAT,
RULES §1b/§1c + push_catalog.sh + enqueue_corpus.py missing, worklog ended
at B02, drafts dir held the 6 B02 drafts).

GitHub state at recovery time (HEAD 93feccc) is AHEAD of every local state,
and COMPLETE (unlike the B06 incident):
  B03    CRON-20261028-B03           rows 196→204 (4 BCA rels)
  B04    CRON-20261028-B04           rows 204→402 (8 done + 2 failed regulations-only)
  B04R   CRON-20261028-B04-repair    rows 402→402 (~81 field repairs)
  B05    CRON-20261028-B05           rows 402→526 (10 done)
  B06    CRON-20261029-B06           rows 526→648 CLAIMED — commit 2d7a5ec shipped
         CHANGELOG+manifest only (CSV lost)
  B06R   CRON-20261029-B06-recovery  rows 526→647, codes 850 — re-derived B06's 10
         docs and successfully pushed the full CSV (HEAD 93feccc, md5 b967d47a...)

This script restores the queue to the B06R-published state and lines up the
next hourly batch (B07):

  1. done          — every 5-course corpus rel whose md5-sha16 is cited in the
                     published 647-row CSV (source_syllabus/source_history) —
                     covers the 18:30-run docs + B03 4 + B04 8 + B05 10 + B06 10;
                     never re-process ingested docs.
  2. failed(regulations-only) — the 2 B04 quarantine docs (B04 manifest
                     evidence; zero subject rows, no catalog content).
  3. NO pins       — B06R's CSV is complete on GitHub; nothing to re-derive.
  4. batch_counter = 6 → select_batch picks the next 10 pending as batch07.

Idempotent: entries keyed by rel; statuses only set when different.
"""
import csv, glob, hashlib, json, os, sys
from datetime import datetime, timezone

QUEUE = "/home/z/my-project/work/pipeline_v2/queue.json"
CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
ROOT = "/home/z/my-project/work"
SCAN = os.path.join(ROOT, "repo_asleep/PDFs/5-course")

# B04 manifest: the 2 regulations-only quarantines (failed, zero subjects)
FAILED_REGULATIONS = [
    "bpharm_ordinances_2019-20.pdf",
    "bpharm_regulations-ordinances_2026-27.pdf",
]


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    # sha16s cited by the published CSV (authoritative ingest evidence)
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
    n_done = n_fail = 0
    for pdf in glob.glob(os.path.join(SCAN, "*", "*.pdf")):
        rel = os.path.relpath(pdf, ROOT)
        e = by_rel.get(rel)
        if not e:
            print(f"MISSING_QUEUE_REL|{rel}")
            continue
        sha = md5(pdf)[:16]
        base = os.path.basename(rel)
        if base in FAILED_REGULATIONS:
            if e["status"] != "failed(regulations-only)":
                e["status"] = "failed(regulations-only)"
                e["md5"] = md5(pdf)
                e["sha16"] = sha
                e["notes"] = ("RECONSTRUCTED 2026-10-29 from the published B04 manifest "
                              "(runs/20261028T190528Z_*: regulations-only doc, 0 subjects, "
                              "61/58 non_subject_rows preserved in that session's drafts; "
                              "no catalog content). evidence: syllabus_catalog/runs/.")
                n_fail += 1
        elif sha in cited:
            if e["status"] != "done":
                e["status"] = "done"
                e["md5"] = md5(pdf)
                e["sha16"] = sha
                e["notes"] = ("RECONSTRUCTED 2026-10-29 (5th reset): this doc's sha16 is cited "
                              "in the published GitHub CSV (syllabus_catalog @93feccc, 647 rows, "
                              "B06R state) — ingested by a prior run (B03/B04/B05/B06 per runs/ "
                              "manifests); never re-process.")
                n_done += 1
    q["meta"]["batch_counter"] = 6
    q["meta"].setdefault("history", []).append({
        "ts": now,
        "event": (f"queue reconstructed to B06R-published state after 5th workspace reset: "
                  f"{n_done} corpus rels marked done (sha16 cited in GitHub CSV @93feccc), "
                  f"{n_fail} failed(regulations-only) per B04 manifest; no re-derivation pins "
                  f"(B06R CSV complete); batch_counter=6")})
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    from collections import Counter
    print("statuses:", Counter(e["status"] for e in q["entries"]))
    print(f"DONE|{n_done} FAILED|{n_fail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
