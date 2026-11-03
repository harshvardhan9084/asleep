#!/usr/bin/env python3
"""B01-S05 extractor: 05_bpharm_scheme-syllabus_2026-27.draft.json (B.Pharm 2026-27, PCI).

Segments the fulltext into subject blocks (map verified page-by-page) and parses each
into the RULES.md §7 draft subject schema. Modes:
  python3 b01_s05_extract.py report   -> parse + print a per-subject report, NO writes
  python3 b01_s05_extract.py write    -> append subjects incrementally to DRAFT_OUT
"""
import json, re, sys

ROOT = '/home/z/my-project'
FT = f'{ROOT}/work/pipeline_v2/parsed/05_bpharm_scheme-syllabus_2026-27.fulltext.txt'
DRAFT = f'{ROOT}/work/pipeline_v2/drafts/05_bpharm_scheme-syllabus_2026-27.draft.json'

SCHEME_PAGES = {1: 6, 2: 34, 3: 65, 4: 94, 5: 120, 6: 149, 7: 174, 8: 200}
SLOT_PAGES = {'e1': 64, 'e2': 93, 'e3': 167, 'e4': 172, 'e5': 172, 'e6': 196, 'e7': 214, 'e8': 219}
MAIN_STARTS = [7,10,13,16,19,21,24,26,28,30,32, 35,38,41,44,47,51,54,56,58,60,62,
               66,69,71,73,76,79,82,84,87,89,91, 95,98,101,103,106,109,111,113,115,117,119,
               121,125,128,133,136,138,141,143,145, 150,153,156,158,161,164,168,170,173,
               175,179,181,184,186,189,193,197,199, 201,204,206,209,211,215,217]
TAIL_STARTS = [(222,'e1'),(224,'e1'),(226,'e1'),(228,'e2'),(230,'e2'),(232,'e2'),
               (234,'e3'),(236,'e3'),(239,'e3'),(241,'e3'),(243,'e3'),(245,'e3'),
               (247,'e4'),(250,'e4'),(252,'e4'),(254,'e5'),(256,'e5'),
               (258,'e6'),(260,'e6'),(263,'e6'),(265,'e6'),(268,'e6'),(270,'e6'),(272,'e6'),
               (274,'e7'),(276,'e7'),(279,'e7'),(281,'e7'),(284,'e7'),(287,'e7'),
               (290,'e8'),(292,'e8'),(294,'e8')]

raw_lines = open(FT, encoding='utf-8').read().split('\n')
page_start = {}
for i, l in enumerate(raw_lines):
    m = re.match(r'===== PAGE (\d+) =====', l)
    if m: page_start[int(m.group(1))] = i
PAGES = sorted(page_start)
def page_lines(p):
    i = PAGES.index(p)
    s = page_start[p] + 1
    e = page_start[PAGES[i+1]] if i + 1 < len(PAGES) else len(raw_lines)
    return raw_lines[s:e]
def page_of_lineidx(pages_used, local_idx):
    """map local line index inside concatenated block to pdf page"""
    acc = 0
    for p in pages_used:
        n = len(page_lines(p))
        if local_idx < acc + n:
            return p
        acc += n
    return pages_used[-1]

BOUNDARIES = sorted(set(MAIN_STARTS) | {p for p,_ in TAIL_STARTS} | set(SCHEME_PAGES.values())
                    | set(SUMMARY_PAGES := {64,93,167,172,196,214,219}) | {220})
def block_pages(s):
    i = BOUNDARIES.index(s)
    e = BOUNDARIES[i+1] - 1 if i + 1 < len(BOUNDARIES) else 295
    return s, e

def sem_of_page(p):
    for sem in range(1, 9):
        sp = SCHEME_PAGES[sem]
        np_ = SCHEME_PAGES.get(sem + 1, 10**9)
        if sp <= p < np_:
            return str(sem)
    return ''

ROMAN = {'I':1,'II':2,'III':3,'IV':4,'V':5}
TYPES = {'core','elective','internship'}
HOURS_RE = re.compile(r'^\s*(\d{1,2})\s*[Hh]ours?\.?\s*$')
BARE_RE = re.compile(r'^\s*(\d{1,2})\s*$')

