#!/usr/bin/env python3
"""probe_b31_flags.py — evidence probe for the 20 B31 merge flags.

For each flagged draft subject: candidate row(s) from the dry-run TIE/TIER2
message + full-vocabulary Jaccard + best per-unit Jaccard + code ownership
from the current baseline CSV. Output: one evidence block per flag.
"""
import csv, json, re, sys

BASE = '/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv'
DRAFTS = '/home/z/my-project/work/pipeline_v2/drafts/'

FLAGS = [
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 1, ['cyber-security', 'sociology-cyber-security']),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 3, ['manufacturing-science-technology-i', 'manufacturing-science-technology-ii']),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 4, None),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 9, None),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 10, None),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 15, ['cyber-security', 'sociology-cyber-security']),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 16, None),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 18, None),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 24, None),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 26, None),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 27, None),
    ('02_btech_mfg-tech_y4_syllabus-cbcs_2019-20', 1, ['automation-and-robotics', 'robotics-and-automation']),
    ('02_btech_mfg-tech_y4_syllabus-cbcs_2019-20', 5, None),
    ('02_btech_mfg-tech_y4_syllabus-cbcs_2019-20', 8, None),
    ('06_btech_mining_y3_syllabus_2025-26', 0, ['environmental-engineering', 'environmental-engineering-i', 'environmental-engineering-ii', 'geoenvironmental-engineering', 'environmental-engineering-process']),
    ('06_btech_mining_y3_syllabus_2025-26', 9, None),
    ('06_btech_mining_y3_syllabus_2025-26', 16, None),
    ('10_btech_open-electives-science_2009-10', 0, None),
    ('10_btech_open-electives-science_2009-10', 1, ['power-station-practice', 'nano-sciences']),
    ('10_btech_open-electives-science_2009-10', 4, None),
]

def norm(s):
    return re.sub(r'[^a-z0-9 ]', ' ', (s or '').lower()).split()

def vocab(units):
    words = set()
    for v in (units or {}).values():
        words |= set(norm(v))
    return words

def unit_j(draft_units, row_units):
    js = []
    for k, dv in (draft_units or {}).items():
        if not dv:
            continue
        dn = set(norm(dv))
        if not dn:
            continue
        best = 0.0
        for rv in (row_units or {}).values():
            rn = set(norm(rv))
            if not rn:
                continue
            j = len(dn & rn) / len(dn | rn)
            best = max(best, j)
        js.append((k, round(best, 2)))
    return js

rows = {}
for r in csv.DictReader(open(BASE)):
    rows[r['subject_id']] = r

def row_units(r):
    u = {}
    for k in range(1, 6):
        t = r.get(f'unit{k}_text', '') or ''
        if t:
            u[str(k)] = t
    return u

def row_all_codes(r):
    toks = set()
    for col in ('primary_code', 'all_codes', 'code_history_all'):
        for t in re.split(r'[;,]', r.get(col, '') or ''):
            t = t.strip().upper()
            if t:
                toks.add(t)
    return toks

# load drafts
draft_cache = {}
def get_subject(stem, idx):
    if stem not in draft_cache:
        draft_cache[stem] = json.load(open(DRAFTS + stem + '.draft.json'))
    return draft_cache[stem]['subjects'][idx]

for stem, idx, cand_ids in FLAGS:
    s = get_subject(stem, idx)
    units = s.get('units', {})
    dv = vocab(units)
    codes = s.get('codes', [])
    print(f"### {stem}::{idx:02d}::{s.get('name','?')!r}")
    print(f"    codes={codes} session={s.get('session') or json.load(open(DRAFTS+stem+'.draft.json'))['session']} "
          f"units={len(units)} flags={s.get('flags')}")
    if cand_ids:
        for cid in cand_ids:
            r = rows.get(cid)
            if r is None:
                print(f"    cand {cid}: NOT FOUND in CSV")
                continue
            rv = vocab(row_units(r))
            j = len(dv & rv) / len(dv | rv) if dv | rv else 0
            uj = unit_j(units, row_units(r))
            print(f"    cand {cid} [{r['subject_name']} | {r['course_name']} | sess={r.get('effective_session_latest')} | "
                  f"primary={r.get('primary_code')} | all={ (r.get('all_codes') or '')[:70]}]")
            print(f"        fullJ={j:.2f} bestPerUnit={uj}")
    # code ownership scan
    owned = []
    for c in codes:
        cu = c.upper().replace(' ', '')
        owners = [sid for sid, r in rows.items() if cu in row_all_codes(r)]
        owned.append((c, owners[:4]))
    print(f"    code owners: {owned}")
    print()
