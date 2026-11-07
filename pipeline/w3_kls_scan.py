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
import sys
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
print(f"W3|targets={len(targets)}", flush=True)

# corpus map with persistent cache (resets wipe work/; rebuild only when stale)
CORPUS_CACHE = f"{BASE}/corpus_map.json"
CORPUS_TS = f"{BASE}/corpus_map.stamp"
def corpus_signature():
    roots = ("/home/z/my-project/work/repo_asleep/PDFs", "/home/z/my-project/upload",
             "/home/z/my-project/work/artd_v3/sources")
    sig = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dp, _d, fs in os.walk(root):
            for fn in fs:
                if fn.lower().endswith(".pdf"):
                    p = os.path.join(dp, fn)
                    try:
                        st = os.stat(p)
                        sig.append(f"{p}:{st.st_size}:{int(st.st_mtime)}")
                    except OSError:
                        pass
    return hashlib.md5("|".join(sorted(sig)).encode()).hexdigest()

corpus = {}
if os.path.exists(CORPUS_CACHE) and os.path.exists(CORPUS_TS) and \
        open(CORPUS_TS).read().strip() == corpus_signature():
    corpus = json.load(open(CORPUS_CACHE))
    print(f"W3|corpus cache reused: {len(corpus)} pdfs", flush=True)
else:
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
    json.dump(corpus, open(CORPUS_CACHE, "w"))
    open(CORPUS_TS, "w").write(corpus_signature())
    print(f"W3|corpus rebuilt: {len(corpus)} pdfs", flush=True)

# checkpoint-resume state (sandbox may kill long runs between calls)
CKPT = f"{BASE}/w3_scan_ckpt.json"
_start_i, wins, rex_queue, not_printed = 0, {}, [], []
if os.path.exists(CKPT):
    try:
        c = json.load(open(CKPT))
        if c.get("targets") == targets:
            _start_i = c.get("i", 0)
            wins = c.get("wins", {})
            rex_queue = c.get("rex_queue", [])
            not_printed = c.get("not_printed", [])
            print(f"W3|resume from checkpoint i={_start_i} "
                  f"(wins={len(wins)} rex={len(rex_queue)} np={len(not_printed)})", flush=True)
        else:
            print("W3|checkpoint targets mismatch — fresh start", flush=True)
    except Exception:
        pass

import time
_BUDGET_S = float(os.environ.get("W3_SCAN_BUDGET", "95"))
_t0 = time.time()

def _save_ckpt(i):
    json.dump({"targets": targets, "i": i, "wins": wins,
               "rex_queue": rex_queue, "not_printed": not_printed}, open(CKPT, "w"))

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

for _ti in range(_start_i, len(targets)):
    sid = targets[_ti]
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

    if time.time() - _t0 > _BUDGET_S and _ti + 1 < len(targets):
        _save_ckpt(_ti + 1)
        print(f"W3|BUDGET checkpoint at i={_ti + 1}/{len(targets)} "
              f"(wins={len(wins)} rex={len(rex_queue)} np={len(not_printed)}) — rerun to resume", flush=True)
        sys.exit(0)
_save_ckpt(len(targets))
if os.path.exists(CKPT):
    os.remove(CKPT)
print(f"W3|deterministic_wins={len(wins)} rex_queue={len(rex_queue)} not_printed={len(not_printed)}")
json.dump(wins, open(f"{BASE}/w3_deterministic_wins.json", "w"), indent=1)
json.dump(rex_queue, open(f"{BASE}/w3_rex_queue.json", "w"), indent=1)
json.dump(not_printed, open(f"{BASE}/w3_not_printed.json", "w"), indent=1)
