#!/usr/bin/env python3
"""Classify every PDF in the workspace: already-cited by the registry (by sha16) vs new.
Zero-guess: classification by content hash + registry citations only."""
import os, re, json, hashlib, csv

BASE = '/home/z/my-project'
REG = os.path.join(BASE, 'download/art_d_final/syllabus_extreme_rich.csv')

# 1. hash all PDFs
pdfs = {}
for dp, dn, fn in os.walk(BASE):
    if '/.git' in dp or 'node_modules' in dp:
        continue
    for f in fn:
        if f.lower().endswith('.pdf'):
            p = os.path.join(dp, f)
            try:
                h = hashlib.md5(open(p, 'rb').read()).hexdigest()
            except Exception:
                continue
            pdfs[p] = h

# 2. registry citations: every sha16-like token in source_syllabus + source_history
sha_tokens = set()
with open(REG, newline='', encoding='utf-8') as fh:
    rdr = csv.DictReader(fh)
    for row in rdr:
        for col in ('source_syllabus', 'source_history'):
            v = row.get(col) or ''
            for tok in re.findall(r'#([0-9a-f]{16})', v):
                sha_tokens.add(tok)

print(f"PDFs in workspace: {len(pdfs)}; distinct cited sha16s in registry: {len(sha_tokens)}")
print()

# 3. classify
cited, uncited = [], []
for p, h in sorted(pdfs.items()):
    if h[:16] in sha_tokens:
        cited.append(p)
    else:
        uncited.append(p)

print("== ALREADY CITED (sha16 match) ==")
for p in cited:
    print("  ", p.replace(BASE + '/', ''), hashlib.md5(open(p, 'rb').read()).hexdigest()[:16])
print()
print("== NOT CITED ==")
for p in uncited:
    print("  ", p.replace(BASE + '/', ''), hashlib.md5(open(p, 'rb').read()).hexdigest()[:16])

# 4. quick page-1 text sniff for uncited docs (scope classification, no guessing beyond print)
print()
print("== PAGE-1 SNIFF (uncited) ==")
import fitz
for p in uncited:
    try:
        d = fitz.open(p)
        t = (d[0].get_text() or '')[:220].replace('\n', ' | ')
        print(f"  [{len(d)}pp] {os.path.basename(p)}\n      {t}")
        d.close()
    except Exception as e:
        print(f"  [ERR] {os.path.basename(p)}: {e}")
