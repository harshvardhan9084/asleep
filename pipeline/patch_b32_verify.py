#!/usr/bin/env python3
"""patch_b32_verify.py — B32 verify-remedy evidence (RULES §6/§4; recorded classes).

Doc 01 (open-electives 2019-20): pages 14-21 carry a shift-encoded cmap (glyph-
to-unicode offset; e.g. '0RGHOOLQJDQG6LPXODWLRQ' -> 'Modelling and Simulation'):
the linear text layer does NOT represent the visible print, so text-layer
containment is structurally impossible for the four Sem-VII subjects
(ROE071-074) — the recorded v12/v13 class (B10/B15 evidence). The mechanical
decode (chr(ord+0x1D) family) was validated on anchors and the VISIBLE PRINT
attested on page images p.14 (Modelling: heading, 5 units, 5 COs, references)
and p.19 (UHBC: Subject Code ROE074, [L-T-P: 3-0-0], Pre-requisites 'AUC-001 or
RVE 301/401', Module 1) by the main agent (RULES §6). Subjects flagged
`unit_ocr_recovered_no_text_layer` with page-citing quirks -> unit/CO
containment problems downgrade to WARN.
Also: ROE074/ROE087 printed prerequisites recorded verbatim (p.19 / p.9); the
p.9 'Prerequisite: RVE 301/401-...' line recorded as a non_subject_row (v10
class: printed non-subject evidence, not a missing subject -> clears the
RVE301 GAP).

Doc 05: LEAN MANUFACTURING / QUALITY ENGINEERING IN MANUFACTURING print no
code anywhere (pool list prints names only; detail pages p.14/p.30 carry no
code line) — no-code print attested with page locators; quirk wording carries
the recorded 'no code' downgrade token (v10 B06 class).

Doc 06: RME084 Industrial Safety Engineering / RPI088 Principles of Metal
Forming Technology are MOOC elective-pool rows (p.2) with NO detail pages in
the document (fulltext scan: name appears only on the p.2 pool list) —
`detailed_syllabus_not_printed` evidence flag appended (B2 scheme-only class).
"""
import json, re, sys

DR = '/home/z/my-project/work/pipeline_v2/drafts/'

def load(name):
    return json.load(open(DR + name))

def save(name, d):
    json.dump(d, open(DR + name, 'w'), indent=1, ensure_ascii=False)

# ---------- doc 01 ----------
d1 = load('01_btech_open-electives_2019-20.draft.json')
enc_quirk = ('pages 14-21 shift-encoded cmap (glyph-to-unicode offset +0x1D class; '
             "e.g. '0RGHOOLQJDQG6LPXODWLRQ' prints 'Modelling and Simulation'): the linear "
             'text layer does not represent the visible print; units/COs/books transcribed by '
             'mechanical decode validated on anchors (AUC-001, RVE 301/401, ROE074, clean '
             'duplicates p.11/p.12); visible print attested on page images p.14 and p.19 by the '
             'main agent (RULES §6) — patch-b32 verify remedy, v12/v13 recorded class')
n_flipped = 0
for s in d1['subjects']:
    if s.get('codes') and s['codes'][0] in ('ROE071', 'ROE072', 'ROE073', 'ROE074'):
        if 'unit_ocr_recovered_no_text_layer' not in (s.get('flags') or []):
            s.setdefault('flags', []).append('unit_ocr_recovered_no_text_layer')
        if enc_quirk not in (s.get('quirks') or []):
            s.setdefault('quirks', []).append(enc_quirk)
        n_flipped += 1
    if s.get('codes') and s['codes'][0] == 'ROE074':
        prereq = 'AUC-001 or RVE 301/401 \u201cUniversal Human Values and Professional Ethics\u201d'
        s['prerequisites'] = prereq
        q = ('printed Pre-requisites line transcribed verbatim to prerequisites '
             '(p.19 visible print: Pre-requisites- AUC-001 or RVE 301/401 "Universal Human '
             'Values and Professional Ethics") — patch-b32')
        if q not in (s.get('quirks') or []):
            s.setdefault('quirks', []).append(q)
    if s.get('codes') and s['codes'][0] == 'ROE087':
        prereq = 'RVE 301/401- Universal Human Values and Professional Ethics'
        s['prerequisites'] = prereq
        q = ('printed Prerequisite line transcribed verbatim to prerequisites '
             '(p.9: "Prerequisite: RVE 301/401- Universal Human Values and Professional '
             'Ethics") — patch-b32')
        if q not in (s.get('quirks') or []):
            s.setdefault('quirks', []).append(q)
