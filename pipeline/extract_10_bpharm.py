#!/usr/bin/env python3
"""Task 10 batch03: BPharm y1-4 2019-20 verbatim syllabus extraction.
RULES.md §6/§7/§8 compliant. Appends each subject to DRAFT_OUT incrementally.
Zero guessing: only printed text is transcribed; blanks stay blank.
"""
import json, re, os, sys

PARSE = '/home/z/my-project/work/pipeline_v2/parsed/10_bpharm_y1-4_syllabus_2019-20.json'
DRAFT_OUT = '/home/z/my-project/work/pipeline_v2/drafts/10_bpharm_y1-4_syllabus_2019-20.draft.json'
PDF_REL = 'repo_asleep/PDFs/5-course/2019-20/bpharm_y1-4_syllabus_2019-20.pdf'
SESSION = '2019-20'
SHA16 = '28cd10357b812c41'
STEM = '10_bpharm_y1-4_syllabus_2019-20'
COURSE = 'BPharm'

HEADER = 'Evaluation Scheme Bachelor of Pharmacy I, II, III & IV Year syllabus 2019-2020'
CODE_RE = r'(?:BP\d{3}[A-Z]{0,3}|KVE301)'
HEAD_RE = re.compile(r'^\s*(' + CODE_RE + r')\.\s*(.*)$')

def norm(s):
    """Normalize extraction whitespace only; words/punctuation/casing verbatim."""
    return re.sub(r'\s+', ' ', s.replace('\x0c', ' ')).strip()

def load_pages():
    d = json.load(open(PARSE))
    pages = {}
    for p in d['pages']:
        lines = []
        for ln in p['text'].split('\n'):
            s = ln.replace('\x0c', '').rstrip()
            st = s.strip()
            if not st:
                continue
            if st == HEADER:
                continue
            if re.match(r'^Page \d+$', st):
                continue
            lines.append(s)
        pages[p['no']] = lines  # p['no'] is 1-based page number? verify below
    return d, pages

