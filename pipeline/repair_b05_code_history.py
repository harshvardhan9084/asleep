#!/usr/bin/env python3
"""CRON-20261027-B05 repair — undo comma damage my hygiene pass caused in
code_history_all (a NARRATIVE provenance cell per RULES §9: e.g. 'KCS301 (2021-22,
sem-3)' must keep its comma). all_codes / primary_code / k_era_pool_codes fixes
(empty-segment removal, separator consistency) are LEGITIMATE and stay.

Repair per CSV:
  - rows present in the pre-commit backup (work/pipeline_v2/backups/20261027-052920):
    restore code_history_all VERBATIM from backup.
  - rows NOT in backup (this batch's appends): reverse the exact damage pattern
    ';sem-' -> ', sem-' (merge writes chains as '<CODE> (<sess>, sem-<n>)' joined by
    ' | ' — no other commas exist in constructed chains).
  - then an artifact-only sweep on code_history_all: strip leading/trailing ';',
    collapse ';;' -> ';', drop empty segments, dedupe within cell — NO comma changes.
"""
import csv, re

BACKUP = '/home/z/my-project/work/pipeline_v2/backups/20261027-052920'
PAIRS = [(f'{BACKUP}/syllabus_extreme_rich.csv',
          '/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv'),
         (f'{BACKUP}/syllabus_aux_rows.csv',
          '/home/z/my-project/download/art_d_final/syllabus_aux_rows.csv')]

for bk_path, path in PAIRS:
    try:
        bk = {r['subject_id']: r for r in csv.DictReader(open(bk_path, encoding='utf-8'))}
    except FileNotFoundError:
        bk = {}
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    cols = list(rows[0].keys())
    n_rest = n_rev = n_art = 0
    for r in rows:
        sid = r['subject_id']
        cur = r.get('code_history_all') or ''
        if sid in bk:
            want = bk[sid].get('code_history_all') or ''
            if cur != want:
                r['code_history_all'] = want
                n_rest += 1
        else:
            if ';sem-' in cur:
                r['code_history_all'] = cur.replace(';sem-', ', sem-')
                n_rev += 1
        # artifact-only sweep (no comma changes)
        cur = r.get('code_history_all') or ''
        parts = [p for p in cur.split(';')]
        parts = [p for p in parts if p.strip()]
        seen, out = set(), []
        for p in parts:
            k = p.strip()
            if k.upper() in seen:
                continue
            seen.add(k.upper())
            out.append(k)
        new = ';'.join(out)
        if new != cur:
            r['code_history_all'] = new
            n_art += 1
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(path.split('/')[-1], '| restored:', n_rest, '| reversed:', n_rev, '| artifact-swept:', n_art)

# verification
for _, path in PAIRS:
    new = list(csv.DictReader(open(path, encoding='utf-8')))
    bad = [r['subject_id'] for r in new
           if ((r.get('code_history_all') or '').startswith(';')
               or (r.get('code_history_all') or '').endswith(';')
               or ';;' in (r.get('code_history_all') or ''))]
    damaged = [r['subject_id'] for r in new
               if re.search(r'\(\d{4}-\d{2};sem-', r.get('code_history_all') or '')]
    print(path.split('/')[-1], '| residual artifacts:', len(bad), '| residual ;sem- damage:', len(damaged))
