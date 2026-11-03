#!/usr/bin/env python3
# Segment e: B.Pharm Semesters VII+VIII (parsed pages 174-221 1-based)
import json, re, os

PARSED = '/home/z/my-project/work/pipeline_v2/parsed/05_bpharm_scheme-syllabus_2026-27.json'
OUT = '/home/z/my-project/work/pipeline_v2/drafts/05e_bpharm_scheme-syllabus_2026-27.json'
PDF_REL = '5-course/2026-27/bpharm_scheme-syllabus_2026-27.pdf'
STEM = '05_bpharm_scheme-syllabus_2026-27'
SESSION = '2026-27'
SHA16 = '97b5d901f34c75a4'

d = json.load(open(PARSED))
P = {p['page']: p['text'] for p in d['pages']}  # 1-based 'page' field

def clean(s):
    return re.sub(r'\s+', ' ', s).strip()

# ---------------- card boundaries ----------------
HDR = re.compile(r'Course Code\s*\n\s*Course Title\s*\n\s*Course Type')
hdr_pages = sorted(pg for pg in range(174, 222) if HDR.search(P[pg]))

def card_text(start_pg, end_pg):
    """Raw text of a card spanning pages [start_pg..end_pg] (inclusive, 1-based)."""
    buf = []
    for pg in range(start_pg, end_pg + 1):
        t = P[pg]
        if pg == start_pg:
            m = HDR.search(t)
            t = t[m.end():]
        # trim next card header if it leaked into the slice (shared pages)
        m = HDR.search(t)
        if m:
            t = t[:m.start()]
        # trim running header
        t = re.sub(r'^\s*B\.\s*Pharm\.\s*Syllabus\s*\n\s*\d+\s*\n', '', t)
        buf.append(t)
    return '\n'.join(buf)

# ---------------- scheme table rows ----------------
def table_rows(pg, codes):
    t = P[pg]
    starts = []
    for c in codes:
        m = re.search(r'\b%s\b' % c, t)
        starts.append((m.start(), c))
    starts.sort()
    rows = {}
    for i, (pos, c) in enumerate(starts):
        nxt = starts[i + 1][0] if i + 1 < len(starts) else t.find('Total', pos)
        rows[c] = clean(t[pos:nxt])
    return rows

sem7_codes = ['BP701T','BP702T','BP703T','BP704T','BP705T','BP706T','BP707T','BP708T','BP709P','BP710RP']
sem8_codes = ['BP801T','BP802T','BP803T','BP804T','BP805T','BP806T','BP807P','BP808P','BP809P','BP810RP']
sem7_rows = table_rows(174, sem7_codes)
sem8_rows = table_rows(200, sem8_codes)

# ---------------- card spec ----------------
CARDS = [
    # (code, card_pages, sem, table_row)
    ('BP701T', (175, 178), 'VII', sem7_rows['BP701T']),
    ('BP702T', (179, 180), 'VII', sem7_rows['BP702T']),
    ('BP703T', (181, 183), 'VII', sem7_rows['BP703T']),
    ('BP704T', (184, 185), 'VII', sem7_rows['BP704T']),
    ('BP705T', (186, 188), 'VII', sem7_rows['BP705T']),
    ('BP706T', (189, 192), 'VII', sem7_rows['BP706T']),
    ('BP707T', (193, 195), 'VII', sem7_rows['BP707T']),
    ('BP709P', (197, 198), 'VII', sem7_rows['BP709P']),
    ('BP710RP', (199, 199), 'VII', sem7_rows['BP710RP']),
    ('BP801T', (201, 203), 'VIII', sem8_rows['BP801T']),
    ('BP802T', (204, 205), 'VIII', sem8_rows['BP802T']),
    ('BP803T', (206, 208), 'VIII', sem8_rows['BP803T']),
    ('BP804T', (209, 210), 'VIII', sem8_rows['BP804T']),
    ('BP805T', (211, 213), 'VIII', sem8_rows['BP805T']),
    ('BP807P', (215, 216), 'VIII', sem8_rows['BP807P']),
    ('BP808P', (217, 218), 'VIII', sem8_rows['BP808P']),
]

