#!/usr/bin/env python3
"""B29 verify-remedy patches, round 2 (D09 + D10), per the recorded remedy classes.
- D09 RME653 'Design And Simulation - Lab II': the printed detail page is ONLY an
  A/B/C practical-turns note block (fulltext-verified: '(3practical turns)' /
  '(5practical turns)' / mini-project home assignment) — no unit theory and no
  numbered experiment list anywhere for this lab. Zero-guess keeps them as
  notes_print; flag practical_turns_notes_only_no_units_printed added, downgrade
  via new verifier v17 remedy (pattern of v11/v14/v15/v16).
- D10 KME554 + KNC601/602: scheme-row-only in this doc (KME 554 prints with
  U+00A0 separator 'KME\xa0554'; KNC601/602 single Sem-VI scheme-table occurrence;
  no detail pages). Draft-level flag statements moved onto the subjects as
  per-subject evidence flags (the verifier reads per-subject flags only).
- D10 IoT Lab: two-column table interleave quirk for the experiment WARN.
"""
import json

BASE = '/home/z/my-project/work/pipeline_v2/drafts/'
changed = []

# --- D09 RME653 -------------------------------------------------------------
p = BASE + '09_btech_me_syllabus_2018-19.draft.json'
d = json.load(open(p, encoding='utf-8'))
for s in d['subjects']:
    if s.get('name') == 'Design And Simulation - Lab II':
        fl = s.get('flags') or []
        ev = 'practical_turns_notes_only_no_units_printed'
        if ev not in fl:
            fl.append(ev)
        s['flags'] = fl
        q = s.get('quirks') or []
        note = ('B29 verify remedy: the printed detail page for this lab carries ONLY the '
                'A./B./C. practical-turns note block (transcribed verbatim in notes_print; '
                '(3practical turns)/(5practical turns)/mini-project home assignment) — no unit '
                'theory and no numbered experiment list printed anywhere for RME653 in this '
                'document; zero-guess forbids inventing experiments. Evidence flag '
                'practical_turns_notes_only_no_units_printed added per v11/v14/v15/v16 remedy class.')
        if note not in q:
            q.append(note)
        s['quirks'] = q
        changed.append(('09…2018-19', s['name'], 'flag practical_turns_notes_only'))
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# --- D10 KME554 / KNC601-602 / IoT Lab ---------------------------------------
p = BASE + '10_btech_me_syllabus_2020-21.draft.json'
d = json.load(open(p, encoding='utf-8'))
for s in d['subjects']:
    codes = set(s.get('codes') or [])
    nm = s.get('name', '')
    if codes & {'KME554'}:
        ev = 'scheme_row_only_detailed_syllabus_not_printed'
        fl = s.get('flags') or []
        if ev not in fl:
            fl.append(ev)
        s['flags'] = fl
        q = s.get('quirks') or []
        note = ('B29 verify remedy: scheme-row-only in this document — Sem-V scheme table '
                'prints "KME\u00a0554 Mini Project or Internship Assessment*" (0 0 2, 50/50, credit 1; '
                'U+00A0 separator explains raw-token miss) with footnote asterisk; no detail page '
                'printed here. Evidence flag per B2 remedy class.')
        if note not in q:
            q.append(note)
        s['quirks'] = q
        changed.append(('10…2020-21', nm[:40], 'flag scheme_row_only (KME554)'))
    elif codes & {'KNC601', 'KNC602'}:
        ev = 'scheme_row_only_detailed_syllabus_not_printed'
        fl = s.get('flags') or []
        if ev not in fl:
            fl.append(ev)
        s['flags'] = fl
        q = s.get('quirks') or []
        note = ('B29 verify remedy: scheme-row-only in this document — KNC601/KNC602 prints once, '
                'in the Sem-VI scheme table ("Constitution of India, Law and Engineering / Indian '
                'Tradition, Culture and Society", 2 0 0, 15/10/25/50); sibling Sem-V row prints '
                'KNC501/KNC502 with the same names; no detail page printed here. Evidence flag per '
                'B2 remedy class.')
        if note not in q:
            q.append(note)
        s['quirks'] = q
        changed.append(('10…2020-21', nm[:40], 'flag scheme_row_only (KNC601/602)'))
    elif 'Internet of Things' in nm and 'Lab' in nm:
        q = s.get('quirks') or []
        note = ('B29 verify note: the printed experiment table is two-column (experiment text | '
                'outcome text) and the text layer interleaves the outcome-column fragments between '
                'experiment-column fragments (e.g. "Write a program on Arduino/Raspberry Pi to" / '
                '"Able to upload status of devices and" on consecutive lines); long experiment '
                'needles therefore cannot be raw-contained — the transcribed experiment text is '
                'faithful column reads, interleave recorded here.')
        if note not in q:
            q.append(note)
        s['quirks'] = q
        changed.append(('10…2020-21', nm[:40], 'interleave quirk'))
# keep the draft-level statement too (harmless), but record that per-subject flags now carry it
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

for c in changed:
    print('PATCHED|' + '|'.join(c))
print('OK')
