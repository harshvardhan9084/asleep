#!/usr/bin/env python3
"""Extract printed text for 04's three problem subjects from parsed pages."""
import json, re

BASE = "/home/z/my-project/work/pipeline_v2"
d = json.load(open(f"{BASE}/parsed/04_bpharm_scheme-syllabus_2026-27.json"))
pages = d["pages"] if isinstance(d, dict) and "pages" in d else d
gettext = lambda p: p.get("text", "") if isinstance(p, dict) else str(p)

def show(rng, label, pat=None):
    print(f"\n######## {label} ########")
    for i in rng:
        t = gettext(pages[i])
        print(f"\n----- parsed page idx {i} -----")
        print(t[:2600] if pat is None else "\n".join(l for l in t.splitlines() if re.search(pat, l, re.I))[:2600])

# DSBM BP607T detail block: pages idx 239-242
show(range(239, 243), "DSBM BP607T detail block (idx 239-242)")
# Bio-similars BP708T detail block: idx 268-271
show(range(268, 272), "BP708T Bio-similars detail block (idx 268-271)")
# Industrial Safety BP806T: idx 277-280
show(range(277, 281), "BP806T Industrial Safety detail block (idx 277-280)")
