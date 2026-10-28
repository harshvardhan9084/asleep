#!/usr/bin/env python3
"""Localize divergence between upload copies and stored Task-28 fulltexts."""
import os, re, unicodedata, difflib

BASE = '/home/z/my-project'

def norm_alnum(t):
    t = unicodedata.normalize('NFKC', t)
    return re.sub(r'[^a-z0-9]+', '', t.lower())

pairs = [
    ('upload/B.Tech. 3rd Year Civil Engineering.pdf', 'work/registry_v6/civil_fulltext.txt', 'civil'),
    ('upload/B.Tech. Arttificial Intelligence & Machine Learning Syllabus 3rd year 2024-25.pdf', 'work/registry_v6/aiml_fulltext.txt', 'aiml'),
]
import fitz
for pdf_rel, txt_rel, tag in pairs:
    d = fitz.open(os.path.join(BASE, pdf_rel))
    a = norm_alnum(''.join(pg.get_text() for pg in d))
    d.close()
    b = norm_alnum(open(os.path.join(BASE, txt_rel), encoding='utf-8', errors='replace').read())
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    ops = [o for o in sm.get_opcodes() if o[0] != 'equal']
    print(f"== {tag}: {len(ops)} diff blocks, ratio={sm.ratio():.6f} ==")
    for op, i1, i2, j1, j2 in ops[:12]:
        frag_a = a[i1:i2][:90]
        frag_b = b[j1:j2][:90]
        print(f"  {op:8s} A[{i1}:{i2}] {frag_a!r}")
        print(f"  {'':8s} B[{j1}:{j2}] {frag_b!r}")
    print()
