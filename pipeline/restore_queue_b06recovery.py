#!/usr/bin/env python3
"""restore_queue_b06recovery.py — queue reconstruction after the 2026-10-29
13:48 workspace reset (4th reset; local state rolled back to the post-B02
snapshot: queue held only B01×2 + B02×6 done, repo clone lost, .env without
PAT, RULES §1b/§1c + push_catalog.sh + enqueue_corpus.py missing).

GitHub state at recovery time (HEAD 2d7a5ec) is AHEAD of every local state:
  B03   CRON-20261028-B03          rows 196→204 (4 BCA rels)
  B04   CRON-20261028-B04          rows 204→402 (8 done + 2 failed regulations-only)
  B04R  CRON-20261028-B04-repair   rows 402→402 (~81 field repairs)
  B05   CRON-20261028-B05          rows 402→526 (10 done)
  B06   CRON-20261029-B06          rows 526→648 CLAIMED — but commit 2d7a5ec
        shipped ONLY CHANGELOG.md + runs/ manifest (git show --stat: 2 files);
        the updated syllabus_extreme_rich.csv NEVER landed. B06's catalog
        deltas (+122 appends / ~57 updates / 74-row baseline G2/G3 repair)
        are LOST with that session's workspace.

This script restores the queue to the B05-published state and sets up the
B06 CSV-recovery re-run (evidence: syllabus_catalog/runs/
20261029T012603Z_CRON-20261029-B06_*.md, CHANGELOG.md, and the sha16
citations inside the published 526-row CSV itself):

  1. done          — every 5-course corpus rel whose md5-sha16 is cited in the
                     published CSV (source_syllabus/source_history) — never
                     re-process ingested docs (B03 4 + B04 7 + B05 10 + …)
  2. failed(regulations-only) — the 2 B04 quarantine docs (B04 manifest
                     evidence; zero subject rows, non_subject_rows preserved
                     in that session's drafts — lost with the reset, but the
                     docs carry no catalog content; re-draft would re-derive
                     nothing)
  3. pending-pinned — B06's 10 rels (RE-DRAFT for CSV recovery: their catalog
                     rows never reached GitHub; re-draft + re-merge re-derives
                     them deterministically from the same PDFs)
  4. batch_counter = 5 → select_batch picks the 10 pinned as batch06.

Idempotent: entries keyed by rel; statuses only set when different.
"""
import csv, glob, hashlib, json, os, sys
from datetime import datetime, timezone

QUEUE = "/home/z/my-project/work/pipeline_v2/queue.json"
CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
ROOT = "/home/z/my-project/work"
SCAN = os.path.join(ROOT, "repo_asleep/PDFs/5-course")
MANIFEST_DIR = os.path.join(ROOT, "repo_asleep/syllabus_catalog/runs")

# B06 recovery batch (stems from the B06 manifest batch table; resolved to
# exact corpus rels below by filename match)
B06_STEMS = [
    "btech_ae_y4_syllabus-cbcs_2019-20",
    "btech_ae_y4_syllabus_2021-22",
    "btech_ae_y4_syllabus_2025-26",
    "btech_ag_course-structure_2026-27",
    "btech_ag_evaluation-scheme_2008-09",
    "btech_ag_syllabus-aicte_2018-19",
    "btech_ag_syllabus_2011-12",
    "btech_ag_syllabus_2013-14",
    "btech_ag_syllabus_2016-17",
    "btech_ag_y1_model-curriculum_2020-21",
]

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
    n_done = n_pin = n_fail = 0
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
                e["notes"] = ("RECONSTRUCTED 2026-10-29: this doc's sha16 is cited in the "
                              "published GitHub CSV (syllabus_catalog @ 2d7a5ec) — ingested "
                              "by a prior run (B03/B04/B05 per runs/ manifests); never re-process.")
                n_done += 1
        # B06 recovery pins (checked after done-guard: B06 docs are NOT in the CSV)
        stem = base[:-4] if base.lower().endswith(".pdf") else base
        if stem in B06_STEMS and e["status"] not in ("done",) and not str(e["status"]).startswith("failed"):
            if e["status"] != "pending-pinned":
                e["status"] = "pending-pinned"
                e["notes"] = ("RECOVERY RE-DRAFT (CRON-20261029-B06-recovery): B06 commit 2d7a5ec "
                              "shipped CHANGELOG+manifest only — the updated CSV never landed "
                              "(git show 2d7a5ec --stat: 2 files). B06's +122 appends/~57 updates "
                              "+ 74-row baseline repair are lost with that session's workspace. "
                              "Re-draft + re-merge from this same PDF re-derives the rows "
                              "(evidence: runs/20261029T012603Z_* manifest).")
                n_pin += 1
    q["meta"]["batch_counter"] = 5
    q["meta"].setdefault("history", []).append({
        "ts": now,
        "event": (f"queue reconstructed to B05-published state after 4th workspace reset: "
                  f"{n_done} rels marked done (sha16 cited in GitHub CSV @2d7a5ec), "
                  f"{n_fail} failed(regulations-only) per B04 manifest, "
                  f"{n_pin} pending-pinned for the B06 CSV-recovery re-run; batch_counter=5")})
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    from collections import Counter
    print("statuses:", Counter(e["status"] for e in q["entries"]))
    print(f"DONE|{n_done} PINNED|{n_pin} FAILED|{n_fail}")
    pinned = sorted(e["rel"] for e in q["entries"] if e["status"] == "pending-pinned")
    for p in pinned:
        print("PINNED|" + p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