def j(s): return re.sub(r'\s+', ' ', s).strip()

# ---------------- scheme table parsing ----------------
NUMTOK = re.compile(r'^(--|–|\d+(?:\.\d+)?)(?:\s*Hr)?$')
def parse_scheme_page(sem):
    p = SCHEME_PAGES[sem]
    lines = [l.strip() for l in page_lines(p)]
    rows, total_row = [], None
    idxs = [i for i, l in enumerate(lines) if re.match(r'^(BP\d{3}[A-Z]*(?:\s+(?:SEC|AEC|VAC)\*?)?)\s*(–|-|$)', l) or re.match(r'^BP\d{3}', l)]
    idxs = sorted(set(idxs))
    # Total row
    for i, l in enumerate(lines):
        if re.match(r'^Total\s*$', l):
            idxs.append(i)
            break
    idxs = sorted(set(idxs))
    for n, i in enumerate(idxs):
        end = idxs[n+1] if n+1 < len(idxs) else len(lines)
        seg = lines[i:end]
        code_m = re.match(r'^(BP\d{3}[A-Z]*(?:\s+(?:SEC|AEC|VAC)\*?)?)', seg[0])
        code = code_m.group(1) if code_m else 'Total'
        body = seg[:]
        toks = []
        for l in body:
            toks.extend(l.split())
        print_str = j(' '.join(seg))
        rows.append({'code': code, 'tokens': toks, 'print': print_str, 'start_line': i})
    return rows

def scheme_fields_from_tokens(code, toks):
    """Extract (h, cm, se, sd, it, esm, esed, total, credit) for normal rows."""
    nums, hrtoks = [], []
    cells = []
    for t in toks:
        cells.append(t)
    # walk: skip the code+title prefix = everything before the first pure number/hr token
    start = None
    for i, t in enumerate(cells):
        if re.match(r'^\d+(\.\d+)?$', t) or re.match(r'^\d+(\.\d+)?\s*Hr$', t):
            start = i
            break
    if start is None:
        return None
    rest = cells[start:]
    # expected: h cm se sd(it may be 'Hr' separate) it esm esed total credit
    def grab(i):
        # returns (value, next_i)
        if i >= len(rest): return None, i
        t = rest[i]
        if re.match(r'^\d+(\.\d+)?$', t):
            if i+1 < len(rest) and rest[i+1] == 'Hr':
                return t + ' Hr', i+2
            return t, i+1
        if re.match(r'^\d+(\.\d+)?Hr$', t):
            return t[:-2] + ' Hr', i+1
        return None, i
    vals, i = [], 0
    while i < len(rest) and len(vals) < 9:
        v, i = grab(i)
        if v is None:
            i += 1
            continue
        vals.append(v)
    if len(vals) < 9:
        return {'raw': vals}
    h, cm, se, sd, it, esm, esed, total, credit = vals
    return {'h': h, 'cm': cm, 'se': se, 'sd': sd, 'it': it, 'esm': esm, 'esed': esed,
            'total': total, 'credit': credit}

