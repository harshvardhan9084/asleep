#!/usr/bin/env python3
"""patch_b31_verify.py — B31 verify remedies (evidence-recorded, RULES §6/§7).

1) doc 04 (2021-22 Mfg-Tech y4): 8 subjects store units as nested
   {"1": {"title": ..., "text": ...}} dicts — the §7 spec wants verbatim
   strings. Flatten to the verbatim unit text; the printed unit heading
   (e.g. 'Introduction') moves to the subject quirk so the print evidence
   is kept (B28 marker-hygiene class: draft-side structure must not lose
   printed content, and the catalog consumes unit text strings only).

2) doc 02 (2019-20 Mfg-Tech y4 CBCS): the four sessional scheme-only rows
   (RMT753 Industrial Training / RMT754 Project-1 / RMT851 Seminar /
   RMT852 Project-2) print no unit theory anywhere in the document (scheme
   table L-T-P/marks rows only) — add the recorded
   scheme_row_only_detailed_syllabus_not_printed flag (verifier B2 remedy
   class) so the zero-guess omission downgrades to WARN.
"""
import json

D = '/home/z/my-project/work/pipeline_v2/drafts/'

# --- doc 04: flatten nested units -------------------------------------------
p = D + '04_btech_mfg-tech_y4_syllabus_2021-22.draft.json'
d = json.load(open(p))
flat = 0
for s in d['subjects']:
    u = s.get('units', {})
    if u and all(isinstance(v, dict) for v in u.values()):
        new_u, titles = {}, []
        for k in sorted(u, key=lambda x: int(x) if str(x).isdigit() else 99):
            v = u[k]
            txt = v.get('text', '')
            if not isinstance(txt, str):
                raise SystemExit(f'STOP: unit {k} of {s["name"]} has non-str text')
            new_u[str(k)] = txt
            if v.get('title'):
                titles.append(f"unit-{k} prints heading '{v['title']}'")
        s['units'] = new_u
        if titles:
            q = f'draft-side unit dicts flattened to verbatim unit text; printed unit headings kept here: ' + '; '.join(titles)
            s.setdefault('quirks', []).append(q)
        flat += 1
json.dump(d, open(p, 'w'), indent=1, ensure_ascii=False)
print(f'doc04: flattened {flat} subjects')

# --- doc 02: flag the 4 sessional scheme-only rows ---------------------------
p = D + '02_btech_mfg-tech_y4_syllabus-cbcs_2019-20.draft.json'
d = json.load(open(p))
n = 0
for s in d['subjects']:
    if s.get('units') == {} and s.get('codes') and s['codes'][0] in ('RMT753', 'RMT754', 'RMT851', 'RMT852'):
        fl = s.setdefault('flags', [])
        tag = 'scheme_row_only_detailed_syllabus_not_printed'
        if tag not in fl:
            fl.append(tag)
        s.setdefault('quirks', []).append(
            'sessional row: document prints scheme-table L-T-P/marks only; '
            'no unit theory, COs or books printed anywhere in the doc (zero-guess omission)')
        n += 1
json.dump(d, open(p, 'w'), indent=1, ensure_ascii=False)
print(f'doc02: flagged {n} sessional rows')