# ---------------- field parsers ----------------
def grab(t, start_re, end_res):
    m = re.search(start_re, t)
    if not m:
        return ''
    end = len(t)
    for er in end_res:
        mm = re.search(er, t[m.end():])
        if mm:
            end = min(end, m.end() + mm.start())
    return t[m.end():end]

def numbered_items(block, maxn=15):
    """Split a block into sequentially numbered items 1..N (items may wrap lines)."""
    items = []
    flat = clean(block)
    n = 1
    while True:
        m = re.search(r'(?:^|\s)%d\.\s' % n, flat)
        if not m:
            break
        m2 = re.search(r'(?:^|\s)%d\.\s' % (n + 1), flat[m.end():])
        seg = flat[m.end():m.end() + m2.start()] if m2 else flat[m.end():]
        items.append(seg.strip())
        n += 1
        if n > maxn:
            break
    return items

ROMAN = re.compile(r'^\s*(I|II|III|IV|V|VI|VII|VIII)\s*$', re.M)

ROMAN_INLINE = re.compile(r'(?m)^\s*(VIII|VII|VI|V|IV|IX|III|II|I)\s*(?:$|\s(?=[A-Z("\u2018]))')

def parse_units(block, quirks):
    """Split detailed-syllabus block on Roman-numeral unit rows.
    Numerals print either alone on a line or inline with the unit title.
    Text printed before the first numeral (cell intro) is kept with unit1."""
    parts = []
    matches = list(ROMAN_INLINE.finditer(block))
    pre = block[:matches[0].start()] if matches else block
    for i, m in enumerate(matches):
        nxt = matches[i + 1].start() if i + 1 < len(matches) else len(block)
        parts.append((m.group(1), block[m.end():nxt]))
    units = {}
    for i, (rn, body) in enumerate(parts, start=1):
        b = clean(body)
        if i == 1:
            b = clean(pre) + ' ' + b
            stripped = re.sub(r'^(?:Unit No\.\s*)?Topics\s*No\. of Lectures\s*', '', b)
            if stripped != b:
                b = stripped
                quirks.append('Units table header row ("Unit No. / Topics / No. of Lectures") printed above unit I; stripped during transcription.')
        b = re.sub(r'^[-\u2013\u2014:\s]+', '', b)
        units['unit%d' % i] = b.strip()
    return units

