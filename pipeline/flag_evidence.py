#!/usr/bin/env python3
"""Evidence gathering for every verify flag (zero-guess: look at the print)."""
import json, re, os

P = '/home/z/my-project/work/pipeline_v2/parsed'
D = '/home/z/my-project/work/pipeline_v2/drafts'

def ft(stem):
    rec = json.load(open(f'{P}/{stem}.json'))
    return [p['text'] for p in rec['pages']], rec

def find_ctx(pages, pat, width=110):
    for i, t in enumerate(pages, 1):
        for m in re.finditer(pat, t):
            s = max(0, m.start() - width // 2)
            print(f'   p{i}: ...{t[s:m.end()+width]!r}...')
            return
    print('   NOT FOUND IN TEXT LAYER')

print('=== 1) RS232 context (01 CSAI, Microprocessor Lab area) ===')
pages, _ = ft('01_B.Tech_2nd_Year_CSAI_CSML_CSDS_CSIOT_2021-22_0709')
find_ctx(pages, r'RS\s?-?232')

print()
print('=== 2) 01 Dhamdhere book print ===')
find_ctx(pages, r'Dhamdhere')

print()
print('=== 3) 01 Gaonkar book print ===')
find_ctx(pages, r'Gaonkar')

print()
print('=== 4) 03 Cloud Computing Rittinghouse/Vecchiola print ===')
pages3, _ = ft('03_B.Tech._3rd_Yr_CSE_AI__2022_23_revised_')
find_ctx(pages3, r'Ritt| Ri.z|锌|Ringh|Ransom')
find_ctx(pages3, r'Vecchiola|Chris')

print()
print('=== 5) 06 Operating System Lab experiment print ===')
pages6, _ = ft('06_B.Tech_2nd_Yr_CSE_v3')
find_ctx(pages6, r'file storage allocation')

print()
print('=== 6) draft-side strings for the glyph cases ===')
d3 = json.load(open(f'{D}/03_B.Tech._3rd_Yr_CSE_AI__2022_23_revised_.draft.json'))
for s in d3['subjects']:
    for b in (s.get('textbooks') or []) + (s.get('reference_books') or []):
        if 'Ri' in b['book'] and ('ghouse' in b['book'] or 'Ransom' in b['book'] or 'Vecchiola' in b['book']):
            print(f"   [{s['name']}] {b['book']!r}")

print()
print('=== 7) 06: which subjects lack units but carry what ===')
d6 = json.load(open(f'{D}/06_B.Tech_2nd_Yr_CSE_v3.draft.json'))
for s in d6['subjects']:
    if not s.get('units'):
        print(f"   {s['name'][:52]:52s} exps={len(s.get('experiments') or [])} flags={s.get('flags')}")

print()
print('=== 8) 01/02/03/04/05 lab-subject flag/experiment profile ===')
for stem in ['01_B.Tech_2nd_Year_CSAI_CSML_CSDS_CSIOT_2021-22_0709',
             '02_B.Tech._2nd_Year_E_C_AICTE_Model_Curriculum_2019-20_23_March_2021',
             '03_B.Tech._3rd_Yr_CSE_AI__2022_23_revised_',
             '04_B.Tech._3rd_Yr_CSE_DS__2022_23_revised_',
             '05_B.Tech_2nd_Year_Mining_Engg_Evaluation_scheme_2024-25']:
    d = json.load(open(f'{D}/{stem}.draft.json'))
    nou = [s for s in d['subjects'] if not s.get('units')]
    print(f'   {stem[:40]:40s} no-units subjects: {len(nou)}')
    for s in nou:
        print(f'      - {s["name"][:56]:56s} exps={len(s.get("experiments") or [])} flags={s.get("flags")}')
