#!/usr/bin/env python3
"""adopt_b37.py — (1) repair the 5 durable B37 drafts' empty pdf_rel/session/
course from the restored queue (sha16-matched; recorded in-flight-batch class),
(2) assemble the clean merge dir work/pipeline_v2/drafts_B37/ with exactly the
10 batch drafts, (3) stage batch37 copies with the B37 stems."""
import json, os, shutil

BASE = "/home/z/my-project/work/pipeline_v2"
QUEUE = f"{BASE}/queue.json"
DURABLE = "/home/z/my-project/work/repo_asleep/pipeline/drafts_B37"
OUT = f"{BASE}/drafts_B37"
STAGING = f"{BASE}/staging/batch37"
SCAN = "/home/z/my-project/work/repo_asleep/PDFs/5-course"

q = json.load(open(QUEUE))
by_sha = {e["sha16"]: e for e in q["entries"] if e.get("sha16")}
os.makedirs(OUT, exist_ok=True)
os.makedirs(STAGING, exist_ok=True)

# 1+2: adopt durable drafts (repaired) into the clean merge dir
adopted = []
for fn in sorted(os.listdir(DURABLE)):
    if not fn.endswith(".draft.json"):
        continue
    d = json.load(open(os.path.join(DURABLE, fn)))
    e = by_sha.get(d.get("sha16", ""))
    if e is None:
        print(f"ABORT|no queue entry for {fn} sha16={d.get('sha16','')}")
        raise SystemExit(2)
    changed = []
    if d.get("pdf_rel") != e["rel"]:
        d["pdf_rel"] = e["rel"]; changed.append("pdf_rel")
    if d.get("session") != e.get("session", ""):
        d["session"] = e.get("session", ""); changed.append("session")
    if d.get("course") != e.get("course", "BTech"):
        d["course"] = e.get("course", "BTech"); changed.append("course")
    d.setdefault("quirks", []).append(
        "durable in-flight draft (parallel instance @0a3b85b) adopted by CRON-20261106-B37; "
        "pdf_rel/session/course repaired from restored queue (sha16 match)")
    out = os.path.join(OUT, fn)
    json.dump(d, open(out, "w"), indent=1, ensure_ascii=False)
    adopted.append((fn, e["rel"], len(d.get("subjects", [])), changed))
    print(f"ADOPT|{fn}|subjects={len(d.get('subjects', []))}|repaired={changed}")

# 3: stage all 10 batch docs with their B37 stems
staged = 0
for e in q["entries"]:
    if e.get("batch") != 37:
        continue
    stem = e["staged_stem"]
    dst = os.path.join(STAGING, stem + ".pdf")
    shutil.copyfile(e["file"], dst)
    staged += 1
    print(f"STAGE|{stem}|{e['rel']}")
print(f"ADOPTED|{len(adopted)} STAGED|{staged}")
