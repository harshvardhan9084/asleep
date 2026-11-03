#!/usr/bin/env python3
"""restore_queue_b16.py — queue reconstruction after the 14th workspace reset
(2026-10-31 ~20:00 local state rolled back to the post-B02 snapshot AGAIN:
8 done entries, no B03+ knowledge locally, no repo_asleep, no GITHUB_PAT in
.env — same class of reset as restore_queue_b13/b15.py documented).

GitHub state at recovery time (HEAD e306256 = B15, pushed 2026-10-31 11:32 UTC)
is AHEAD of every local state: B03..B15 completed in prior sessions
(runs/ manifests B03..B15; latest B15 = rows 1304→1385, codes 1690→1859).

The resending cron task still labels itself CRON-20261031-B04, but B04 was
completed and pushed long ago (commits 2daa401/189ba64 + repair 43cea6a) and
the chain has since shipped B05..B15. Per the no-repeat hard rule and RULES
§1c (GitHub is the durable record), this run continues the corpus at the next
un-run batch: B16.

Reconstruction (evidence: syllabus_catalog/runs/ manifests, CHANGELOG.md,
sha16 citations inside the published 1385-row CSV itself):
  1. done — every 5-course corpus rel whose md5-sha16 is cited in the
     published CSV (source_syllabus/source_history) — never re-process.
  2. failed(regulations-only) — the 2 B04 quarantine docs (B04 manifest).
  3. failed(content-*) — the 2 B08 corroborating-copy docs + the B15
     corroborating-copy skip (btech_ce_y3_syllabus_2024-25.pdf, sha16
     03d279e76a24f6ff, B15 manifest: byte-identical to the B04-ingested
     B.Tech. 3rd Year Civil Engineering.pdf 79a6daf1f0cd9310) — never
     re-process.
  4. everything else stays pending; future batches.
  5. batch_counter = 15 → select_batch picks the next 10 as batch16 (B16).

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
# B15 manifest evidence (runs/20261031T113242Z_*): staged doc 01 skip class.
FAILED_CONTENT_DUP = {
    "btech_ag_y4_syllabus_2016-17_2.pdf":
        "failed(content-equivalent-corroborating-copy)",
    "btech_ai-ml_y3_syllabus_2024-25.pdf":
        "failed(content-duplicate-corroborating-copy)",
    "btech_ce_y3_syllabus_2024-25.pdf":
        "failed(content-equivalent-corroborating-copy)",
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
            e["notes"] = ("RECONSTRUCTED 2026-10-31 (14th reset) from the published B04 "
                          "manifest (runs/20261028T190528Z_*): regulations-only doc, 0 "
                          "subjects, non_subject_rows preserved in that session's drafts; "
                          "no catalog content. evidence: syllabus_catalog/runs/.")
            n_fail += 1
        elif base in FAILED_CONTENT_DUP:
            e["status"] = FAILED_CONTENT_DUP[base]
            e["md5"] = md5(pdf)
            e["sha16"] = sha
            e["notes"] = ("RECONSTRUCTED 2026-10-31 (14th reset) from the published B08/B15 "
                          "manifests (runs/20261030T142740Z_*, runs/20261031T113242Z_*): "
                          "corroborating copy already ingested under another sha16 "
                          "(content-duplicate/equivalent adjudication with recorded "
                          "evidence); never re-process.")
            n_fail += 1
        elif sha in cited:
            e["status"] = "done"
            e["md5"] = md5(pdf)
            e["sha16"] = sha
            e["notes"] = ("RECONSTRUCTED 2026-10-31 (14th reset): this doc's sha16 is cited "
                          "in the published GitHub CSV (syllabus_catalog @ e306256, 1385 "
                          "rows) — ingested by a prior run (B01-B15 per runs/ manifests); "
                          "never re-process.")
            n_done += 1
        else:
            n_still += 1
    q["meta"]["batch_counter"] = 15
    q["meta"].setdefault("history", []).append({
        "ts": now,
        "event": (f"queue reconstructed to B15-published state after 14th workspace reset: "
                  f"{n_done} rels newly marked done (sha16 cited in GitHub CSV @e306256, "
                  f"1385 rows), {n_fail} failed per B04/B08/B15 manifests, "
                  f"{n_still} still pending; batch_counter=15 → next batch B16 "
                  f"(run continues the CRON-20261031-B04 resend chain; B04 itself was "
                  f"completed+pushed as commits 2daa401/189ba64/43cea6a and B05..B15 "
                  f"have since shipped — no repeat)")})
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    from collections import Counter
    print("statuses:", Counter(e["status"] for e in q["entries"]))
    print(f"NEW_DONE|{n_done} FAILED|{n_fail} STILL_PENDING|{n_still}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