SPECIAL_SCHEME_ROWS = {
    'BP212P SEC*': {'h': '2', 'cm': '10', 'se': '10', 'sd': '3 Hr', 'it': '20', 'esm': '30', 'esed': '3 Hr', 'total': '50', 'credit': '1',
                    'print_full': 'BP212P SEC* \u2013 Elective 1 (Practical) 2 10 10 3 Hr 20 30 3 Hr 50 1'},
    'BP312P AEC*': {'h': '2', 'cm': '10', 'se': '10', 'sd': '3 Hr', 'it': '20', 'esm': '30', 'esed': '3 Hr', 'total': '50', 'credit': '1',
                    'print_full': 'BP312P AEC* \u2013 Elective 2 (Practical) 2 10 10 3 Hr 20 30 3 Hr 50 1'},
    'BP607T AEC*': {'h': '1', 'cm': '10', 'se': '10', 'sd': '1 Hr', 'it': '20', 'esm': '30', 'esed': '1.5 Hr', 'total': '50', 'credit': '1',
                    'print_full': 'BP607T AEC* \u2013 Elective 3 (Theory) 1 10 10 1 Hr 20 30 1.5 Hr 50 1'},
    'BP610P SEC*': {'h': '2', 'cm': '10', 'se': '10', 'sd': '3 Hr', 'it': '20', 'esm': '30', 'esed': '3 Hr', 'total': '50', 'credit': '1',
                    'print_full': 'BP610P SEC* \u2013 Elective 4 (Practical) 2 10 10 3 Hr 20 30 3 Hr 50 1'},
    'BP611P VAC*': {'h': '2', 'cm': '10', 'se': '10', 'sd': '3 Hr', 'it': '20', 'esm': '30', 'esed': '3 Hr', 'total': '50', 'credit': '1',
                    'print_full': 'BP611P VAC* \u2013 Elective 5 (Practical) 2 10 10 3 Hr 20 30 3 Hr 50 1'},
    'BP708T AEC*': {'h': '1', 'cm': '10', 'se': '10', 'sd': '1 Hr', 'it': '20', 'esm': '30', 'esed': '1.5 Hr', 'total': '50', 'credit': '1',
                    'print_full': 'BP708T AEC* \u2013 Elective 6 (Theory) 1 10 10 1 Hr 20 30 1.5 Hr 50 1'},
    'BP806T AEC*': {'h': '2', 'cm': '10', 'se': '10', 'sd': '1 Hr', 'it': '20', 'esm': '30', 'esed': '1.5 Hr', 'total': '50', 'credit': '2',
                    'print_full': 'BP806T AEC* \u2013 Elective 7 (Theory) 2 10 10 1 Hr 20 30 1.5 Hr 50 2'},
    'BP809P VAC*': {'h': '2', 'cm': '10', 'se': '10', 'sd': '3 Hr', 'it': '20', 'esm': '30', 'esed': '3 Hr', 'total': '50', 'credit': '1',
                    'print_full': 'BP809P VAC* \u2013 Elective 8 (Practical) 2 10 10 3 Hr 20 30 3 Hr 50 1'},

    'BP411I': {'h': '8', 'cm': 'Refer Section 22 of the ordinance', 'se': '', 'sd': '', 'it': '–',
               'esm': '100', 'esed': '4 Hr', 'total': '100', 'credit': '4'},
    'BP612I': {'h': '8', 'cm': 'Refer Section 22 of the ordinance', 'se': '', 'sd': '', 'it': '–',
               'esm': '100', 'esed': '4 Hr', 'total': '100', 'credit': '4'},
    'BP710RP': {'h': '–', 'cm': 'Refer Section 21 of the Ordinance', 'se': '', 'sd': '', 'it': '–',
                'esm': '150', 'esed': '4 Hr', 'total': '150', 'credit': '6'},
    'BP810RP': {'h': '–', 'cm': 'Refer Section 21 of the Ordinance', 'se': '', 'sd': '', 'it': '–',
                'esm': '150', 'esed': '4 Hr', 'total': '150', 'credit': '6'},
}

