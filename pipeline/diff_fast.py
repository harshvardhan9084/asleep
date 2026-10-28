#!/usr/bin/env python3
"""Fast divergence localization: first-diff index + per-4k block hash comparison."""
import os, re, unicodedata
import fitz

BASE = '/home/z/my-project'

def norm_alnum(t):
    t = unicodedata.normalize('NFKC', t)
    return re.sub(r'[^a-z0-9]+', '', t.lower())

pairs = [
    ('upload/B.Tech. 3rd Year Civil Engineering.pdf', 'work/registry_v6/civil_fulltext.txt', 'civil'),
    ('upload/B.Tech. Arttificial Intelligence & Machine Learning Syllabus 3rd year 2024-25.pdf', 'work/registry_v6/aiml_fulltext.txt', 'aiml'),
]
for pdf_rel, txt_rel, tag in pairs:
    d = fitz.open(os.path.join(BASE, pdf_rel))
    a = norm_alnum(''.join(pg.get_text() for pg in d))
    d.close()
    b = norm_alnum(open(os.path.join(BASE, txt_rel), encoding='utf-8', errors='replace').read())
    # first divergence
    m = min(len(a), len(b))
    i = 0
    while i < m and a[i] == b[i]:
        i += 1
    print(f"== {tag}: lenA={len(a)} lenB={len(b)} first_divergence@{i} ==")
    print(f"   A: ...{a[max(0,i-60):i]}[DIV]{a[i:i+120]}...")
    print(f"   B: ...{b[max(0,i-60):i]}[DIV]{b[i:i+120]}...")
    # after re-syncing (align by searching A-tail in B), where do they re-converge?
    probe = a[i:i+40]
    j = b.find(probe, i)
    print(f"   A[{i}:{i+40}] re-found in B at {j} (gap {None if j < 0 else j - i})")
    if j >= 0:
        # count total mismatched 4k blocks after re-alignment by offset j-i
        off = j - i
        bad = []
        for s in range(j, min(len(a), len(b) - off) - 4000, 4000):
            if a[s:s+4000] != b[s+off:s+off+4000]:
                bad.append(s)
        print(f"   mismatched 4k blocks (offset-aligned): {len(bad)} {bad[:8]}")
        print(f"   tail check: A-end={a[-80:]!r}")
        print(f"               B-end={b[-80:]!r}")
    print()
