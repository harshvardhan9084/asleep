#!/usr/bin/env python3
"""Resolve which documents the registry actually cites, and test content-identity
of upload/ copies against stored fulltext extracts (zero-guess)."""
import os, re, json, csv, hashlib, glob
from collections import defaultdict

BASE = '/home/z/my-project'
REG = os.path.join(BASE, 'download/art_d_final/syllabus_extreme_rich.csv')

pairs = defaultdict(set)
with open(REG, newline='', encoding='utf-8') as fh:
    rdr = csv.DictReader(fh)
    for row in rdr:
        for col in ('source_syllabus', 'source_history'):
            v = row.get(col) or ''
            for m in re.findall(r'([A-Za-z0-9_.() \-]+?\.(?:pdf|PDF))#([0-9a-f]{16})', v):
                pairs[m[1]].add(m[0].strip())

print("== CITED (sha16 -> filenames) ==")
for sha, fns in sorted(pairs.items()):
    print(f"  {sha}  {sorted(fns)}")

# stored fulltext extracts anywhere under work/
print()
print("== STORED EXTRACTS / ARTIFACT DIRS ==")
for d in ['work/registry_v6', 'work/artd_v3', 'work/registry_v5', 'work/artd_v2']:
    p = os.path.join(BASE, d)
    if os.path.isdir(p):
        n = sum(len(f) for _, _, f in os.walk(p))
        print(f"  {d}/  ({n} files)")
        for f in sorted(os.listdir(p))[:25]:
            print(f"     - {f}")

# registry branch coverage
branches = set()
with open(REG, newline='', encoding='utf-8') as fh:
    for row in csv.DictReader(fh):
        if row.get('row_kind') == 'subject':
            for b in (row.get('branch_names') or '').split(';'):
                if b.strip():
                    branches.add(b.strip())
print()
print(f"== BRANCHES IN REGISTRY ({len(branches)}) ==")
print("  " + ' | '.join(sorted(branches)))

# subjects+codes coverage for Mining / E&C / CSAI-CSML-CSDS-CSIOT K-era
print()
print("== K-era 2nd-yr CSE-family codes present (KAU/KCS/KOE 3xx/4xx sample) ==")
codes_seen = set()
with open(REG, newline='', encoding='utf-8') as fh:
    for row in csv.DictReader(fh):
        if row.get('row_kind') == 'subject':
            codes_seen.update(c for c in (row.get('all_codes') or '').split(';') if c.strip())
for probe in ['KAS301', 'KAS302', 'KCS301', 'KCS302', 'KCS303', 'KCS304', 'KCS305', 'KCS306',
              'KCS307', 'KCS308', 'KCS309', 'KCS310', 'KCS311', 'KOE031', 'KOE032', 'KOE033',
              'KOE034', 'KOE035', 'KOE036', 'KOE037', 'KOE038', 'KCS401', 'KCS402', 'KCS403',
              'KCS451', 'KCS452', 'KCS453', 'KOE039', 'KOE040', 'KOE041', 'KOE042', 'KOE043',
              'KOE044', 'KOE045', 'KOE046', 'KOE047', 'KOE048', 'KOE049']:
    print(f"  {probe}: {'YES' if probe in codes_seen else 'no'}")
