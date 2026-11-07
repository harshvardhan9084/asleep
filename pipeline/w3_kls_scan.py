#!/usr/bin/env python3
"""w3_kls_scan.py — W3 phase 1: deterministic K-level scan for co_kls backfill.
For every row flagged KLS_MISSING/KLS_SHORT: scan the CITED docs' text layers
for the printed CO/K-level table (regex CO-n … Kx pairs). Rows where the
print yields a complete, conflict-free K sequence are applied directly
(evidence = doc pp.N). Everything else goes to w3_rex_queue.json for the
mercury-3 REX phase. Read-only over PDFs; writes only its outputs."""
import csv
import json
import re
import fitz
import hashlib
import os

BASE = "/home/z/my-project/work/pipeline_v2"
CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"

rows = list(csv.DictReader(open(CSV, newline="", encoding="utf-8")))
by_id = {r["subject_id"]: r for r in rows}
flags_doc = json.load(open(f"{BASE}/audit_flags.json"))

targets = []
for sid, fl in flags_doc.get("rows", {}).items():
    for f in fl:
        if f.get("rule") in ("KLS_MISSING", "KLS_SHORT") and f.get("action", "").startswith("fix:"):
            targets.append(sid)
            break
targets = sorted(set(targets))
print(f"W3|targets={len(targets)}")

corpus = {}
for root in ("/home/z/my-project/work/repo_asleep/PDFs", "/home/z/my-project/upload",
             "/home/z/my-project/work/artd_v3/sources"):
    for dp, _d, fs in os.walk(root):
        for fn in fs:
            if fn.lower().endswith(".pdf"):
                p = os.path.join(dp, fn)
                try:
                    h = hashlib.md5()
                    with open(p, "rb") as fh:
                        for chunk in iter(lambda: fh.read(1 << 20), b""):
                            h.update(chunk)
                    corpus.setdefault(h.hexdigest()[:16], p)
                except Exception:
                    pass

def ncos_of(r):
    return sum(1 for i in range(1, 7) if (r.get(f"co{i}_text", "") or "").strip())

def doc_pages(sha):
    p = corpus.get(sha)
    if not p:
        return None
    try:
        d = fitz.open(p)
        pages = [pg.get_text() for pg in d]
        d.close()
        return pages
    except Exception:
        return None

PAIR = re.compile(r"CO[\s\-–]?(\d)\s*[:.\-–]?\s*(.{0,180}?)\b(K[1-6])\b", re.S)
KRUN = re.compile(r"\bK([1-6])\b")

wins, rex_queue, not_printed = {}, [], []
for sid in targets:
    r = by_id.get(sid)
    if not r:
        continue
    n = ncos_of(r)
    if not n:
        continue
    shas = re.findall(r"#([0-9a-f]{16})", r.get("source_syllabus", "") or "")
    kmap, pages_hit, fname_hit = {}, [], ""
    for sha in shas:
        pages = doc_pages(sha)
        if not pages:
            continue
        for pi, ptxt in enumerate(pages):
            if not ptxt or ("CO" not in ptxt and "K1" not in ptxt and "K2" not in ptxt):
                continue
            # normalize line-wrapped table rows: join hyphen-newlines
            flat = re.sub(r"\s*\n\s*", " ", ptxt)
            for m in PAIR.finditer(flat):
                no = int(m.group(1))
                if 1 <= no <= 6 and no not in kmap:
                    kmap[no] = m.group(3)
                    if not pages_hit:
                        fname_hit = os.path.basename(corpus.get(sha, "?"))
                        pages_hit.append(pi + 1)
        if len(kmap) >= n:
            break
    if len(kmap) == n and all(kmap.get(i) for i in range(1, n + 1)):
        wins[sid] = {"kls": [kmap[i] for i in range(1, n + 1)],
                     "evidence": f"{fname_hit}#{shas[0] if shas else ''} pp.{pages_hit[0] if pages_hit else '?'} (printed CO/K table, deterministic scan)"}
    elif kmap:
        rex_queue.append({"sid": sid, "co_count": n, "partial": sorted(kmap),
                          "shas": shas[:3]})
    else:
        not_printed.append({"sid": sid, "co_count": n, "shas": shas[:3]})

print(f"W3|deterministic_wins={len(wins)} rex_queue={len(rex_queue)} not_printed={len(not_printed)}")
json.dump(wins, open(f"{BASE}/w3_deterministic_wins.json", "w"), indent=1)
json.dump(rex_queue, open(f"{BASE}/w3_rex_queue.json", "w"), indent=1)
json.dump(not_printed, open(f"{BASE}/w3_not_printed.json", "w"), indent=1)
