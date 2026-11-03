#!/usr/bin/env python3
"""Inventory the pre-existing G2/G3 violations in the baseline CSV."""
import csv, re
from collections import defaultdict

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def normc(c): return re.sub(r'[^A-Z0-9]', '', (c or '').upper())

rows = list(csv.DictReader(open('/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv')))
CODE = re.compile(r'^[A-Z]{2,4}[0-9]{3}[A-Z]?$')

own = defaultdict(list)
for r in rows:
    if r['row_kind'] != 'subject':
        continue
    toks = set()
    for c in (r['primary_code'] or '').split(';'):
        if CODE.match(normc(c)):
            toks.add(normc(c))
    for c in (r['all_codes'] or '').split(';'):
        if CODE.match(normc(c)):
            toks.add(normc(c))
    for t in toks:
        own[(r['course_name'], t)].append(r)

g2 = [(k, v) for k, v in own.items() if len(v) > 1]
print(f"=== G2 violation groups: {len(g2)} ===")
for (ck, t), v in sorted(g2):
    print(f"{t} [{ck}]:")
    for r in v:
        print(f"   {r['subject_id']} | sess={r['effective_session_latest']} | pc={r['primary_code']} | codes={r['all_codes'][:45]}")

names = defaultdict(list)
for r in rows:
    if r['row_kind'] == 'subject':
        names[(norm(r['subject_name']), r['course_name'])].append(r)

g3 = [(k, v) for k, v in names.items() if len(v) > 1]
print(f"=== G3 (name,course) dups: {len(g3)} ===")
for k, v in g3:
    for r in v:
        print(f"   {r['subject_id']} | {r['subject_name'][:55]} | sess={r['effective_session_latest']} | codes={r['all_codes'][:45]}")
