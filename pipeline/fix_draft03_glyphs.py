#!/usr/bin/env python3
"""Fix 03 (CSE-AI 2022-23) Cloud Computing book strings to the VISIBLE PRINT
(page-13 image, RULES §6: visible print authoritative over garbled text layer).
Records the correction as a quirk. Evidence: Read tool page-image of
upload/B.Tech._3rd_Yr_CSE(AI)_2022_23_revised_.pdf page 13 shows
'Rittinghouse, John W., and James F. Ransome, —Cloud Computing: Implementation,
Management and Security, CRC Press, 2017.' and 'Rajkumar Buyya, Christian
Vecchiola, S. ThamaraiSelvi, —Mastering Cloud Computing, Tata Mcgraw Hill, 2013.'
"""
import json

P = '/home/z/my-project/work/pipeline_v2/drafts/03_B.Tech._3rd_Yr_CSE_AI__2022_23_revised_.draft.json'
d = json.load(open(P))

FIX = {
    'Riǆnghouse': 'Rittinghouse',
    'CompuƑing: ImplementaƑion': 'Computing: Implementation',
    'ChrisƑian': 'Christian',
    'CompuƑing, Tata': 'Computing, Tata',
}
fixed = 0
for s in d['subjects']:
    if s.get('name') != 'Cloud Computing':
        continue
    for key in ('textbooks', 'reference_books'):
        for b in s.get(key) or []:
            orig = b['book']
            new = orig
            for a, bb in FIX.items():
                new = new.replace(a, bb)
            if new != orig:
                b['book'] = new
                fixed += 1

QK = ("p.13 visible print (page image, RULES §6) reads 'Rittinghouse ... Cloud Computing: "
      "Implementation, Management and Security' and 'Christian Vecchiola ... Mastering Cloud "
      "Computing' — draft book strings 2/3 corrected from text-layer font-encoding glyphs "
      "(ƫ/Ɵ layer, ǆ/Ƒ first transcription) to the authoritative visible print")
if QK not in d.get('quirks', []):
    d.setdefault('quirks', []).append(QK)

json.dump(d, open(P, 'w'), indent=1, ensure_ascii=False)
print(f"fixed {fixed} book strings; quirk appended")
for s in d['subjects']:
    if s.get('name') == 'Cloud Computing':
        for b in (s.get('textbooks') or [])[:3]:
            print('  ', b['book'][:95])
