#!/usr/bin/env python3
"""CRON-20261104-B29 flag probe — evidence dump for adjudication review.
For each of the 27 flags: the draft subject, the ladder candidates, the
published rows involved (subject_id, name, session, owned codes, unit1 head),
plus per-unit Jaccard for contested fuzzy matches (B28 probe class)."""
import csv, json, re, sys

CSV_PATH = '/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv'
DRAFTS = '/home/z/my-project/work/pipeline_v2/drafts/B29/'
BASE = '/home/z/my-project/work/pipeline_v2/'

rows = list(csv.DictReader(open(CSV_PATH)))
by_sid = {r['subject_id']: r for r in rows}

def norm_name(s):
    return re.sub(r'[^a-z0-9 ]', '', (s or '').lower()).strip()

def norm_code(c):
    return re.sub(r'[^A-Z0-9]', '', (c or '').upper())

def unit_set(r):
    try:
        u = json.loads(r.get('units_all') or r.get('units') or '{}')
        if isinstance(u, dict):
            return set(re.findall(r'[a-z]{4,}', json.dumps(u).lower()))
    except Exception:
        pass
    return set()

def draft_set(stem, idx):
    d = json.load(open(DRAFTS + stem + '.draft.json'))
    s = d['subjects'][idx]
    return s, set(re.findall(r'[a-z]{4,}', json.dumps(s.get('units', {})).lower()))

def show(r, label):
    print(f"  [{label}] {r['subject_id']} | {r['subject_name']} | course={r['course_name']} | "
          f"sess={r.get('effective_session_latest','')} | primary={r.get('primary_code','')}")
    print(f"      all_codes={r.get('all_codes','')[:120]}")
    print(f"      branches={r.get('branch_names','')[:100]}")
    u1 = ''
    try:
        u = json.loads(r.get('units_all') or r.get('units') or '{}')
        if isinstance(u, dict):
            u1 = (u.get('1') or '')[:90]
    except Exception:
        pass
    print(f"      unit1: {u1}")

report = json.load(open(BASE + 'decisions_report.json'))
drafts = {}
for stem, idx, slug in (f['0'].split('::') for f in []):
    pass

flag_keys = [(f[0], f[1], f[2]) for f in report['flags']]
# cache drafts
dcache = {}
for k, ftype, detail in flag_keys:
    stem, idx, slug = k.split('::')
    if stem not in dcache:
        dcache[stem] = json.load(open(DRAFTS + stem + '.draft.json'))
    s = dcache[stem]['subjects'][int(idx)]
    print(f"\n=== {k} | {ftype}")
    print(f"  draft: {s.get('name')} | codes={s.get('codes')} | sess={dcache[stem].get('session')} | "
          f"sem={s.get('semester')} | type={s.get('subject_type','')}")
    dset = set(re.findall(r'[a-z]{4,}', json.dumps(s.get('units', {})).lower()))
    # find the candidate rows named in the flag detail
    cands = set()
    m = re.findall(r'owned by ([a-z0-9\-]+)', detail)
    cands.update(m)
    m2 = re.findall(r'(\d+)/([a-z0-9\-]+)', detail)
    for _, sid in m2:
        cands.add(sid)
    if 'quality-management' in detail:
        cands.update(['quality-management', 'total-quality-management-tqm'])
    for sid in sorted(cands):
        r = by_sid.get(sid)
        if not r:
            print(f"  [{cand}] {sid} — NOT FOUND in CSV")
            continue
        show(r, 'owner/cand')
        rset = unit_set(r)
        inter = len(dset & rset)
        union = len(dset | rset) or 1
        print(f"      vocab: |draft|={len(dset)} |row|={len(rset)} inter={inter} J={inter/union:.2f}")
