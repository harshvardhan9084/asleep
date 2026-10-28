#!/usr/bin/env python3
"""Independent post-commit verification of the B02 registry state."""
import csv, json, re, hashlib
from collections import Counter

CSV = '/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv'
rows = list(csv.DictReader(open(CSV, newline='', encoding='utf-8')))
hdr = list(rows[0].keys())
print(f"rows={len(rows)} cols={len(hdr)}")

kinds = Counter(r['row_kind'] for r in rows)
print('row_kinds:', dict(kinds))

# G2-style ownership recount
CODE_RE = re.compile(r"^[A-Z]{2,4}\d{3}[A-Z]?$")
own = {}
dup = []
for r in rows:
    toks = set()
    for c in (r.get('primary_code', '') or '').split(';'):
        c = c.strip()
        if CODE_RE.match(c):
            toks.add(c)
    for c in (r.get('all_codes', '') or '').split(';'):
        c = c.strip()
        if CODE_RE.match(c):
            toks.add(c)
    for t in toks:
        if t in own and own[t] != r['subject_id']:
            dup.append(t)
        own[t] = r['subject_id']
print(f"owned codes={len(own)} dups={len(dup)} {dup[:5]}")

# new rows sanity
print()
print('== B02 appended rows (21) ==')
for r in rows:
    cn = r.get('change_note_vs_previous', '')
    if cn.startswith('First ingestion ('):
        print(f"  {r['primary_code']:8s} {r['subject_name'][:46]:46s} eff={r['effective_session_latest']} py={r['program_year']} sem={r['semester_slots']} branch={r['branch_names'][:44]} det={r['has_detailed_syllabus']}")

# B02-touched update rows: check change notes + provenance chains
print()
print('== spot checks ==')
by_id = {r['subject_id']: r for r in rows}
for sid in ['microprocessor', 'microprocessor-lab', 'python-language-programming-lab',
            'introduction-to-data-analytics-and-visualization', 'big-data-and-analytics-lab',
            'mine-surveying-ii', 'sports-and-yoga-or-nss-ii', 'data-structure',
            'cloud-computing', 'mineralogy-petrology-and-stratigraphy']:
    r = by_id.get(sid)
    if not r:
        print(f"  MISSING {sid}")
        continue
    print(f"  {sid}: codes={r['all_codes'][:56]} hist={r['code_history_all'][:88]}")
    print(f"      src chain ({len(r['source_syllabus'].split(';'))}): {r['source_syllabus'][:150]}")

# viewer load sanity: JSON columns parse
bad = 0
for r in rows:
    for col in ('textbooks_structured', 'reference_books_structured', 'experiments_structured', 'objectives_print'):
        v = r.get(col, '')
        if v:
            try:
                json.loads(v)
            except Exception:
                bad += 1
                print(f"  BAD JSON {sid}:{col}")
print(f"json-column parse errors: {bad}")

# branch set
branches = set()
for r in rows:
    if r['row_kind'] == 'subject':
        for b in (r.get('branch_names') or '').split(';'):
            if b.strip():
                branches.add(b.strip())
print(f"branches ({len(branches)}): {' | '.join(sorted(branches))}")