def parse_card(code, pages_span, table_row):
    t = card_text(*pages_span)
    quirks = []
    is_lab = code.endswith('P') and not code.endswith('RP')
    is_project = code.endswith('RP')

    # --- header name ---
    hm = re.match(r'\s*%s\s*\n(.*?)\n\s*(Core|CORE|Elective|ELECTIVE)\s*\n' % code, t, re.S)
    name_print = clean(hm.group(1)) if hm else ''
    ctype = hm.group(2) if hm else ''

    # --- card mark table: Credit | Hours Per Week (L-T-P) | Max Hours -> 5 values ---
    dash = '--'
    l = tt = t_p = ''
    mm = re.search(r'Hours Per Week\s*\(?L-T-P\)?\*?\s*\n\s*Max\.?\s*Hours\.?\s*\n\s*L\s*\n\s*T\s*\n\s*P\s*\n\s*(\S+)\s*\n\s*(\S+)\s*\n\s*(\S+)\s*\n\s*(\S+)\s*\n\s*(\S+)', t)
    credit = ''
    if mm:
        credit, l, tt, t_p, _mh = mm.groups()
        credit = '' if credit == dash else credit
        l = '' if l == dash else l
        tt = '' if tt == dash else tt
        t_p = '' if t_p == dash else t_p
    mm2 = re.search(r'Maximum Marks\s*\n\s*SE\s*\n\s*ESE\s*\n\s*(\d+)\s*\n\s*(\d+)\s*\n\s*(\d+)', t)
    total_marks = se = ese = ''
    if mm2:
        total_marks, se, ese = mm2.groups()

    # --- objectives ---
    obj_raw = grab(t, r'COURSE OBJECTIVES:?', [r'Course Outcomes \(CO\):?', r'COURSE OUTCOMES \(CO\):?'])
    objectives = numbered_items(obj_raw)

    # --- COs ---
    co_raw = grab(t, r'Course Outcomes \(CO\):?|COURSE OUTCOMES \(CO\):?', [r'Detailed Syllabus', r'List of [Pp]ractical'])
    co_texts = []
    for m in re.finditer(r'^\s*([1-9])\s*$(.*?)(?=^\s*[1-9]\s*$|\Z)', co_raw, re.S | re.M):
        co_texts.append(clean(m.group(2)))

    # --- detailed syllabus / units / experiments ---
    units = {}
    experiments = []
    ds_raw = grab(t, r'Detailed Syllabus:?|Unit\s*\n?\s*No\.', [r'Recommended (References|Readings)', r'List of [Pp]racticals?'])
    if is_lab:
        exp_raw = grab(t, r'List of [Pp]racticals?[^\n]*', [r'Recommended References'])
        experiments = numbered_items(exp_raw)
    else:
        units = parse_units(ds_raw, quirks)

    # --- references -> textbooks (per task instruction) ---
    ref_raw = grab(t, r'Recommended (References|Readings)[^\n]*', [r'\Z'])
    textbooks = numbered_items(ref_raw)

    # --- scheme table mapping ---
    # columns: hours/wk(L/P) | Continuous Mode | Sessional Exam | Sessional Duration |
    #          Internal Total | End Sem Marks | Exam Duration | Total Marks | Credit
    s_ct = s_ta = s_tot = ese_t = t_marks = ''
    m9 = re.search(r'(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+([\d.]+\s*Hr)\s+(\d+)\s+(\d+)\s+([\d.]+\s*Hr)\s+(\d+)\s+(\d+)\s*$', table_row)
    if m9 and not is_project:
        _lp, s_ct, s_ta, _d1, s_tot, ese_t, _d2, t_marks, _cr = m9.groups()
    elif is_project:
        mp = re.search(r'(\d+)\s+4 Hr\s+(\d+)\s+(\d+)\s*$', table_row)
        if mp:
            ese_t, t_marks, _cr = mp.groups()

    L = l if not is_lab else ''
    Pv = t_p if is_lab else ''
    Tt = tt if not is_lab else ''

    pages = '%d-%d' % pages_span
    sp = {'scheme': '174' if pages_span[0] < 200 else '200',
          'detailed': pages, 'units': pages if not is_lab else '',
          'cos': pages, 'books': pages,
          'experiments': pages if is_lab else ''}

    notes = []
    if is_project:
        notes.append('Research project: card prints only scheme; content as printed is "Refer Section 21 of the Ordinance" / "Refer section 21 of regulation".')
    return {
        'subject_name': name_print, 'subject_name_print': name_print,
        'primary_code': code, 'all_codes': [code],
        'is_lab': is_lab,
        'scheme': {'L': L, 'T': Tt, 'P': Pv,
                   'credit': credit,
                   'sessional_ct': s_ct, 'sessional_ta': s_ta, 'sessional_total': s_tot or se,
                   'ese_te_pe': ese_t or ese, 'total_marks': t_marks or total_marks,
                   'scheme_line_print': table_row, 'sn': ''},
        'placement': {'semesters': [pages_span[0] < 200 and 'VII' or 'VIII'], 'branches_note': ''},
        'has_detailed_syllabus': bool(units or experiments),
        'prerequisites': '',
        'units': units,
        'lectures_per_unit': '',
        'co_count': len(co_texts), 'co_texts': co_texts, 'co_kls': [],
        'textbooks': textbooks, 'reference_books': [], 'experiments': experiments,
        'objectives': objectives,
        'source_pages': sp,
        'notes': notes, 'print_quirks': quirks, 'needs_review': False,
    }