# ---- unit / numbering helpers ----
ROMAN = {'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7,'VIII':8,'IX':9,'X':10}
UNIT_RE = re.compile(r'(?i)^\s*unit\s*[-–]?\s*([0-9]+|[ivx]+)\b(.*)$')

def unit_no(tok):
    t = tok.strip().upper()
    if t.isdigit():
        return int(t)
    return ROMAN.get(t)

def main():
    d, pages = load_pages()
    if pages.get(1) is None or 'no' not in d['pages'][0]:
        pass
    # verify page numbering basis: use enumerate order as page number if 'no' mismatch
    # (parsed pages have 'no' field; trust enumerate to be safe)
    pages = {}
    for idx, p in enumerate(d['pages'], start=1):
        lines = []
        for ln in p['text'].split('\n'):
            s = ln.replace('\x0c', '').rstrip()
            st = s.strip()
            if not st:
                continue
            if st == HEADER:
                continue
            if re.match(r'^Page \d+$', st):
                continue
            lines.append(s)
        pages[idx] = lines

    # ---------- scheme table rows (pages 2..9) ----------
    SEM_OF_PAGE = {2:1,3:2,4:3,5:4,6:5,7:6,8:7,9:8}
    scheme = {}          # code -> dict
    scheme_rows_raw = {} # page -> list of row strings (verbatim)
    rowstart_re = re.compile(r'^\s*(' + CODE_RE + r'(?:\s+' + CODE_RE + r')*)\s*(.*)$')
    for pg, sem in SEM_OF_PAGE.items():
        lines = pages[pg]
        starts = []
        for i, ln in enumerate(lines):
            m = rowstart_re.match(ln)
            if m and m.group(1):
                toks = m.group(1).split()
                ok = all(re.fullmatch(CODE_RE, t) for t in toks)
                rest = m.group(2).strip()
                if ok and (rest == '' or not re.match(r'^[\d\-–—.\s]', rest)):
                    starts.append((i, toks))
        # merge consecutive code-only lines (e.g. shared "BP106RBT BP106RMT" row)
        merged = []
        k2 = 0
        while k2 < len(starts):
            grp_i, grp_toks = starts[k2]
            def _rest_empty(idx):
                ln2 = lines[starts[idx][0]]
                m2 = rowstart_re.match(ln2)
                return m2 is not None and m2.group(2).strip() == ''
            while k2+1 < len(starts) and starts[k2+1][0] == grp_i + len(grp_toks) and _rest_empty(k2+1):
                k2 += 1
                grp_toks = grp_toks + starts[k2][1]
            merged.append((grp_i, grp_toks))
            k2 += 1
        starts = merged
        for j, (i, toks) in enumerate(starts):
            end = starts[j+1][0] if j+1 < len(starts) else len(lines)
            # stop at 'Total' line
            seg = lines[i:end]
            cut = len(seg)
            is_sem8_et = any(re.fullmatch(r'BP8(?:0[3-9]|1[0-4])ET', t) for t in toks)
            for k, ln in enumerate(seg):
                if re.match(r'^\s*Total\b', ln, re.I):
                    cut = k
                    break
                if is_sem8_et and k > 0 and re.search(r'\d+\s*\+\s*\d+', ln):
                    cut = k
                    break
            seg = seg[:cut]
            joined = norm(' '.join(seg))
            for code in toks:
                scheme[code] = {'sem': sem, 'row': joined, 'page': pg}
        scheme_rows_raw[pg] = None

    # --- §6 print-quirk recovery (p.9): PyMuPDF silently drops the wrapped second-line
    # fragments of two scheme cells. pdftotext -bbox confirms visible print:
    #   "Design*"       y=275 x=147  -> second line of BP807ET cell (first line y=262)
    #   "Pharmacology*" y=318 x=147  -> second line of BP810ET cell (first line y=305)
    scheme['BP807ET']['row'] = 'BP807ET Computer Aided Drug Design*'
    scheme['BP810ET']['row'] = 'BP810ET Experimental Pharmacology*'

    def row_body(code):
        r = scheme.get(code, {}).get('row', '')
        toks = r.split()
        z = 0
        while z < len(toks) and re.fullmatch(CODE_RE, toks[z]):
            z += 1
        return norm(' '.join(toks[z:])), ' '.join(toks[:z])

    def row_name(code):
        rest, _lead = row_body(code)
        if not rest:
            return ''
        # name = leading tokens until first pure number / dash token
        out = []
        for tok in rest.split():
            if tok == '---' or re.fullmatch(r'\d+(?:\.\d+)?', tok):
                break
            out.append(tok)
        return norm(' '.join(out))

    def row_tail(code):
        rest, _lead = row_body(code)
        nm = row_name(code)
        return norm(rest[len(nm):]) if rest.lower().startswith(nm.lower()) else rest

    def row_credit(code):
        tail = row_tail(code).split()
        if tail and re.fullmatch(r'[1-8]', tail[-1]):
            return int(tail[-1])
        return None

    def row_hours(code):
        tail = row_tail(code).split()
        if tail and re.fullmatch(r'\d+', tail[0]):
            return tail[0]
        return None

    # ---------- headings / regions ----------
    subs = []  # (code, namepart, page, lineidx)
    for pg in range(10, max(pages)+1):
        for i, ln in enumerate(pages[pg]):
            m = HEAD_RE.match(ln)
            if m:
                subs.append((m.group(1), m.group(2), pg, i))
    print(f'headings found: {len(subs)}')

    def region_lines(si):
        code, namepart, pg, i = subs[si]
        lines = []
        if si+1 < len(subs):
            _, _, npg, ni = subs[si+1]
        else:
            npg, ni = max(pages)+1, 0
        # same page remainder, then full pages, then head of next-heading page
        lines += pages[pg][i+1:]
        for p2 in range(pg+1, npg):
            lines += pages[p2]
        if npg > pg and npg in pages:
            lines += pages[npg][:ni]
        elif npg == pg:
            lines = pages[pg][i+1:ni]
        return lines

    ROMAN_SEQ = ['I','II','III','IV','V','VI','VII','VIII','IX','X','XI','XII']
    ROMAN_ITEM = re.compile(r'^\s*([IVX]{1,4})\s*\.(?![a-zA-Z])\s*(.*)$')
    ROMAN_ITEM_SP = re.compile(r'^\s*([IVX]{1,4})\s{2,}(\S.*)$')
    HRS_LINE = re.compile(r'^\s*(\d{1,2}\s*Hours?)\s*$', re.I)
    COURSE_CONTENT = re.compile(r'(?i)^\s*course\s*content\s*:\s*$')

    def parse_subject(si):
        code, namepart, pg, i = subs[si]
        head_line = pages[pg][i]
        name_print = norm(head_line)
        lines = region_lines(si)
        # heading may wrap: a bare "(Theory)"/"(Practical)" line belongs to the heading
        if lines and re.match(r'^\s*\((?:Theory|THEORY|Practical|PRACTICAL)\)\s*$', lines[0]):
            name_print = norm(name_print + ' ' + lines[0].strip())
            lines = lines[1:]
        # hours: trailing on heading or first line(s)
        hours_print = ''
        m = re.search(r'(\d+\s*Hours(?:\s*/\s*weeks?)?)\s*$', name_print, re.I)
        if m:
            hours_print = norm(m.group(1))
            name_print = norm(name_print[:m.start()])
        elif lines:
            m2 = re.match(r'^\s*(\d+\s*Hours(?:\s*/\s*weeks?)?)\s*$', lines[0], re.I)
            if m2:
                hours_print = norm(m2.group(1))
                lines = lines[1:]
        # name: strip "(Theory)"/"(Practical)"/"(THEORY)" suffix
        nm = name_print.split('. ', 1)[1] if '. ' in name_print else name_print
        nm = re.sub(r'\s*\((?:Theory|THEORY|Practical|PRACTICAL)\)\s*$', '', nm).strip()
        suffix = ''
        ms = re.search(r'\((Theory|THEORY|Practical|PRACTICAL)\)', name_print)
        if ms:
            suffix = ms.group(1).lower()
        if code == 'KVE301':
            suffix = 'theory'

        # locate books / journals headings
        book_idx = None
        for k, ln in enumerate(lines):
            if re.match(r'(?i)^\s*recommended\s*books?\b', ln):
                book_idx = k
                break
        content = lines[:book_idx] if book_idx is not None else lines
        books = []
        journals = []
        books_head = ''
        journals_head = ''
        if book_idx is not None:
            books_head = norm(lines[book_idx])
            mode = 'books'
            for ln in lines[book_idx+1:]:
                st = ln.strip()
                if re.match(r'(?i)^\s*recommended\s*journals?\b', ln):
                    mode = 'journals'
                    journals_head = norm(ln)
                    continue
                if re.match(r'(?i)^\s*recommended\s*books?\b', ln):
                    mode = 'books'
                    continue
                if re.match(r'^\s*[\u2022\u00b7]\s*', ln):
                    tgt = books if mode == 'books' else journals
                    tgt.append(norm(re.sub(r'^\s*[\u2022\u00b7]\s*', '', ln)))
                elif st:
                    tgt = books if mode == 'books' else journals
                    if tgt:
                        tgt[-1] = norm(tgt[-1] + ' ' + st)
                    else:
                        tgt.append(norm(st))

        # split content into unit blocks / unmarked blocks
        unit_starts = []
        for k, ln in enumerate(content):
            mu = UNIT_RE.match(ln)
            if mu and unit_no(mu.group(1)) is not None:
                unit_starts.append((k, unit_no(mu.group(1))))
        units = {}
        unmarked_blocks = []
        if unit_starts:
            pre_end = unit_starts[0][0]
            blocks = []
            for jx,(k,uno) in enumerate(unit_starts):
                end = unit_starts[jx+1][0] if jx+1 < len(unit_starts) else len(content)
                seg = content[k:end]
                blocks.append((str(uno), seg))
            # unmarked trailing blocks: standalone Hours-annotation line after content inside a unit block
            for key, seg in blocks:
                cut = None
                seen_content = False
                for z, ln in enumerate(seg):
                    st = ln.strip()
                    if not st:
                        continue
                    if z == 0:
                        continue  # unit marker line itself
                    if HRS_LINE.match(st) and not seen_content:
                        continue  # hour annotation belonging to the marker header
                    if HRS_LINE.match(st) and seen_content:
                        cut = z
                        break
                    seen_content = True
                if cut is not None:
                    units[key] = norm(' '.join(seg[:cut]))
                    unmarked_blocks.append({'after_unit': key, 'print': norm(' '.join(seg[cut:]))})
                else:
                    units[key] = norm(' '.join(seg))
            # consecutive duplicates (unmarked block inside last unit handled above)
            pre = content[:pre_end]
        else:
            pre = content

        # experiments from pre (practicals list items before books)
        experiments = []
        exp_no = None
        exp_label = None
        exp_text = []
        exp_seq = [0]
        def flush_exp():
            nonlocal exp_no, exp_text, exp_label
            if exp_no is not None:
                exp_seq[0] += 1
                experiments.append({'no': exp_seq[0], 'label_print': str(exp_label), 'exp': norm(' '.join(exp_text))})
                exp_no = None
                exp_label = None
                exp_text = []
        for ln in pre:
            st = ln.strip()
            ma = re.match(r'^(\d+)[.)]\s*(.*)$', st)
            mr1 = ROMAN_ITEM.match(st)
            mr2 = ROMAN_ITEM_SP.match(st) if not mr1 else None
            if ma:
                flush_exp()
                exp_no = ma.group(1); exp_label = ma.group(1); exp_text = [ma.group(2)]
            elif mr1 and not exp_text_join_guard(exp_text, mr1):
                flush_exp()
                exp_no = mr1.group(1); exp_label = mr1.group(1); exp_text = ([mr1.group(2)] if mr1.group(2) else [])
            elif mr2 and not exp_text_join_guard(exp_text, mr2):
                flush_exp()
                exp_no = mr2.group(1); exp_label = mr2.group(1); exp_text = [mr2.group(2)]
            elif exp_no is not None and st:
                exp_text.append(st)
        flush_exp()

        # preamble text (non-experiment lines)
        pre_lines = []
        seen_num = False
        for ln in pre:
            st = ln.strip()
            if re.match(r'^(\d+)[.)]\s*', st):
                seen_num = True
                continue
            if ROMAN_ITEM.match(st) or ROMAN_ITEM_SP.match(st):
                seen_num = True
                continue
            if COURSE_CONTENT.match(st):
                continue
            if not st:
                continue
            if seen_num:
                continue  # continuation of an experiment
            pre_lines.append(norm(st))
        preamble = ' '.join(pre_lines)
        content_raw_print = norm(' '.join(lines))

        # subject_type
        if code.endswith('PW'):
            stype = 'project'
        elif code.endswith('PS'):
            stype = 'practice-school'
        elif code in ('BP509P','BP610P','BP707P','BP816P'):
            stype = 'training-report'
        elif code in ('BP106RBT',):
            stype = 'remedial-theory'
        elif code in ('BP112RBP',):
            stype = 'remedial-practical'
        elif code.endswith('ET'):
            stype = 'elective'
        elif suffix == 'practical':
            stype = 'practical'
        else:
            stype = 'theory'

        sem = scheme.get(code, {}).get('sem')
        if sem is None:
            msem = re.match(r'^BP([1-8])\d\d', code)
            sem = int(msem.group(1)) if msem else None

        codes = [code]
        quirks = []
        flags = []
        if code == 'BP106RBT':
            codes = ['BP106RBT', 'BP106RMT']
            quirks.append('Scheme row prints shared row "BP106RBT BP106RMT Remedial Biology/ Mathematics - Theory"; separate syllabus pages printed for each code.')
        if code == 'BP106RMT':
            codes = ['BP106RMT', 'BP106RBT']
        if code == 'BP408P' and 'PHARMACOGNOSY' in nm.upper():
            codes = ['BP408P', 'BP409P']
            quirks.append('Syllabus page heading prints code "BP408P" for this Pharmacognosy practical, but the Fourth Semester scheme table prints "BP409P Pharmacognosy I - Practical"; both printed codes retained.')
            flags.append('duplicate_print_code_BP408P_scheme_prints_BP409P')
        if code == 'BP105T':
            quirks.append('Printed heading reads "COMMUNIUCATION SKILLS" (typo for COMMUNICATION) - kept verbatim.')
        if code == 'BP111P':
            quirks.append('Printed heading reads "COMMUNIUCATION SKILLS" (typo for COMMUNICATION) - kept verbatim.')
        if code == 'BP801T':
            quirks.append('Printed heading reads "BIOSTATISITCS AND RESEARCH METHODOLOGY" (typo for BIOSTATISTICS) - kept verbatim.')
        if code == 'BP810ET':
            quirks.append('Semester VIII scheme table prints "BP810ET Experimental Pharmacology*" (cell wraps to a second line; the wrapped word "Pharmacology*" is dropped by the PDF text layer and was recovered from the visible print) while the syllabus page heading prints "PHARMACOLOGICAL SCREENING METHODS (Theory)"; both printed forms retained.')
        if code == 'BP807ET':
            quirks.append('Semester VIII scheme table prints "BP807ET Computer Aided Drug Design*" (cell wraps; the wrapped word "Design*" is dropped by the PDF text layer and was recovered from the visible print); syllabus page heading prints "COMPUTER AIDED DRUG DESIGN (Theory)".')
        if code == 'BP808ET':
            quirks.append('Semester VIII scheme table row prints only "BP808ET Cell and Molecular" (name genuinely truncated in the print; no continuation word exists anywhere on the page); syllabus page heading prints "CELL AND MOLECULAR BIOLOGY (Theory)".')
        if code == 'BP405T':
            quirks.append('Scheme table prints "Pharmacognosy I - Theory" while syllabus page heading prints "PHARMACOGNOSY AND PHYTOCHEMISTRY I (Theory)"; both printed forms retained.')
        if code == 'BP606T':
            quirks.append('Scheme table prints "Quality Assurance- Theory" while syllabus page heading prints "PHARMACEUTICAL QUALITY ASSURANCE (Theory)"; both printed forms retained.')
        if code == 'BP806ET':
            quirks.append('Scheme table prints "Quality Control and Standardization of Herbal*" while syllabus page heading prints "QUALITY CONTROL AND STANDARDIZATION OF HERBALS".')
        # unit sequence check
        ukeys = sorted(int(k) for k in units)
        if ukeys and ukeys != list(range(1, len(ukeys)+1)):
            quirks.append('Unit numbering not sequential as printed: ' + ','.join(str(u) for u in ukeys))
        for uk, ut in units.items():
            mm = re.search(r'.{0,30}(?:\b0 6\b|\b0 7\b|\b0 8\b|10hours|10Hours).{0,10}', ut)
            if mm:
                quirks.append('Unit-'+uk+': hour annotation prints as garbled/compact text in PDF text layer ("'+mm.group(0).strip()+'"); transcription kept verbatim.')
        if unmarked_blocks:
            for b in unmarked_blocks:
                quirks.append('Print omits the unit label for the block following Unit-'+b['after_unit']+' (verified blank in print; only the hour annotation "07 Hours" prints); its content is transcribed verbatim in unmarked_unit_blocks.')
        if journals:
            quirks.append('Printed "Recommended Journals" list transcribed in journals_print ('+str(len(journals))+' entries).')

        npg_span = subs[si+1][2] if si+1 < len(subs) else pg
        pages_span = f'pp.{pg}' if npg_span == pg else f'pp.{pg}-{npg_span}'

        sch_code = 'BP409P' if (code == 'BP408P' and 'PHARMACOGNOSY' in nm.upper()) else code
        sch = scheme.get(sch_code)
        subject = {
            'name': nm,
            'name_print': name_print,
            'codes': codes,
            'semester': sem,
            'subject_type': stype,
            'hours_print': hours_print,
            'hours_week_print': row_hours(sch_code) if sch else None,
            'credit': row_credit(sch_code) if sch else None,
            'scheme_row_print': sch['row'] if sch else '',
            'scheme_name_print': row_name(sch_code) if sch else '',
            'marks_tail_print': row_tail(sch_code) if sch else '',
            'units': units,
            'unmarked_unit_blocks': unmarked_blocks,
            'experiments': experiments,
            'content_preamble_print': preamble,
            'content_raw_print': content_raw_print,
            'textbooks': [{'no': i2+1, 'book': b} for i2, b in enumerate(books)],
            'reference_books': [],
            'journals_print': [{'no': i2+1, 'journal': j2} for i2, j2 in enumerate(journals)],
            'books_heading_print': books_head,
            'cos': [],
            'locator': {'scheme_page': sch['page'] if sch else None, 'syllabus_pages': pages_span},
            'quirks': quirks,
            'flags': flags,
        }
        return subject

    def exp_text_join_guard(cur_text, m):
        # guard: a roman-item match while an experiment is open with text is still a new item;
        # only treat as continuation if it looks like a stray word line (roman token followed by
        # lowercase word) - none expected; kept for safety.
        return False


    # ---------- incremental append ----------
    os.makedirs(os.path.dirname(DRAFT_OUT), exist_ok=True)
    def append_subject(s):
        if os.path.exists(DRAFT_OUT):
            draft = json.load(open(DRAFT_OUT))
        else:
            draft = {'pdf_rel': PDF_REL, 'session': SESSION, 'course': COURSE,
                     'sha16': SHA16, 'stem': STEM, 'subjects': [], 'non_subject_rows': [],
                     'quirks': [], 'flags': []}
        draft['subjects'].append(s)
        tmp = DRAFT_OUT + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(draft, f, ensure_ascii=False, indent=1)
        os.replace(tmp, DRAFT_OUT)

    counts = []
    for si in range(len(subs)):
        s = parse_subject(si)
        append_subject(s)
        counts.append((s['codes'][0], s['semester'], len(s['units']), len(s['experiments']), len(s['textbooks']), s['subject_type']))
    for c in counts:
        print(c)

    # ---------- non_subject_rows ----------
    draft = json.load(open(DRAFT_OUT))
    nsr = []
    cover = norm(' '.join(pages[1]))
    nsr.append({'kind': 'cover', 'print': cover, 'locator': 'p.1'})
    nsr.append({'kind': 'note', 'print': 'BACHELOR OF PHARMACY I, II, III & IV Year — On PCI Guidelines (EFFECTIVE FROM THE SESSION: 2019-20)', 'locator': 'p.1'})
    names = {2:'FIRST SEMESTER',3:'ECOND SEMESTER',4:'THIRD SEMESTER*',5:'FOURTH SEMESTER*',6:'FIFTH SEMESTER',7:'SIXTH SEMESTER',8:'SEVENTH SEMESTER',9:'EIGHTH SEMESTER'}
    for pg, nm in names.items():
        body = norm(' '.join(pages[pg]))
        if pg == 9:
            body = body.replace('BP807ET Computer Aided Drug', 'BP807ET Computer Aided Drug Design*', 1)
            body = body.replace('BP810ET Experimental', 'BP810ET Experimental Pharmacology*', 1)
        nsr.append({'kind': 'scheme_table', 'print': nm + ' — ' + body, 'locator': f'p.{pg}'})
    nsr.append({'kind': 'note', 'print': norm(' '.join(pages[147])), 'locator': 'p.147'})
    draft['non_subject_rows'] = nsr
    draft['quirks'] = [
        'Page header/running title prints "Evaluation Scheme Bachelor of Pharmacy I, II, III & IV Year syllabus 2019-2020"; cover prints "(EFFECTIVE FROM THE SESSION: 2019-20)". Session recorded as 2019-20 per printed cover.',
        'PDF text layer (PyMuPDF) silently drops the wrapped second-line scheme-cell fragments "Design*" (BP807ET row) and "Pharmacology*" (BP810ET row) on p.9; both recovered from the visible print via pdftotext -bbox cross-check (coordinates match the wrapped cell lines) and restored in the affected scheme rows and the p.9 scheme_table row.',
        'Semester II heading prints "ECOND SEMESTER" (typo for SECOND) — kept verbatim in scheme_table row (p.3).',
        'Semester VIII scheme table prints the ten elective rows (BP803ET-BP812ET) against a single merged marks block ("4 + 4 = 8", "10 + 10 = 20", ...); individual elective rows carry only code+name (p.9). Footnote: every candidate opts two elective subjects and carries out project on any one.',
        'Scheme lists BP814ET (LSSSDC Elective*) in Semester VIII but no syllabus page is printed for it anywhere in the document.',
        'Fourth Semester scheme prints "BP409P Pharmacognosy I – Practical" but the syllabus page for that subject prints heading code "BP408P" (same code as Pharmacology-I Practical); both printed codes retained on that subject.',
        'Fourth Semester scheme prints "Pharmacognosy I – Theory" for BP405T while the syllabus page heading prints "PHARMACOGNOSY AND PHYTOCHEMISTRY I (Theory)".',
        'BP101T and BP201T syllabus pages print no Recommended Books list (printed blank).',
        'Printed typos kept verbatim: "COMMUNIUCATION SKILLS" (BP105T, BP111P), "BIOSTATISITCS" (BP801T), "ECOND SEMESTER" (p.3).',
        'PDF text layer splits superscripts and some hour annotations ("4 / th / edition", "10hours", "0 6 Hours"); transcriptions normalize whitespace only and keep the printed token sequence.',
        'KVE301 row: End Semester marks 100, Total 150 (not 75/100 like core subjects); footnote prints "Human values & Professional Ethics will be offered as a compulsory course for which passing marks shall be 30% in End Semester Examination and 40% in aggregate."',
    ]
    draft['flags'] = [
        'BP814ET (LSSSDC Elective) listed in Semester VIII scheme table but has no printed syllabus page — no subject row extractable.',
        'BP408P printed on two different syllabus pages (Pharmacology-I Practical p.72; Pharmacognosy and Phytochemistry I Practical p.75, where scheme prints BP409P) — needs owner adjudication at merge.',
    ]
    tmp = DRAFT_OUT + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(draft, f, ensure_ascii=False, indent=1)
    os.replace(tmp, DRAFT_OUT)

    print('total subjects:', len(draft['subjects']))
    print('non_subject_rows:', len(nsr))

if __name__ == '__main__':
    main()
