#!/usr/bin/env python3
"""probe_b31_flags2.py — find the fuzzy candidates for the unnamed TIER2 flags."""
import csv, json, re
from difflib import SequenceMatcher

BASE = '/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv'
DRAFTS = '/home/z/my-project/work/pipeline_v2/drafts/'

TARGETS = [
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 4),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 9),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 10),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 16),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 18),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 24),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 26),
    ('01_btech_mfg-tech_y3_syllabus_2018-19', 27),
    ('02_btech_mfg-tech_y4_syllabus-cbcs_2019-20', 5),
    ('02_btech_mfg-tech_y4_syllabus-cbcs_2019-20', 8),
    ('06_btech_mining_y3_syllabus_2025-26', 9),
    ('06_btech_mining_y3_syllabus_2025-26', 16),
]

def norm(s):
    return re.sub(r'[^a-z0-9 ]', ' ', (s or '').lower()).split()

def vocab(units):
    w = set()
    for v in (units or {}).values():
        w |= set(norm(v))
    return w

rows = [r for r in csv.DictReader(open(BASE)) if r['row_kind'] == 'subject']

def row_units(r):
    return {str(k): (r.get(f'unit{k}_text') or '') for k in range(1, 6) if (r.get(f'unit{k}_text') or '')}

def slugify(n):
    return re.sub(r'[^a-z0-9]+', '-', n.lower()).strip('-')

draft_cache = {}
for stem, idx in TARGETS:
    if stem not in draft_cache:
        draft_cache[stem] = json.load(open(DRAFTS + stem + '.draft.json'))
    s = draft_cache[stem]['subjects'][idx]
    nm = re.sub(r'[^a-z0-9]', '', s['name'].lower())
    dv = vocab(s.get('units', {}))
    scored = []
    for r in rows:
        if r['course_name'] != 'BTech':
            continue
        sim = SequenceMatcher(None, nm, re.sub(r'[^a-z0-9]', '', r['subject_name'].lower())).ratio()
        if sim < 0.80:
            continue
        rv = vocab(row_units(r))
        j = len(dv & rv) / len(dv | rv) if (dv | rv) else 0
        uj = []
        for k, dtxt in (s.get('units') or {}).items():
            dn = set(norm(dtxt))
            best = 0
            for rt in (row_units(r) or {}).values():
                rn = set(norm(rt))
                if rn:
                    best = max(best, len(dn & rn) / len(dn | rn))
            uj.append(round(best, 2))
        scored.append((round(sim, 2), round(j, 2), uj, r['subject_id'], r['subject_name'][:44],
                       r['effective_session_latest'], (r.get('primary_code') or '')))
    scored.sort(reverse=True)
    print(f"### {stem}::{idx:02d} {s['name']!r} codes={s.get('codes')}")
    for t in scored[:4]:
        print(f"    sim={t[0]} J={t[1]} unitJ={t[2]} {t[3]} [{t[4]}] sess={t[5]} pri={t[6]}")
    if not scored:
        print("    NO same-course fuzzy candidate >= 0.80")
    print()