# ---------------- detail block parsing ----------------
CODE_RE = re.compile(r'^BP\d{3}[A-Z]*(?:\s+(?:SEC|AEC|VAC)\d)?$')
def parse_header(lines):
    li = next(i for i, l in enumerate(lines) if 'Course Code' in l)
    rest = [l.strip() for l in lines[li+1:]]
    base = li + 1
    code_parts, k = [], 0
    while k < len(rest):
        t = rest[k]
        if CODE_RE.match(t):
            code_parts.append(t); k += 1
        elif code_parts:
            break
        else:
            k += 1
    code = ' '.join(code_parts)
    title_lines, ctype = [], ''
    while k < len(rest):
        t = rest[k]
        if t.lower() in TYPES and title_lines:
            ctype = t; k += 1; break
        title_lines.append(t); k += 1
    labels = []
    while k < len(rest):
        t = rest[k]
        if re.match(r'^(Credit|Hours Per Week \(L-T-P\)\*?|Max\.?\s*Hours\.?)$', t) or t in ('L','T','P'):
            labels.append(t); k += 1
        elif t == '':
            k += 1
        else:
            break
    vals = []
    while k < len(rest):
        t = rest[k]
        if re.match(r'^(--|–|-|00|\d{1,3})$', t):
            vals.append(t); k += 1
        else:
            break
    has_mh = any(l.startswith('Max') for l in labels)
    sc = {'credit':'','L':'','T':'','P':'','max_hours':'','se_total':'','ese_internal':'','ese_endsem':''}
    if len(vals) >= 4:
        sc['credit'], sc['L'], sc['T'], sc['P'] = vals[0], vals[1], vals[2], vals[3]
        if has_mh and len(vals) >= 5:
            sc['max_hours'] = vals[4]
    elif vals:
        sc['credit'] = vals[0]
    mm = [x for x in rest[k:] if x][:8]
    if mm and mm[0] == 'Maximum Marks':
        nums = [x for x in mm[1:] if re.match(r'^(--|–|00|\d{1,3})$', x)]
        if len(nums) >= 3:
            sc['se_total'], sc['ese_internal'], sc['ese_endsem'] = nums[0], nums[1], nums[2]
    return code, j(' '.join(title_lines)), ctype, sc

def find_marker(lines, pat, start=0):
    for i in range(start, len(lines)):
        if re.match(pat, lines[i].strip(), re.I):
            return i
    return None

def parse_objectives(lines, start_after):
    objs, cur, i = [], None, start_after
    while i < len(lines):
        t = lines[i].strip()
        if re.match(r'^\d+\.\s*$', t) or re.match(r'^\d+\.\s+\S', t):
            if cur is not None: objs.append(cur)
            cur = re.sub(r'^\d+\.\s*', '', t)
        elif re.match(r'(?i)^\s*course outcomes', t):
            break
        elif cur is not None and t:
            cur += ' ' + t
        i += 1
    if cur is not None: objs.append(cur)
    return [j(o) for o in objs]

def parse_cos(lines, start_after):
    cos, cur, i = [], None, start_after
    while i < len(lines):
        t = lines[i].strip()
        if re.match(r'(?i)^\s*detailed syllabus', t):
            break
        mco = re.match(r'^CO(\d{1,2})$', t)
        done = len(cos) + (1 if cur is not None else 0)
        if (mco and int(mco.group(1)) == done + 1) or (BARE_RE.match(t) and int(t) == done + 1):
            if cur is not None: cos.append(cur)
            cur = ''
        elif cur is not None and t and not re.match(r'(?i)^(upon successful|co\s*no)', t) and t not in ('CO','No.'):
            cur = j(cur + ' ' + t)
        i += 1
    if cur is not None: cos.append(cur)
    return cos

def parse_units(lines, ds_i, books_i):
    units, hrs = {}, {}
    i = ds_i + 1
    while i < books_i:
        t = lines[i].strip()
        if t == '' or (len(t) < 40 and re.match(r'(?i)^(unit no\.?.*|topics( no.*)?|no\.? of lectures?|lectures)$', t)):
            i += 1; continue
        break
    cur_n, cur_l = None, []
    def flush():
        nonlocal cur_n, cur_l
        if cur_n is None: return
        txt, u_h = [], None
        for jj, t in enumerate(cur_l):
            mh = HOURS_RE.match(t)
            if mh:
                u_h = int(mh.group(1)); continue
            if BARE_RE.match(t) and (jj == len(cur_l)-1 or HOURS_RE.match(cur_l[jj+1].strip())):
                u_h = int(t); continue
            txt.append(t)
        if txt and BARE_RE.match(txt[-1]) and u_h is None:
            u_h = int(txt[-1]); txt = txt[:-1]
        units[cur_n] = j(' '.join(txt))
        if u_h is not None: hrs[cur_n] = u_h
    while i < books_i:
        t = lines[i].strip()
        m1 = re.match(r'^(I|II|III|IV|V)$', t)
        m2 = re.match(r'^(I|II|III|IV|V)\s+(\S.*)$', t)
        nxt = (ROMAN.get(cur_n, 0) + 1) if cur_n else 1
        if m1 and ROMAN[t] == nxt:
            flush(); cur_n, cur_l = t, []
        elif m2 and ROMAN[m2.group(1)] == nxt:
            flush(); cur_n, cur_l = m2.group(1), [m2.group(2)]
        elif cur_n is not None and t:
            cur_l.append(t)
        i += 1
    flush()
    return units, hrs

