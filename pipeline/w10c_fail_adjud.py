#!/usr/bin/env python3
"""w10c_fail_adjud.py — page-level adjudication of the 24 B74 re-audit fails.
For each: print the governing-header candidate line, the code hit line, and
the lines between them (compressed) so each verdict can be adjudicated as
TRUE_HEADER_LONG_TABLE (header genuinely governs; keep write) vs
WRAP_OR_UNRELATED (false positive; revert)."""
import json
import re
import sys

import fitz

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC
from w10c2_fulldoc_probe import (corpus_map_load, governing_header_tight,
                                 code_variants, HEADERS, HONOR_RE)

rows = WC.load_rows()
by_id = {r["subject_id"]: r for r in rows}
corpus = corpus_map_load()

# rebuild the fail list fresh (same logic as reaudit)
fails = []
for r in rows:
    if "corrected_W10C_CATEGORY" not in (r.get("quality_flags") or ""):
        continue
    sid = r["subject_id"]
    pc = (r.get("primary_code") or "").strip().upper()
    ev = ""
    try:
        for e in json.loads(r.get("corrections_json") or "[]"):
            if e.get("rule") == "TYPE_EMPTY" and e.get("evidence"):
                ev = e["evidence"]
    except Exception:
        pass
    m = re.search(r"(\S+)#([0-9a-f]{12,16})\s*p\.(\d+)", ev)
    if not m or not pc:
        continue
    base, sha, pno = m.group(1), m.group(2), int(m.group(3))
    path = corpus.get(sha) or next((corpus[k] for k in corpus if k.startswith(sha)), None)
    if not path:
        continue
    d = fitz.open(path)
    t = d[pno - 1].get_text() or ""
    d.close()
    variants = code_variants(pc)
    pat = re.compile(r"\b(" + "|".join(re.escape(v) for v in variants) + r")\b", re.I)
    hit = pat.search(t)
    if not hit:
        continue
    cat, why = governing_header_tight(t, hit.start())
    cur = (r.get("subject_type") or "").strip()
    if not (cat and cat == cur and not why):
        # locate the loose-header candidate (any HEADERS match above code)
        lines = t[:hit.start()].splitlines()
        hidx, hcat = -1, None
        for i, ln in enumerate(lines):
            s = ln.strip()
            for hre, c in HEADERS:
                if hre.match(s) and not HONOR_RE.match(s):
                    hidx, hcat = i, c
        fails.append((sid, cur, base, sha, pno, t, hit.start(),
                      hidx, hcat, why))

print(f"ADJUDICATING {len(fails)} fails\n")
for (sid, cur, base, sha, pno, t, hpos, hidx, hcat, why) in fails:
    lines = t.splitlines()
    # recompute code line index
    code_i = len(t[:hpos].splitlines()) - 1
    print("=" * 76)
    print(f"ROW {sid} | stored={cur} | {base} p.{pno} | loose-header='{lines[hidx].strip() if hidx >= 0 else '?'}' ({hcat}) at ln{hidx+1} | code at ln{code_i+1} | tight-why={why}")
    lo = max(0, (hidx if hidx >= 0 else code_i - 12))
    for j in range(lo, min(len(lines), code_i + 3)):
        mark = "HDR" if j == hidx else ">> " if j == code_i else "   "
        print(f"  {mark} {lines[j].rstrip()[:95]}")
