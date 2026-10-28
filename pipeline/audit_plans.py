#!/usr/bin/env python3
"""Audit every merge plan: draft name vs target row identity, plus the code
ownership evidence behind each match. Zero-guess adjudication support."""
import json, csv, re
from difflib import SequenceMatcher

BASE = '/home/z/my-project'
rep = json.load(open(f'{BASE}/work/pipeline_v2/decisions_report.json'))
rows = {r['subject_id']: r for r in csv.DictReader(open(f'{BASE}/download/art_d_final/syllabus_extreme_rich.csv', encoding='utf-8'))}

def norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', (s or '').lower())).strip()

def sim(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio() * 100

print('== UPDATE plans with draft-name vs target-name similarity < 70 ==')
for p in rep['plans']:
    if p['op'] != 'UPDATE':
        continue
    t = rows.get(p['target'])
    if not t:
        print(f"  !! {p['key'][:60]} target MISSING {p['target']}")
        continue
    s = sim(p['name'], t['subject_name'])
    if s < 70:
        print(f"  sim={s:3.0f} {p['key'].split('::')[0][:2]}::{p['name'][:42]:42s} -> {p['target'][:36]:36s} | row codes={t['all_codes'][:60]} | hist={t['code_history_all'][:100]}")

print()
print('== TIE plans ==')
for p in rep['plans']:
    if p['op'] == 'TIE':
        print(f"  {p['key'][:70]}")
        print(f"     {p['info']} -> targets: {p['target']}")
        for sid in p['target'].split(';'):
            t = rows.get(sid)
            if t:
                print(f"       - {sid}: codes={t['all_codes'][:70]} | hist={t['code_history_all'][:110]}")

print()
print('== APPEND plans ==')
for p in rep['plans']:
    if p['op'] == 'APPEND':
        print(f"  {p['key'][:70]} codes={p['codes']}")

print()
print('== FLAGS (unique kinds) ==')
kinds = {}
for f in rep['flags']:
    kinds.setdefault(f[1].split(' ')[0], []).append(f[0])
for k, v in sorted(kinds.items()):
    print(f"  {k}: {len(v)}")
