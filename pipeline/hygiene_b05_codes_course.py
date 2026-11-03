#!/usr/bin/env python3
"""CRON-20261027-B05 post-commit hygiene pass (main + aux CSVs):

1. Empty code segments in semicolon-joined code cells (';BAE754...' leading, trailing
   or doubled ';' — introduced when codeless draft subjects contributed empty strings
   on UPDATE/APPEND; earliest instances date to batch-04's MBA-Integrated DSE rows).
   Fix: split on [;,], strip whitespace, drop empty segments, dedupe within the cell
   preserving first-seen order, rejoin with ';'.
2. course_name 'BTech' -> 'B.Tech' (registry convention, batch-01; same rule as
   normalize_b03_course_name.py — pipe-split aware, dedupe, case-insensitive).

Nothing else touched. Cells scanned: all_codes, primary_code, code_history_all,
k_era_pool_codes (additive/narrative code cells only; *_print evidence cells untouched).
"""
import csv

CODE_COLS = ['all_codes', 'primary_code', 'code_history_all', 'k_era_pool_codes']
PATHS = ['/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv',
         '/home/z/my-project/download/art_d_final/syllabus_aux_rows.csv']

for path in PATHS:
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    cols = list(rows[0].keys())
    n_code_cells = 0
    n_course_cells = 0
    for r in rows:
        for col in CODE_COLS:
            cur = r.get(col) or ''
            if not cur:
                continue
            parts = [p.strip() for p in cur.replace(',', ';').split(';')]
            parts = [p for p in parts if p]
            seen, out = set(), []
            for p in parts:
                if p.upper() in seen:
                    continue
                seen.add(p.upper())
                out.append(p)
            new = ';'.join(out)
            if new != cur:
                r[col] = new
                n_code_cells += 1
        cur = r.get('course_name') or ''
        parts = [p.strip() for p in cur.split('|') if p.strip()]
        new_parts = ['B.Tech' if p == 'BTech' else p for p in parts]
        seen, out = set(), []
        for p in new_parts:
            k = p.lower()
            if k in seen:
                continue
            if k == 'btech' and 'b.tech' in seen:
                continue
            seen.add(k)
            out.append(p)
        new = '|'.join(out)
        if new != cur:
            r['course_name'] = new
            n_course_cells += 1
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(path.split('/')[-1], '| code cells fixed:', n_code_cells, '| course cells fixed:', n_course_cells)
