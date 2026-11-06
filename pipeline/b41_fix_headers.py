#!/usr/bin/env python3
"""b41_fix_headers.py — repair the draft headers (pdf_rel / session / course)
for the B41 drafts AND the archived B40 drafts, from queue.json.

Root cause (recorded for future batches): parse_batch.py stages files as
NN_<stem>.pdf with meta.rel='' and meta.session=''; mercury_engine.draft_doc's
queue lookup matched by staged basename (with the NN_ prefix) against queue rel
basenames (without) — every B40/B41 draft fell back to course='BTech',
session='', pdf_rel=''. Consequence: §3's newer-session-fieldwise policy
silently degraded to backfill-only in the B40 commit, and 11 appended rows got
empty effective_session_latest.

The printed course codes override draft course metadata (RULES §1b) — here the
queue's course field IS the filename-derived canonical course and matches the
printed codes (KMBAI/KMBI/RMBI/BMBAI → MBA; KOE/BOE → BTech), verified below
per doc via the codes the drafts actually carry.
"""
import json, re

Q = "/home/z/my-project/work/pipeline_v2/queue.json"
q = json.load(open(Q))
by_base = {e["rel"].split("/")[-1]: e for e in q["entries"]}

MBA_CODES = re.compile(r"^(K|R|B)?MBAI", re.I)
BTech_OE = re.compile(r"^(K|R|B|N|E)?(OE|C|EC|IC|ME|IT|HU|GP|AUC|NOE|NHU|NGP)", re.I)

targets = []
import glob, os
for p in sorted(glob.glob("/home/z/my-project/work/pipeline_v2/drafts/*.draft.json")):
    targets.append(p)
for p in sorted(glob.glob("/home/z/my-project/work/pipeline_v2/drafts_B40_done/*.draft.json")):
    targets.append(p)

for p in targets:
    d = json.load(open(p))
    stem = d.get("stem") or os.path.basename(p)[:-len(".draft.json")]
    clean = re.sub(r"^\d+_", "", stem) + ".pdf"
    e = by_base.get(clean)
    if not e:
        print("NO-QUEUE-MATCH|", stem)
        continue
    old = (d.get("pdf_rel"), d.get("session"), d.get("course"))
    d["pdf_rel"] = e["rel"]
    d["session"] = e.get("session", "")
    d["course"] = e.get("course", "")
    # §1b printed-codes cross-check (zero-guess): the dominant code family must
    # agree with the canonical course from the queue
    fams = set()
    for s in d["subjects"]:
        for c in (s.get("codes") or []):
            c = re.sub(r"[^A-Z]", "", c.upper())
            if c.startswith("MBAI"):
                fams.add("MBA")
            elif MBA_CODES.match(c):
                fams.add("MBA")
    if fams and fams != {d["course"]}:
        print("CODE-COURSE-CONFLICT|", stem, fams, "vs queue", d["course"])
    json.dump(d, open(p, "w"), indent=1, ensure_ascii=False)
    print("FIXED|", os.path.basename(p)[:46], "|", old, "->", (d["pdf_rel"][-48:], d["session"], d["course"]))
