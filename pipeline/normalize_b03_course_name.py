#!/usr/bin/env python3
"""CRON-20261027-B03 post-commit normalization: course_name 'BTech' -> 'B.Tech' (registry
convention from batch 01). Pipe-split aware; main + aux CSVs; nothing else touched."""
import csv

for path in ['/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv',
             '/home/z/my-project/download/art_d_final/syllabus_aux_rows.csv']:
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    cols = list(rows[0].keys())
    fixed = 0
    for r in rows:
        cur = r.get('course_name') or ''
        parts = [p.strip() for p in cur.split('|') if p.strip()]
        new_parts = ['B.Tech' if p == 'BTech' else p for p in parts]
        # dedupe case-insensitively while preserving order (B.Tech first if it exists)
        seen, out = set(), []
        for p in new_parts:
            k = p.lower()
            if k in seen:
                continue
            # if BTech collapsed into existing B.Tech
            if k == 'btech' and 'b.tech' in seen:
                continue
            seen.add(k)
            out.append(p)
        new = '|'.join(out)
        if new != cur:
            r['course_name'] = new
            fixed += 1
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(path.split('/')[-1], 'cells fixed:', fixed)