def parse_numbered(lines, start_i, stop_i):
    items, cur = [], None
    for i in range(start_i, stop_i):
        t = lines[i].strip()
        m = re.match(r'^(\d{1,2})\.\s*(.*)$', t)
        if m:
            if cur is not None: items.append(cur)
            cur = m.group(2)
        elif cur is not None and t:
            cur = j(cur + ' ' + t)
    if cur is not None: items.append(cur)
    return [j(x) for x in items]

def parse_block(start):
    s, e = block_pages(start)
    pgs = list(range(s, e+1))
    lines, pagemap = [], []
    for p in pgs:
        seg = page_lines(p)
        # strip running-header furniture: 'B. Pharm. Syllabus' anywhere; the printed
        # page number (= pdf page - 5) only when it sits in the first 4 lines of the page
        for li, l in enumerate(seg):
            t = l.strip()
            if t == 'B. Pharm. Syllabus':
                continue
            if li < 4 and t and t.isdigit() and int(t) == p - 5:
                continue
            lines.append(l)
            pagemap.append(p)
    return {'pages': pgs, 'lines': lines, 'pagemap': pagemap}

def parse_subject(start, slot=None, slot_line=''):
    blk = parse_block(start)
    pgs, lines = blk['pages'], blk['lines']
    pagemap = blk['pagemap']
    code, title, ctype, sc = parse_header(lines)
    sem = sem_of_page(start)
    base_code = code.split()[0]
    lab = (base_code.endswith('P') and not base_code.endswith('RP')) or '(Practical)' in title
    internship = base_code.endswith('I') or ctype.lower() == 'internship'
    rp = base_code.endswith('RP')
    subj = {
        'subject_name': re.sub(r'\s*\(Theory\)|\s*\(Practical\)', '', title).strip(),
        'subject_name_print': title,
        'primary_code': code,
        'all_codes': [code],
        'is_lab': bool(lab),
        'scheme': {'L':'','T':'','P':'','credit': sc['credit'],
                   'sessional_ct':'','sessional_ta':'','sessional_total':'',
                   'ese_te_pe':'','total_marks':'','scheme_line_print': slot_line, 'sn': ''},
        'placement': {'semesters': [sem], 'branches_note': ''},
        'has_detailed_syllabus': True,
        'prerequisites': '',
        'units': {'unit1':'','unit2':'','unit3':'','unit4':'','unit5':''},
        'lectures_per_unit': '',
        'co_count': 0, 'co_texts': [], 'co_kls': [],
        'textbooks': [], 'reference_books': [], 'experiments': [],
        'objectives': [],
        'source_pages': {'scheme': str(SCHEME_PAGES[int(sem)]),
                         'detailed': f'pp.{pgs[0]}-{pgs[-1]}' if len(pgs) > 1 else f'p.{pgs[0]}',
                         'units':'','cos':'','books':'','experiments':''},
        'notes': [], 'print_quirks': [], 'needs_review': False,
    }
    if lab: subj['scheme']['P'] = sc['P']
    elif internship or rp:
        subj['scheme']['P'] = sc['P'] if sc['P'] not in ('--','–') else ''
        subj['scheme']['L'] = sc['L'] if sc['L'] not in ('--','–') else ''
    else: subj['scheme']['L'] = sc['L']
    # detail header corroboration
    if sc['se_total']:
        subj['notes'].append(f"Detail header prints: Maximum Marks SE {sc['se_total']}, ESE {sc['ese_internal']}/{sc['ese_endsem']} (internal/end-sem split).")
    if sc['max_hours']:
        subj['notes'].append(f"Detail header Max. Hours: {sc['max_hours']}.")
    if slot:
        subj['notes'].append(f"Elective option under slot line '{slot_line.split(chr(9733))[0].strip() if chr(9733) in slot_line else slot_line[:40]}'; base code {base_code} is shared by all options of this elective slot (appendix list of electives pp.220-221).")
    if not (sc['se_total'] or sc['credit']):
        subj['needs_review'] = True
    # sections
    obj_i = find_marker(lines, r'^course objectives')
    co_i = find_marker(lines, r'^course outcomes')
    ds_i = find_marker(lines, r'^detailed syllabus')
    prac_i = find_marker(lines, r'^list of practic')
    books_i = find_marker(lines, r'^recommended (references|readings)')
    def pg(idx):
        return pagemap[idx] if 0 <= idx < len(pagemap) else pgs[-1]
    if obj_i is not None:
        subj['objectives'] = parse_objectives(lines, obj_i + 1)
        if co_i is not None:
            subj['source_pages']['cos'] = f"pp.{pg(obj_i)}-{pg(co_i)}" if pg(obj_i) != pg(co_i) else f"p.{pg(obj_i)}"
    if co_i is not None:
        start = co_i + 1
        cos = parse_cos(lines, start)
        subj['co_texts'] = cos
        subj['co_count'] = len(cos)
    if ds_i is not None:
        u_page = pg(ds_i)
        if books_i is not None:
            subj['source_pages']['units'] = f"pp.{u_page}-{pg(books_i)}"
            subj['source_pages']['books'] = f"pp.{pg(books_i)}-{pgs[-1]}"
        else:
            subj['source_pages']['units'] = f"pp.{u_page}-{pgs[-1]}"
    if lab:
        if prac_i is not None:
            stop = books_i if books_i is not None else len(lines)
            seg = lines[prac_i:stop]
            m = re.search(r'\((Perform any\s*\d+\s*Experiments?[^)]*|Minimum\s*\d+\s*experiments?[^)]*)\)', j(' '.join(seg)), re.I)
            if m: subj['notes'].insert(0, f"Printed instruction: ({j(m.group(1))}).")
            item_start = prac_i + 1
            note_i = None
            for ii in range(item_start, stop):
                if re.match(r'^Notes?\b\.?:?$', lines[ii].strip()):
                    note_i = ii
                    break
            if note_i is not None:
                stop_eff = note_i
                note_txt = j(' '.join(x.strip() for x in lines[note_i+1:stop] if x.strip()))
                if note_txt:
                    subj['notes'].append(f"Printed Note: {note_txt}")
            else:
                stop_eff = stop
            items = parse_numbered(lines, item_start, stop_eff)
            if m:
                items = [it for it in items if not re.match(r'(?i)^perform any', it)]
            subj['experiments'] = items
            if ds_i is not None and books_i is not None:
                subj['source_pages']['experiments'] = f"pp.{pg(prac_i)}-{pg(books_i)}"
    else:
        if ds_i is not None and books_i is not None:
            units, hrs = parse_units(lines, ds_i, books_i)
            for n in range(1, 6):
                rk = {1:'I',2:'II',3:'III',4:'IV',5:'V'}.get(n)
                subj['units'][f'unit{n}'] = units.get(rk, '')
            if hrs:
                if len(set(hrs.values())) == 1:
                    subj['lectures_per_unit'] = f"{list(hrs.values())[0]} hours per unit"
                else:
                    subj['lectures_per_unit'] = '; '.join(f"{k}: {v} hours" for k, v in hrs.items())
    if books_i is not None:
        books = parse_numbered(lines, books_i + 1, len(lines))
        subj['reference_books'] = books
    if not subj['units']['unit1'] and not subj['experiments'] and not internship and not rp:
        subj['has_detailed_syllabus'] = False
    return subj

