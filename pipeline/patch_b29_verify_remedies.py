#!/usr/bin/env python3
"""CRON-20261104-B29 verify remedies — 4 FAILs + 1 WARN, each with recorded
evidence classes from prior batches (RULES §6: visible print authoritative;
draft-side annotations live in quirks, unit/exp text verbatim-only).

R1 doc02: BME554 + BNC501/502 + BNC601/602 are scheme-row-only subjects
   (printed only in the Sem-V p.2 / Sem-VI p.3 evaluation-scheme tables; no
   detailed syllabus section anywhere in the doc) -> flag
   scheme_row_only_detailed_syllabus_not_printed (doc-04/B28 class) + quirks.
R2 doc03: Inventory Management (detail p.17) + Quality Engineering In
   Manufacturing (detail p.34) print NO code anywhere (pool list p.11 prints
   them uncoded: '5. InventoryManagement' / '5. Quality Engineering
   InManufacturing') -> flag 'no-code-printed-in-document' (v10/B06 class)
   + quirks. Zero-guess: codes stay absent.
R3 doc07: MATHEMATICS-III unit1 carried two draft-side bracketed markers for
   the bitmap integral formulas the text layer drops (p.11 prints 'of the
   type [bitmap] and [bitmap] 10') -> markers moved to quirk, unit text kept
   verbatim-only (B28 doc-04 Mathematics-III class).
R4 doc09: RELIABILITY ENGINEERING unit5 carried the draft-side annotation
   '(second unit printed under the same heading)' inside the unit text ->
   moved to the subject quirk (already explains the duplicate UNIT-IV print);
   unit text verbatim-only (B28 doc-10 annotation class).
R5 doc08: CAED Lab exp 13 'Internal assessment, viva voce and end semester
   practical examination [Hours: 03]' carried a draft-side Hours marker ->
   stripped to verbatim text; hours value already recorded in subject quirk
   6 (B28 doc-10 annotation class).
"""
import json, sys

DRAFTS = '/home/z/my-project/work/pipeline_v2/drafts/'
changed = []

def load(stem):
    return json.load(open(DRAFTS + stem + '.draft.json'))

def save(stem, d):
    json.dump(d, open(DRAFTS + stem + '.draft.json', 'w'), indent=1, ensure_ascii=False)

# ---- R1 doc02: scheme-row-only flags ----
stem = '02_btech_me-ind_y3_evaluation-scheme_2024-25'
d = load(stem)
r1 = 0
for s in d['subjects']:
    codes = [c.replace(' ', '').upper() for c in (s.get('codes') or [])]
    nm = (s.get('name') or '').lower()
    hit = None
    if any(c.startswith('BME554') for c in codes):
        hit = 'BME 554 Mini Project/Internship Assessment* — printed only as Sem-V evaluation-scheme row 9 (p.2: P 0-0-2, 50/50/50/100) with the p.2 footnote "The Mini Project or internship (4‐5 weeks) conducted during summer break after IV semester and will be assessed during semester"; no detailed syllabus section anywhere in the document (fulltext sweep); scheme-row-only per print design.'
    elif any(c.startswith('BNC501') for c in codes):
        hit = 'BNC501/502 Constitution of India/ Essence of Indian Traditional Knowledge — printed only as Sem-V evaluation-scheme row 10 (p.2: T VA/HS 2-0-0, 15/10/25/50, NC) with row 11 MOOCs note; no detailed syllabus section anywhere in the document (fulltext sweep); scheme-row-only per print design.'
    elif any(c.startswith('BNC601') for c in codes):
        hit = 'BNC601/602 Constitution of India/ Essence of Indian Traditional Knowledge — printed only as Sem-VI evaluation-scheme row 9 (p.3: T VA/HS 2-0-0, 15/10/25/50, NC) with row 10 MOOCs note; no detailed syllabus section anywhere in the document (fulltext sweep); scheme-row-only per print design.'
    if hit:
        fl = s.setdefault('flags', [])
        if 'scheme_row_only_detailed_syllabus_not_printed' not in fl:
            fl.append('scheme_row_only_detailed_syllabus_not_printed')
        q = s.setdefault('quirks', [])
        if hit not in q:
            q.append(hit)
        r1 += 1
save(stem, d); changed.append(f'R1 {stem}: {r1} subjects flagged')

