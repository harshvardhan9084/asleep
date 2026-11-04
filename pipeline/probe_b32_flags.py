#!/usr/bin/env python3
"""probe_b32_flags.py — B32 flag evidence (token overlap + per-unit Jaccard +
row provenance + published-draft cross-checks), the recorded probe class."""
import csv, json, re, sys
from difflib import SequenceMatcher

CSV = '/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv'
DR = '/home/z/my-project/work/pipeline_v2/drafts/'
CODE_RE = re.compile(r"\b([A-Z]{2,4})\s?-?(\d{3})([A-Z]?)\b")
STOP = set("""the of and to a in for with on by an as at or be is are from that this it its into
through their they using use used various study studies engineering science system systems""".split())

rows = list(csv.DictReader(open(CSV)))
by_sid = {r['subject_id']: r for r in rows}

def units_of_row(r):
    return {str(k): r.get(f'unit{k}_text', '') or '' for k in range(1, 6)}

def units_of_draft(d, idx):
    for s in d['subjects']:
        key = f"{d['stem']}::{idx:02d}::" 
        # caller matches by name; use index
    return None

def toks(t):
    return {w for w in re.findall(r"[a-z0-9]+", (t or '').lower()) if w not in STOP and len(w) > 2}

def jac(a, b):
    A, B = toks(a), toks(b)
    return len(A & B) / len(A | B) if (A | B) else 0.0

def distinct_terms(A, B):
    inter = A & B
    return sorted(t for t in inter if len(t) > 5)

def probe(name, dname, idx, target_sid):
    d = json.load(open(DR + dname))
    s = d['subjects'][idx]
    r = by_sid[target_sid]
    print(f"### {name}")
    print(f"  draft: {s['name']!r} codes={s.get('codes')} session={d['session']} units={len(s.get('units') or {})}")
    print(f"  row:   {r['subject_id']!r} codes primary={r['primary_code']} all={r['all_codes'][:80]}")
    print(f"         session_latest={r['effective_session_latest']} first={r['first_introduced_session']}")
    du = s.get('units') or {}
    ru = units_of_row(r)
    full_d = ' '.join(du.values()); full_r = ' '.join(ru.values())
    print(f"  fullJ={jac(full_d, full_r):.2f}  per-unit:", {k: round(jac(du.get(k,''), ru.get(k,'')), 2) for k in ['1','2','3','4','5'] if du.get(k) or ru.get(k)})
    A, B = toks(full_d), toks(full_r)
    print(f"  shared distinctive ({len(distinct_terms(A,B))}):", distinct_terms(A,B)[:14])
    print(f"  draft u1[:160]: {' '.join((du.get('1') or '').split())[:160]}")
    print(f"  row   u1[:160]: {' '.join((ru.get('1') or '').split())[:160]}")
    print(f"  row source_syllabus: {r['source_syllabus'][:110]}")
    print(f"  row code_history: {r.get('code_history_all','')[:200]}")
    print()

probe('01::05 renewable-energy-resources -> renewable-energy-sources',
      '01_btech_open-electives_2019-20.draft.json', 5, 'renewable-energy-sources')
probe('05::18 instrumentation-and-control -> instrumentation-and-process-control',
      '05_btech_pe-ipe_y3_syllabus_2018-19.draft.json', 18, 'instrumentation-and-process-control')
probe('06::02 cad-cam-lab -> cad-cam-lab (name target)',
      '06_btech_pe-ipe_y4_syllabus-cbcs_2019-20.draft.json', 2, 'cad-cam-lab')
probe('06::02 cad-cam-lab -> computer-aided-design-manufacturing-lab (code owner)',
      '06_btech_pe-ipe_y4_syllabus-cbcs_2019-20.draft.json', 2, 'computer-aided-design-manufacturing-lab')
probe('02::26 project-management -> project-management (name target)',
      '02_btech_pe-ipe_syllabus_2020-21.draft.json', 26, 'project-management')
probe('04::07 ergonomics-workplace-design -> ergonomics-workplace-design (name target)',
      '04_btech_pe-ipe_y3_evaluation-scheme_2024-25.draft.json', 7, 'ergonomics-workplace-design')

# provenance of the two contested owners
for sid in ('facility-planning-design', 'computer-aided-design-manufacturing-lab', 'mechanical-vibrations', 'mechatronics-systems'):
    r = by_sid[sid]
    print(f"### {sid}: primary={r['primary_code']} all={r['all_codes']}")
    print(f"    session_latest={r['effective_session_latest']} first={r['first_introduced_session']}")
    print(f"    source={r['source_syllabus'][:140]}")
    print(f"    history={r.get('source_history','')[:160]}")
    print(f"    change_note={r.get('change_note_vs_previous','')[:220]}")
    print()
