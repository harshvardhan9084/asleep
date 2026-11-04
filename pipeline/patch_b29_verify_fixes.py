#!/usr/bin/env python3
"""B29 verify-remedy patches (3 drafts), per recorded prior-batch classes.
1) D02: BNC501/502 + BNC601/602 are scheme-table-only rows (notes record 'no
   detail page printed here'); add the evidence flag the verifier downgrades
   (B2 remedy class). Keep the pairing needs_review for merge adjudication.
2) D07: Mathematics-III unit1 carried two bracketed draft-side markers for the
   bitmap integral formulas (text layer prints only 'of the type ... and 10') —
   B28 doc-04 class: markers live in the quirk, unit text kept verbatim-only.
3) D08: Applied Physics Lab experiments were transcribed as plain strings —
   convert to RULES §7 dict shape {'no': n, 'exp': s}.
"""
import json, sys

BASE = '/home/z/my-project/work/pipeline_v2/drafts/'
changed = []

# --- 1) D02 BNC rows -------------------------------------------------------
p = BASE + '02_btech_me-ind_y3_evaluation-scheme_2024-25.draft.json'
d = json.load(open(p, encoding='utf-8'))
for s in d['subjects']:
    codes = set(s.get('codes') or [])
    if codes & {'BNC501', 'BNC502', 'BNC601', 'BNC602'}:
        fl = s.get('flags') or []
        ev = 'scheme_row_only_detailed_syllabus_not_printed'
        if not any(ev == f or 'scheme' in str(f).lower() and 'only' in str(f).lower() for f in fl):
            fl.append(ev)
        s['flags'] = fl
        # record the remedy in quirks for provenance
        q = s.get('quirks') or []
        note = ('B29 verify remedy: scheme-table-only row (scheme tables pp.5-7 print no '
                'unit theory for this NC subject; notes record no detail page) — evidence '
                'flag scheme_row_only_detailed_syllabus_not_printed added per B2 remedy class.')
        if note not in q:
            q.append(note)
        s['quirks'] = q
        changed.append((p.split('/')[-1], s['name'][:40], 'flags+=scheme_row_only'))
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# --- 2) D07 Mathematics-III unit1 ------------------------------------------
p = BASE + '07_btech_me-pe_syllabus_2009-10.draft.json'
d = json.load(open(p, encoding='utf-8'))
for s in d['subjects']:
    if s.get('name') == 'Mathematics-III':
        u1 = s['units']['1']
        marker = ' [integral formula not decodable in text layer or page render]'
        before = u1
        u1 = u1.replace(marker, '').replace(marker.strip(), '')
        u1 = ' '.join(u1.split())  # normalize the whitespace left by dropped markers
        s['units']['1'] = u1
        q = s.get('quirks') or []
        for i, qu in enumerate(q):
            if 'left as bracketed markers' in qu:
                q[i] = qu.replace(
                    'left as bracketed markers, zero guessing',
                    'originally transcribed with bracketed draft-side markers in unit1; '
                    'B29 verify remedy moved the markers into this quirk per the recorded '
                    'B28 doc-04 Mathematics-III class — unit1 text kept verbatim-only '
                    '(text layer prints "of the type" + "and" + lecture count "10"), zero guessing')
        s['quirks'] = q
        changed.append((p.split('/')[-1], 'Mathematics-III', f'unit1 {len(before)}→{len(u1)} chars'))
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# --- 3) D08 Applied Physics Lab experiments --------------------------------
p = BASE + '08_btech_me_course-structure_2026-27.draft.json'
d = json.load(open(p, encoding='utf-8'))
for s in d['subjects']:
    exps = s.get('experiments')
    if exps and any(isinstance(e, str) for e in exps):
        fixed = []
        for i, e in enumerate(exps, 1):
            if isinstance(e, str):
                fixed.append({'no': i, 'exp': e})
            else:
                # keep dict entries; renumber only if mixed shapes collide
                fixed.append(e)
        s['experiments'] = fixed
        q = s.get('quirks') or []
        note = ('B29 verify remedy: experiment list re-keyed from plain strings to the '
                'RULES §7 {"no","exp"} dict shape (no text changed).')
        if note not in q:
            q.append(note)
        s['quirks'] = q
        changed.append((p.split('/')[-1], s['name'][:40], f'experiments → dicts ({len(fixed)})'))
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

for c in changed:
    print('PATCHED|' + '|'.join(c))
print('OK')
