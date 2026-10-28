#!/usr/bin/env python3
"""1) Which docs established E&C and CSE(DS) rows? 2) Are upload Civil/AIML copies
content-identical to the stored Task-28 fulltexts? (normalized-alnum diff)"""
import os, re, csv, hashlib, unicodedata
import fitz

BASE = '/home/z/my-project'
REG = os.path.join(BASE, 'download/art_d_final/syllabus_extreme_rich.csv')

rows = list(csv.DictReader(open(REG, newline='', encoding='utf-8')))

def show_source(pred, label):
    print(f"== {label} ==")
    n = 0
    for r in rows:
        if r.get('row_kind') != 'subject':
            continue
        if pred(r):
            n += 1
            if n <= 3:
                print(f"  {r['primary_code']:8s} {r['subject_name'][:38]:38s} src={r.get('source_syllabus','')[:80]}")
    print(f"  ({n} subject rows)\n")

show_source(lambda r: 'Electronics and Computer' in (r.get('branch_names') or ''), 'E&C rows')
show_source(lambda r: '(Data Science)' in (r.get('branch_names') or ''), 'CSE(DS) rows')
show_source(lambda r: 'Artificial Intelligence & Data Science' in (r.get('branch_names') or ''), 'AI&DS rows')
show_source(lambda r: (r.get('all_codes') or '').find('KOE03') >= 0, 'KOE03x rows')

def norm_alnum(t):
    t = unicodedata.normalize('NFKC', t)
    return re.sub(r'[^a-z0-9]+', '', t.lower())

def pdf_norm_text(p):
    d = fitz.open(p)
    t = ''.join(pg.get_text() for pg in d)
    d.close()
    return norm_alnum(t)

def file_norm_text(p):
    return norm_alnum(open(p, encoding='utf-8', errors='replace').read())

pairs = [
    ('upload/B.Tech. 3rd Year Civil Engineering.pdf', 'work/registry_v6/civil_fulltext.txt'),
    ('upload/B.Tech. 3rd Year Civil Engineering.pdf', 'work/registry_v6/civil_fulltext_plumber.txt'),
    ('upload/B.Tech. Arttificial Intelligence & Machine Learning Syllabus 3rd year 2024-25.pdf', 'work/registry_v6/aiml_fulltext.txt'),
    ('upload/B.Tech. Arttificial Intelligence & Machine Learning Syllabus 3rd year 2024-25.pdf', 'work/registry_v6/aiml_fulltext_plumber.txt'),
]
print("== CONTENT-IDENTITY (normalized alnum containment) ==")
for pdf_rel, txt_rel in pairs:
    pp = os.path.join(BASE, pdf_rel)
    tp = os.path.join(BASE, txt_rel)
    if not os.path.exists(pp) or not os.path.exists(tp):
        print(f"  MISSING: {pdf_rel} or {txt_rel}")
        continue
    a = pdf_norm_text(pp)
    b = file_norm_text(tp)
    # mutual containment with a tolerance window: substring check both ways on chunks
    contain = a[:20000] in b if len(a) <= len(b) else b[:20000] in a
    # ratio fallback
    m = min(len(a), len(b))
    same_prefix = a[:m] == b[:m]
    print(f"  {os.path.basename(pdf_rel)[:40]:40s} vs {os.path.basename(txt_rel)[:28]:28s} "
          f"| len {len(a)} vs {len(b)} | prefix-equal={same_prefix} | 20k-contain={contain}")
