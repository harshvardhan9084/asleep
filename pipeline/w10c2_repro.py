#!/usr/bin/env python3
"""w10c2_repro.py — reproduction harness for the 3 W10c2 print_category
verdicts (zero-guess standard, B74 style). For each: row identity, cited
docs, every hit page's printed context (5 lines up, code line, 2 down) and
the governing header line — printed for manual adjudication."""
import json
import os
import re
import sys

import fitz

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import w10c2_fulldoc_probe as P

BASE = P.BASE

rows = P.WC.load_rows()
by_id = {r["subject_id"]: r for r in rows}
ck = json.load(open(f"{BASE}/w10c2_ckpt.json"))["results"]
corpus = json.load(open(f"{BASE}/corpus_map.json"))

for sid, v in ck.items():
    if v.get("status") != "print_category":
        continue
    r = by_id[sid]
    print("=" * 80)
    print(f"ROW {sid} | {r.get('subject_name_print') or r.get('subject_name')} "
          f"| course={r.get('course_name')} | session={r.get('effective_session_latest')}")
    print(f"  primary_code={r.get('primary_code')} | scheme_line={r.get('source_scheme_line','')[:90]}")
    print(f"  VERDICT {v['category']} at {v['evidence']}")
    pc = (r.get("primary_code") or "").strip().upper()
    variants = P.code_variants(pc)
    pat = re.compile(r"\b(" + "|".join(re.escape(x) for x in variants) + r")\b", re.I)
    for cite in re.findall(r"(\S+)#([0-9a-f]{12,16})\s*p\.(\d+)", v["evidence"]):
        base, sha, pno = cite
        path = P.resolve(corpus, sha)
        if not path:
            print(f"  !! path missing for {sha}")
            continue
        d = fitz.open(path)
        t = d[int(pno) - 1].get_text() or ""
        d.close()
        lines = t.splitlines()
        idxs = [i for i, ln in enumerate(lines) if pat.search(ln)]
        for i in idxs:
            lo, hi = max(0, i - 5), min(len(lines), i + 3)
            print(f"  --- {base} p.{pno} ctx (lines {lo+1}-{hi}):")
            for j in range(lo, hi):
                mark = ">>" if j == i else "  "
                print(f"    {mark} {lines[j].rstrip()[:100]}")
            cat = P.governing_header(t, t.find(lines[i]) if lines[i] in t else 0)
            hdrs = [ln.strip() for ln in lines[:i] if P.governing_header("\n".join(lines[:lines.index(ln)+1]) if ln in lines else "", 0)]
            print(f"  governing_header on page -> {cat}")
print("=" * 80)
print("REPRO DONE — each verdict above must show the code line sitting under an")
print("independent standalone section header on the SAME page (tight grammar).")
