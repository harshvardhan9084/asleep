#!/usr/bin/env python3
"""w10c_b74_reaudit.py — B76 integrity check: re-verify the 31 B74-written
subject_type values under the tightened governing-header grammar (gap<=8
lines + wrap-continuation rejection), discovered via wrap-masquerade false
positives in textile-era docs. For each corrected_W10C_CATEGORY row: re-open
the corrections_json evidence page, locate the primary_code hit, apply the
tight rules, report PASS/FAIL with printed context."""
import json
import re
import sys

import fitz

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC
from w10c2_fulldoc_probe import (corpus_map_load, governing_header_tight,
                                 code_variants)

rows = WC.load_rows()
by_id = {r["subject_id"]: r for r in rows}
corpus = corpus_map_load()

targets = [r for r in rows
           if "corrected_W10C_CATEGORY" in (r.get("quality_flags") or "")]
print(f"B74_REAUDIT|targets={len(targets)}")

fails, passes = [], []
for r in targets:
    sid = r["subject_id"]
    pc = (r.get("primary_code") or "").strip().upper()
    ev = ""
    try:
        cjson = json.loads(r.get("corrections_json") or "[]")
        for e in cjson:
            if e.get("rule") == "TYPE_EMPTY" and e.get("evidence"):
                ev = e["evidence"]
    except Exception:
        pass
    m = re.search(r"(\S+)#([0-9a-f]{12,16})\s*p\.(\d+)", ev)
    if not m or not pc:
        fails.append((sid, "no evidence cite / no code", ev[:60]))
        continue
    base, sha, pno = m.group(1), m.group(2), int(m.group(3))
    path = corpus.get(sha) or next((corpus[k] for k in corpus
                                    if k.startswith(sha)), None)
    if not path:
        fails.append((sid, "sha unresolved", sha))
        continue
    d = fitz.open(path)
    t = d[pno - 1].get_text() or ""
    d.close()
    variants = code_variants(pc)
    pat = re.compile(r"\b(" + "|".join(re.escape(v) for v in variants) + r")\b", re.I)
    hit = pat.search(t)
    if not hit:
        fails.append((sid, "code not on cited page", f"{base} p.{pno}"))
        continue
    cat, why = governing_header_tight(t, hit.start())
    cur = (r.get("subject_type") or "").strip()
    if cat and cat == cur and not why:
        passes.append(sid)
    else:
        fails.append((sid, f"stored={cur} tight-probe={cat} why={why}",
                      f"{base} p.{pno}"))

print(f"B74_REAUDIT|pass={len(passes)} fail={len(fails)}")
for sid, why, ev in fails:
    print(f"  FAIL {sid}: {why} [{ev}]")