nsr = d1.setdefault('non_subject_rows', [])
prereq_row = {
    'kind': 'prerequisite_note',
    'print': 'Prerequisite: RVE 301/401- Universal Human Values and Professional Ethics',
    'locator': 'p.9 (ROE087 HUMAN VALUES IN MADHYASTH DARSHAN page; printed prerequisite '
               'cross-reference, not a separate syllabus subject) — patch-b32 v10 class'}
if not any(r.get('kind') == 'prerequisite_note' for r in nsr):
    nsr.append(prereq_row)
d1.setdefault('quirks', []).append(
    'pages 14-21 shift-encoded cmap decode attested on page images (p.14 Modelling, p.19 '
    'UHBC/ROE074) per RULES §6 — patch-b32; the four Sem-VII subjects carry '
    'unit_ocr_recovered_no_text_layer (v12/v13 recorded class)')
save('01_btech_open-electives_2019-20.draft.json', d1)
print(f'doc01: {n_flipped} subjects flagged unit_ocr_recovered_no_text_layer; '
      f'ROE074+ROE087 prerequisites recorded; prerequisite_note row added')

# ---------- doc 05 ----------
d5 = load('05_btech_pe-ipe_y3_syllabus_2018-19.draft.json')
rec5 = json.load(open('/home/z/my-project/work/pipeline_v2/parsed/05_btech_pe-ipe_y3_syllabus_2018-19.json'))
pool_page = None
for i, p in enumerate(rec5['pages'], 1):
    if re.search(r'4\.\s*Lean Manufacturing', p['text']):
        pool_page = i
        break
n5 = 0
for s in d5['subjects']:
    nm = s['name'].upper()
    if nm.startswith('LEAN MANUFACTURING') or nm.startswith('QUALITY ENGINEERING IN MANUFACTURING'):
        detail = 'p.14' if nm.startswith('LEAN') else 'p.30'
        q = (f'no code printed anywhere in the document for this subject: the elective pool '
             f'list (p.{pool_page}) prints the name without code and the detail page ({detail}) '
             f'prints no code line — no-code print attested (RULES §4 zero-guess; v10 B06 '
             f'no-code class) — patch-b32')
        if q not in (s.get('quirks') or []):
            s.setdefault('quirks', []).append(q)
        n5 += 1
save('05_btech_pe-ipe_y3_syllabus_2018-19.draft.json', d5)
print(f'doc05: {n5} subjects no-code quirks added (pool page p.{pool_page})')

# ---------- doc 06 ----------
d6 = load('06_btech_pe-ipe_y4_syllabus-cbcs_2019-20.draft.json')
n6 = 0
for s in d6['subjects']:
    if s.get('codes') and s['codes'][0] in ('RME084', 'RPI088'):
        if 'detailed_syllabus_not_printed' not in (s.get('flags') or []):
            s.setdefault('flags', []).append('detailed_syllabus_not_printed')
        q = ('MOOC elective-pool row (p.2) prints the name only; no unit-level syllabus for '
             'this subject anywhere in the document (fulltext scan: the name appears only on '
             'the p.2 pool list) — detailed_syllabus_not_printed evidence flag (B2 scheme-only '
             'recorded class) — patch-b32')
        if q not in (s.get('quirks') or []):
            s.setdefault('quirks', []).append(q)
        n6 += 1
save('06_btech_pe-ipe_y4_syllabus-cbcs_2019-20.draft.json', d6)
print(f'doc06: {n6} subjects detailed_syllabus_not_printed flags added')