# ---------------- init draft ----------------
draft = {
    'pdf_rel': PDF_REL, 'stem': STEM, 'session': SESSION, 'sha16': SHA16,
    'doc_meta': {'course': 'B.Pharm', 'program_year': '4', 'branches': [],
                 'effective_session': '2026-27', 'doc_kind': 'syllabus', 'segment': 'e',
                 'title_print': ''},
    'subjects': [], 'non_subject_rows': [],
    'doc_level_flags': [], 'doc_level_notes': [
        'Segment e covers Semesters VII+VIII only (parsed pages 174-221).',
        'Elective pool index (APPENDIX list of recommended electives) printed on pages 220-221; full elective cards start p222 (segment f).',
    ],
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(draft, open(OUT, 'w'), indent=1, ensure_ascii=False)

def append_subject(subj):
    dd = json.load(open(OUT))
    dd['subjects'].append(subj)
    json.dump(dd, open(OUT, 'w'), indent=1, ensure_ascii=False)

# ---------------- extract each subject (append after every subject) ----------------
for code, span, sem, trow in CARDS:
    s = parse_card(code, span, trow)
    if code == 'BP701T':
        s['print_quirks'].append('Decode artifacts on pp.176-177: Greek symbols (chi-square, rho, r) dropped by extraction, leaving "-efficient" fragments in units 3-4.')
    if code == 'BP703T':
        s['print_quirks'].append('Card prints "AI in Clinical applications (Theory)" (lowercase a); scheme table p.174 prints "AI in Clinical Applications (Theory)".')
        s['print_quirks'].append('Units table prints no "Detailed Syllabus" heading (starts directly with "Unit No. / Topics / No. of Lectures" on p.182); last unit hours marker truncated to "6 Ho" at page end (p.183).')
    if code == 'BP801T':
        s['print_quirks'].append('References section headed "Recommended Readings:" (variant of "Recommended References"); unit V hours marker prints bare "6" (word "hours" not visible in extraction, p.203).')
    if code in ('BP805T', 'BP808P'):
        s['print_quirks'].append('Card title prints "Sterile Dosage Form and Novel Drug Delivery System" (singular Form, no "and" after Form); scheme table p.200 prints "Sterile Dosage Forms and Novel Drug Delivery System".')
    if code == 'BP801T':
        s['print_quirks'].append('Units III and IV titles print doubled "AI in in Pharmacy Automation & Supply Chain" / "AI in in Public Health & Real-World Data Analytics" as printed.')
    if code == 'BP802T':
        s['print_quirks'].append('Printed unit numbering repeats "VII" twice (VII Diseases of bones and joints; VII Infectious Diseases) then jumps to IX; units transcribed as printed and indexed positionally unit1..unit9. Several unit numerals print inline with titles.')
    if code == 'BP710RP':
        s['print_quirks'].append('Card prints course type "CORE" (uppercase); Sem VII table prints "Core".')
        s['has_detailed_syllabus'] = False
    if code == 'BP810RP':
        pass
    append_subject(s)
    print('appended', code, 'units=%d cos=%d objs=%d books=%d exps=%d' % (
        len(s['units']), s['co_count'], len(s['objectives']), len(s['textbooks']), len(s['experiments'])))

# ---------------- BP810RP (scheme-table row only; no detailed card in range) ----------------
s810 = {
    'subject_name': 'Research Project', 'subject_name_print': 'Research Project',
    'primary_code': 'BP810RP', 'all_codes': ['BP810RP'], 'is_lab': False,
    'scheme': {'L': '', 'T': '', 'P': '', 'credit': '6', 'sessional_ct': '', 'sessional_ta': '',
               'sessional_total': '', 'ese_te_pe': '150', 'total_marks': '150',
               'scheme_line_print': sem8_rows['BP810RP'], 'sn': ''},
    'placement': {'semesters': ['VIII'], 'branches_note': ''},
    'has_detailed_syllabus': False, 'prerequisites': '',
    'units': {}, 'lectures_per_unit': '', 'co_count': 0, 'co_texts': [], 'co_kls': [],
    'textbooks': [], 'reference_books': [], 'experiments': [], 'objectives': [],
    'source_pages': {'scheme': '200', 'detailed': '', 'units': '', 'cos': '', 'books': '', 'experiments': ''},
    'notes': ['Research project: printed as "Refer Section 21 of the Ordinance"; no detailed card found within pages 174-221.'],
    'print_quirks': [], 'needs_review': True,
}
append_subject(s810)
print('appended BP810RP (scheme row only)')

# ---------------- non_subject_rows ----------------
def append_nsr(row):
    dd = json.load(open(OUT))
    dd['non_subject_rows'].append(row)
    json.dump(dd, open(OUT, 'w'), indent=1, ensure_ascii=False)

append_nsr({
    'row_kind': 'semester_summary',
    'payload': {'semester': 'VII', 'totals_print': 'Total 22 110 110 11 Hr 220 480 21 Hr 700 26',
                'columns_print': 'No. of hours per week (L/P) | Continuous Mode (Marks) | Sessional Exam (Marks) | Sessional Duration | Internal Total | End Semester Marks | Exam Duration | Total Marks | Credit Points'},
    'source_pages': '174', 'notes': ['Printed totals row of Semester VII scheme table.']})
append_nsr({
    'row_kind': 'semester_summary',
    'payload': {'semester': 'VIII', 'totals_print': 'Total 22 100 100 16 Hr 200 450 24 Hr 650 24',
                'columns_print': 'No. of hours per week (L/P | Continuous Mode (Marks) | Sessional Exam (Marks) | Sessional Duration | Internal Total | End Semester Marks | Exam Duration | Total Marks | Credit Points'},
    'source_pages': '200', 'notes': ['Printed totals row of Semester VIII scheme table; header prints "(L/P" without closing paren.']})

def pool(slot_code, slot_print, sem, elective_no, category, pool_page, members, extra_pages, slot_scheme_print):
    return {
        'row_kind': 'elective_pool',
        'payload': {'slot_code': slot_code, 'slot_print': slot_print, 'semester': sem,
                    'elective_no': elective_no, 'category': category,
                    'pool_page_scheme_print': slot_scheme_print,
                    'members': members},
        'source_pages': '%s,%s' % (slot_code and pool_page, extra_pages),
        'notes': ['Pool printed on dedicated slot page; full member syllabi in APPENDIX starting p.222 (segment f).']}

m708 = [
    {'code_print': 'BP708T AEC1', 'title_print': 'Current Good Manufacturing Practices (cGMP)'},
    {'code_print': 'BP708T AEC2', 'title_print': 'Pharmaceutical Automation'},
    {'code_print': 'BP708T AEC3', 'title_print': 'Modern Techniques in Cellular Biology'},
    {'code_print': 'BP708T AEC4', 'title_print': 'Medical Devices'},
    {'code_print': 'BP708T AEC5', 'title_print': 'Transformation of Food Waste into Medicinal Products'},
    {'code_print': 'BP708T AEC6', 'title_print': 'Biosimilars, Vaccines & Macromolecules'},
    {'code_print': 'BP708T AEC7', 'title_print': 'Precision Medicine'},
]
append_nsr({
    'row_kind': 'elective_pool',
    'payload': {'slot_code': 'BP708T', 'slot_print': 'BP708T AEC* \u2013 Elective 6 (Theory)', 'semester': 'VII',
                'elective_no': '6', 'category': 'AEC',
                'pool_page_scheme_print': 'Credit 1 | Hours Per Week (L-T-P): L 1, T --, P -- | Max. Hours 15 | Maximum Marks: SE 20, ESE 30, Total 50',
                'members': m708},
    'source_pages': '174,196,220-221',
    'notes': ['Slot row in Sem VII scheme table (p.174); pool list on p.196; also listed in APPENDIX index pp.220-221 where AEC1 title is split across the page break ("Current Good Manufacturing" / "Practices (cGMP)").',
              'Full member syllabi live in APPENDIX (segment f).']})

m806 = [
    {'code_print': 'BP806T AEC1', 'title_print': 'Pharmaceutical Packaging'},
    {'code_print': 'BP806T AEC2', 'title_print': 'Supply Chain Management'},
    {'code_print': 'BP806T AEC3', 'title_print': 'Industrial Safety and Waste Management'},
    {'code_print': 'BP806T AEC4', 'title_print': 'Traditional Healing Practices of India'},
    {'code_print': 'BP806T AEC5', 'title_print': 'Futuristic Pharma through AR/VR: Pharma 4.0'},
    {'code_print': 'BP806T AEC6', 'title_print': 'Herbal Cosmetics for Industry Perspective'},
]
append_nsr({
    'row_kind': 'elective_pool',
    'payload': {'slot_code': 'BP806T', 'slot_print': 'BP806T AEC* \u2013 Elective 7 (Theory)', 'semester': 'VIII',
                'elective_no': '7', 'category': 'AEC',
                'pool_page_scheme_print': 'Credit 2 | Hours Per Week (L-T-P): L 2, T --, P -- | Max. Hours 30 | Maximum Marks: SE 20, ESE 30, Total 50',
                'members': m806},
    'source_pages': '200,214,221',
    'notes': ['Slot row in Sem VIII scheme table (p.200); pool list on p.214; also listed in APPENDIX index p.221.',
              'Full member syllabi live in APPENDIX (segment f).']})

m809 = [
    {'code_print': 'BP809P VAC1', 'title_print': 'Cleaning Validation'},
    {'code_print': 'BP809P VAC2', 'title_print': 'Basic Training in Aseptic Handling Techniques'},
    {'code_print': 'BP809P VAC3', 'title_print': 'Impurity Profiling'},
]
append_nsr({
    'row_kind': 'elective_pool',
    'payload': {'slot_code': 'BP809P', 'slot_print': 'BP809P VAC* \u2013 Elective 8 (Practical)', 'semester': 'VIII',
                'elective_no': '8', 'category': 'VAC',
                'pool_page_scheme_print': 'Credit 1 | Hours Per Week (L-T-P): L --, T --, P 2 | Max. Hours 30 | Maximum Marks: SE 20, ESE 30, Total 50',
                'members': m809},
    'source_pages': '200,219,221',
    'notes': ['Slot row in Sem VIII scheme table (p.200); pool list on p.219; also listed in APPENDIX index p.221.',
              'Full member syllabi live in APPENDIX (segment f).']})

print('non_subject_rows appended:', len(json.load(open(OUT))['non_subject_rows']))
dd = json.load(open(OUT))
print('TOTAL subjects:', len(dd['subjects']))
for s in dd['subjects']:
    u = s['units']
    print(s['primary_code'], '| L=%s T=%s P=%s cr=%s ct=%s ta=%s tot=%s ese=%s tm=%s | units=%s cos=%d' % (
        s['scheme']['L'], s['scheme']['T'], s['scheme']['P'], s['scheme']['credit'],
        s['scheme']['sessional_ct'], s['scheme']['sessional_ta'], s['scheme']['sessional_total'],
        s['scheme']['ese_te_pe'], s['scheme']['total_marks'],
        ','.join(sorted(u.keys(), key=lambda x: int(x[4:]))), s['co_count']))
