#!/usr/bin/env python3
"""restore_queue_b20.py — queue reconstruction after the 19th workspace reset
(2026-11-01 ~14:00 +08:00 trigger: state rolled back to the post-B02 snapshot
AGAIN — mid-session reset this time: the 18th-reset restore had completed this
same day (env+clone+CSV+toolchain+queue to 279 pending, batch20 selected,
5/10 drafts done) and was fully wiped. Same reset class as
restore_queue_b13/b15/b16/b17/b18/b19.py).

GitHub state at recovery time (HEAD 0265a95 = B19, pushed 2026-11-01 01:36 UTC,
rows 1500→1550, codes 2720→2970 per B18→B19 delta) is AHEAD of every local
state: B03..B19 completed and pushed in prior sessions (runs/ manifests).

The resending cron task still carries the B<NN> template (summaries mislabel
it "B04"); B04 shipped long ago (commits 2daa401/189ba64/43cea6a) and the
chain has since shipped B05..B19. Per the no-repeat hard rule and RULES §1c
(GitHub is the durable record), this run continues the corpus at the next
un-run batch: B20.

Reconstruction (evidence: syllabus_catalog/runs/ manifests, CHANGELOG.md,
sha16 citations inside the published 1551-row CSV itself):
  1. done — every 5-course corpus rel whose md5-sha16 is cited in the
     published CSV (source_syllabus/source_history) — never re-process.
  2. failed(regulations-only) — the 2 B04 quarantine docs (B04 manifest).
  3. failed(content-*) — the 3 corroborating-copy docs (B08 + B15 manifests)
     — never re-process.
  4. everything else stays pending; future batches.
  5. batch_counter = 19 → select_batch picks the next 10 as batch20 (B20).

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
    n_rows = 0
    for r in csv.DictReader(open(CSV)):
        n_rows += 1
        for col in ("source_syllabus", "source_history"):
            for tok in (r.get(col, "") or "").split("#")[1:]:
                tok = tok.strip()
                if len(tok) >= 16 and all(c in "0123456789abcdef" for c in tok[:16]):
                    cited.add(tok[:16])
    print(f"CSV cites {len(cited)} distinct sha16(s) across {n_rows} data rows")

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
            e["notes"] = ("RECONSTRUCTED 2026-11-01 (19th reset) from the published B04 "
                          "manifest (runs/20261028T190528Z_*): regulations-only doc, 0 "
                          "subjects, non_subject_rows preserved in that session's drafts; "
                          "no catalog content. evidence: syllabus_catalog/runs/.")
            n_fail += 1
        elif base in FAILED_CONTENT_DUP:
            e["status"] = FAILED_CONTENT_DUP[base]
            e["md5"] = md5(pdf)
            e["sha16"] = sha
            e["notes"] = ("RECONSTRUCTED 2026-11-01 (19th reset) from the published B08/B15 "
                          "manifests (runs/20261030T142740Z_*, runs/20261031T113242Z_*): "
                          "corroborating copy already ingested under another sha16 "
                          "(content-duplicate/equivalent adjudication with recorded "
                          "evidence); never re-process.")
            n_fail += 1
        elif sha in cited:
            e["status"] = "done"
            e["md5"] = md5(pdf)
            e["sha16"] = sha
            e["notes"] = ("RECONSTRUCTED 2026-11-01 (19th reset): this doc's sha16 is cited "
                          "in the published GitHub CSV (syllabus_catalog @0265a95 = B19, "
                          "1550 data rows) — ingested by a prior run (B01-B19 per runs/ "
                          "manifests); never re-process.")
            n_done += 1
        else:
            n_still += 1
    q["meta"]["batch_counter"] = 19
    q["meta"].setdefault("history", []).append({
        "ts": now,
        "event": (f"queue reconstructed to B19-published state after 19th workspace reset "
                  f"(mid-session reset wiped the 18th-reset restore of this same day): "
                  f"{n_done} rels newly marked done (sha16 cited in GitHub CSV @0265a95), "
                  f"{n_fail} failed per B04/B08/B15 manifests, {n_still} still pending; "
                  f"batch_counter=19 → next batch B20 (run continues the CRON resend "
                  f"chain; B04 itself was completed+pushed as commits "
                  f"2daa401/189ba64/43cea6a and B05..B19 have since shipped — no repeat)")})
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    from collections import Counter
    print("statuses:", Counter(e["status"] for e in q["entries"]))
    print(f"NEW_DONE|{n_done} FAILED|{n_fail} STILL_PENDING|{n_still}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