# ---- R2 doc03: no-code evidence flags ----
stem = '03_btech_me-ind_y3_syllabus_2018-19'
d = load(stem)
r2 = 0
for s in d['subjects']:
    nm = (s.get('name') or '').lower()
    hit = None
    if 'inventory management' in nm:
        hit = 'no code printed anywhere in the document for this Elective-2 subject: the elective pool list (p.11) prints "5. InventoryManagement" uncoded and the detail page (p.17) is headed "INVENTORY MANAGEMENT" with no code line; sibling electives carry RME/RMI codes — zero-guess keeps codes absent (v10/B06 no-code print class).'
    elif 'quality engineering in manufacturing' in nm:
        hit = 'no code printed anywhere in the document for this Elective-2 subject: the elective pool list (p.11) prints "5. Quality Engineering InManufacturing" uncoded and the detail page (p.34) is headed "QUALITY ENGINEERING IN MANUFACTURING" with no code line; sibling electives carry RME/RMI codes — zero-guess keeps codes absent (v10/B06 no-code print class).'
    if hit:
        fl = s.setdefault('flags', [])
        if 'no-code-printed-in-document' not in fl:
            fl.append('no-code-printed-in-document')
        q = s.setdefault('quirks', [])
        if hit not in q:
            q.append(hit)
        r2 += 1
save(stem, d); changed.append(f'R2 {stem}: {r2} subjects flagged')

# ---- R3 doc07: Math-III unit1 bitmap-formula markers -> quirk ----
stem = '07_btech_me-pe_syllabus_2009-10'
d = load(stem)
r3 = 0
for s in d['subjects']:
    if 'MATHEMATICS' in (s.get('name') or '').upper() and 'EAS-301' in [c.replace(' ', '') for c in (s.get('codes') or [])]:
        u1 = s['units'].get('1', '')
        m1 = '[two printed integral formulas dropped by text layer]'
        m2 = '[formula dropped]'
        if m1 in u1 or m2 in u1:
            s['units']['1'] = u1.replace(m1, '').replace(m2, '')
            # collapse the double space left by the removals, keep '  and 10' spacing natural
            s['units']['1'] = s['units']['1'].replace('of the type   and  10', 'of the type  and 10')
            q = s.setdefault('quirks', [])
            note = ('Unit-I prints two integral formulas as bitmap images after "Evaluation of real integrals of the type" '
                    '(p.11: text layer prints only "of the type" then "and" then the lecture count 10); the formulas are '
                    'attested from the page print and recorded here instead of the unit text — unit text kept verbatim-only '
                    '(B28 doc-04 Mathematics-III integral-formula class).')
            if note not in q:
                q.append(note)
            r3 += 1
save(stem, d); changed.append(f'R3 {stem}: {r3} unit1 patched')

# ---- R4 doc09: Reliability unit5 annotation -> quirk ----
stem = '09_btech_me_syllabus_2018-19'
d = load(stem)
r4 = 0
for s in d['subjects']:
    if 'RELIABILITY' in (s.get('name') or '').upper():
        u5 = s['units'].get('5', '')
        ann = '(second unit printed under the same heading)'
        if ann in u5:
            s['units']['5'] = u5.replace(ann, '').replace('UNIT-IV \n', 'UNIT-IV\n').replace('UNIT-IV \n8', 'UNIT-IV\n8')
            s['units']['5'] = s['units']['5'].replace('UNIT-IV\n8', 'UNIT-IV\n8', 1)
            q = s.setdefault('quirks', [])
            newq = []
            for qq in q:
                if "recorded as unit '5' with the duplicate heading noted in-line" in qq:
                    qq = qq.replace(
                        "recorded as unit '5' with the duplicate heading noted in-line",
                        "recorded as unit '5'; the draft-side annotation '(second unit printed under the same heading)' "
                        "is kept in this quirk rather than the unit text (verbatim-only unit text, B28 doc-10 annotation class)")
                newq.append(qq)
            s['quirks'] = newq
            r4 += 1
save(stem, d); changed.append(f'R4 {stem}: {r4} unit5 patched')

# ---- R5 doc08: CAED lab exp13 marker strip ----
stem = '08_btech_me_course-structure_2026-27'
d = load(stem)
r5 = 0
for s in d['subjects']:
    if 'Computer Aided Engineering Drawing Lab' in (s.get('name') or ''):
        for e in s.get('experiments', []):
            if e.get('no') == 13 and '[Hours: 03]' in e.get('exp', ''):
                e['exp'] = e['exp'].replace(' [Hours: 03]', '')
                r5 += 1
        newq = []
        for qq in (s.get('quirks') or []):
            if "recorded as experiments 13-14 for completeness" in qq:
                qq += " The draft-side '[Hours: ...]' markers on rows 13-14 are recorded here instead of the experiment text (verbatim-only, B28 doc-10 annotation class); Hours 03 / Total 45 as printed."
            newq.append(qq)
        s['quirks'] = newq
save(stem, d); changed.append(f'R5 {stem}: {r5} exp13 patched')

for c in changed:
    print(c)
print('DONE')
