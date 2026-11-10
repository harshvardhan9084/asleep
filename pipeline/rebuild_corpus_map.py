#!/usr/bin/env python3
"""rebuild_corpus_map.py — reset-restore helper (B80).
Walks work/repo_asleep/PDFs/**, maps sha16 -> absolute pdf path.
Idempotent; prints doc/page counts (page count via fitz text layer presence
is NOT computed here — that is the page index's job, kept out for speed).
"""
import glob
import hashlib
import json
import os

ROOT = "/home/z/my-project/work/repo_asleep/PDFs"
OUT = "/home/z/my-project/work/pipeline_v2/corpus_map.json"


def sha16(p):
    # registry convention (w9a_book_trunc.sha16): MD5 hexdigest[:16]
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def main():
    pdfs = sorted(glob.glob(os.path.join(ROOT, "**", "*.pdf"), recursive=True))
    m = {}
    dups = 0
    for p in pdfs:
        s = sha16(p)
        if s in m:
            dups += 1
            continue
        m[s] = p
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(m, open(OUT, "w"), indent=1)
    print(f"CORPUS_MAP|pdfs={len(pdfs)}|unique_shas={len(m)}|dups_skipped={dups} -> {OUT}")


if __name__ == "__main__":
    main()