# ---------------- scheme rows / summaries / pools ----------------
def load_scheme_rows():
    out = {}
    for sem in range(1, 9):
        rows = parse_scheme_page(sem)
        d = {}
        for r in rows:
            c = r['code'].strip()
            if c == 'Total':
                d['__total__'] = r
                continue
            base = re.match(r'^(BP\d{3}[A-Z]*)', c).group(1)
            if base in SPECIAL_SCHEME_ROWS:
                f = dict(SPECIAL_SCHEME_ROWS[base]); f['print'] = r['print']; f['sn'] = ''
                d[c] = f
            else:
                f = scheme_fields_from_tokens(c, r['tokens']) or {}
                f['print'] = r['print']
                d[c] = f
        out[sem] = d
    return out

def parse_summary_page(slot_pages):
    """pool member lists from slot summary pages {slot: page}; a page may hold
    several consecutive tables (each starts at a 'Course Code' line)."""
    pools = {}
    tables_by_page = {}
    for slot, p in sorted(slot_pages.items(), key=lambda kv: kv[1]):
        if p in tables_by_page:
            continue
        lines = [l.strip() for l in page_lines(p)]
        starts = [i for i, l in enumerate(lines) if 'Course Code' in l]
        tables = []
        for n, s0 in enumerate(starts):
            end = starts[n+1] if n+1 < len(starts) else len(lines)
            members, cur = [], None
            for l in lines[s0:end]:
                if re.match(r'^Credit', l):
                    if cur: members.append(cur); cur = None
                    break
                m = re.match(r'^(BP\d{3})\s*((?:SEC|AEC|VAC)\d?)$', l)
                if m:
                    if cur: members.append(cur)
                    cur = {'code': (m.group(1) + ' ' + m.group(2)).strip(), 'name': ''}
                    continue
                if l == 'Elective':
                    continue
                if l.startswith('BP'):
                    m2 = re.match(r'^(BP\d{3}[A-Z]*(?:\s+(?:SEC|AEC|VAC)\d)?)\s*(.*)$', l)
                    if m2:
                        if cur: members.append(cur)
                        cur = {'code': m2.group(1), 'name': m2.group(2)}
                        continue
                if cur is not None and l:
                    cur['name'] = j(cur['name'] + ' ' + l)
            if cur: members.append(cur)
            tables.append(members)
        tables_by_page[p] = tables
    # assign slots in printed page order
    order = sorted(slot_pages.items(), key=lambda kv: (kv[1], kv[0]))
    for slot, p in order:
        t = tables_by_page[p]
        pools[slot] = t.pop(0) if t else []
    return pools

