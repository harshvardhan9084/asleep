#!/usr/bin/env python3
"""b39_fix_parsed_meta.py — enrich the 10 B39 parsed records with the meta
fields the mercury engine / resume script expect (file = queue-rel basename,
session = queue session). The flat parse records carry rel/session/sha16 at
top level; rec.get('meta', rec) fallback works but file/session were empty."""
import json, os

PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
QUEUE = "/home/z/my-project/work/pipeline_v2/queue.json"
q = json.load(open(QUEUE))
by_stem = {}
for e in q["entries"]:
    if e.get("status") == "selected" and e.get("staged_stem"):
        by_stem[e["staged_stem"]] = e

for stem, e in sorted(by_stem.items()):
    p = f"{PARSED}/{stem}.json"
    rec = json.load(open(p))
    rec["file"] = os.path.basename(e["rel"])
    if not rec.get("session"):
        rec["session"] = e.get("session", "")
    json.dump(rec, open(p, "w"), indent=1, ensure_ascii=False)
    print(stem, "->", rec["file"], "| session:", rec["session"], "| sha16:", rec["sha16"])
print("FIXED", len(by_stem))