def main(mode):
    sr = load_scheme_rows()
    pools = parse_summary_page(SLOT_PAGES)
    if mode == 'report':
        print('=== SCHEME ROWS ===')
        for sem in range(1, 9):
            for c, f in sr[sem].items():
                if c == '__total__':
                    print(f'S{sem} TOTAL: {f["print"][:120]}')
                else:
                    print(f'S{sem} {c}: h={f.get("h")} cm={f.get("cm")} se={f.get("se")} it={f.get("it")} esm={f.get("esm")} tot={f.get("total")} cr={f.get("credit")}')
        print('=== POOLS ===')
        for s, m in pools.items():
            print(s, [f"{x['code']} {x['name']}" for x in m])
        print('=== SUBJECTS (report only) ===')
        for start in MAIN_STARTS:
            s = parse_subject(start)
            flag = 'LAB' if s['is_lab'] else ('INT' if s['primary_code'].endswith('I') else ('RP' if s['primary_code'].endswith('RP') else 'TH '))
            print(f"{start:>3} {flag} {s['primary_code']:<14} {s['subject_name'][:52]:<52} obj={len(s['objectives'])} co={s['co_count']} u1={'Y' if s['units']['unit1'] else '-'} exp={len(s['experiments'])} books={len(s['reference_books'])} lpu={s['lectures_per_unit'][:24]}")
        for start, slot in TAIL_STARTS:
            s = parse_subject(start, slot)
            flag = 'LAB' if s['is_lab'] else 'TH '
            print(f"{start:>3} {flag} {s['primary_code']:<14} {s['subject_name'][:52]:<52} obj={len(s['objectives'])} co={s['co_count']} u1={'Y' if s['units']['unit1'] else '-'} exp={len(s['experiments'])} books={len(s['reference_books'])} lpu={s['lectures_per_unit'][:24]}")
        return

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'report')
