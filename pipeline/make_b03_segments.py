#!/usr/bin/env python3
"""Build segment slices for batch03's two oversized PDFs (S05 mode):
- 08_bpharm_scheme-syllabus_2026-27 (295pp, ~126 subject blocks)
- 10_bpharm_y1-4_syllabus_2019-20 (149pp, ~50 subject blocks)

Segments are cut EXACTLY at subject-start pages, so no subject spans a
segment boundary. Each segment slice gets a fulltext-format .txt and a
parsed-schema .json under staging/batch03/segments/. Fragment drafts are
written by subagents to drafts/frag_b03_<stem>_s<k>.json (NOT *.draft.json);
a later merge step concatenates them into the canonical draft.
"""
import json, os, re

PARSED = '/home/z/my-project/work/pipeline_v2/parsed'
OUT = '/home/z/my-project/work/pipeline_v2/staging/batch03/segments'
os.makedirs(OUT, exist_ok=True)


def load(stem):
    d = json.load(open(f'{PARSED}/{stem}.json'))
    pgs = d['pages']
    if pgs and isinstance(pgs[0], dict):
        pgs = [p.get('text', '') for p in pgs]
    return d, pgs


def starts_08(pgs):
    # detailed subject blocks carry a Course Code/Course Title/Course Type header
    s = [i for i, t in enumerate(pgs, 1)
         if i >= 7 and re.search(r'Course\s*Code', t) and re.search(r'BP\d{3}', t)]
    return s  # p6 = Semester-I scheme table only -> handled inside seg 1


def starts_10(pgs):
    s = [i for i, t in enumerate(pgs, 1)
         if re.search(r'^BP\d{3}[A-Z]{0,2}\.\s*\S', t, re.M)]
    return [i for i in s if i >= 11]  # pp2-9 scheme tables -> seg 1


def write_slice(rec, pgs, k, lo, hi):
    """lo..hi inclusive, 1-based page numbers."""
    stem = f"{rec['stem']}_s{k:02d}"
    pages = [{'page': n, 'text': pgs[n - 1]} for n in range(lo, hi + 1)]
    js = {"stem": stem, "pdf_path": rec['pdf_path'], "rel": rec['rel'],
          "session": rec.get('session'), "sha16": rec['sha16'],
          "n_pages": len(pages), "pages": pages,
          "page_range": [lo, hi]}
    with open(f'{OUT}/{stem}.json', 'w') as f:
        json.dump(js, f, ensure_ascii=False)
    with open(f'{OUT}/{stem}.fulltext.txt', 'w') as f:
        for p in pages:
            f.write(f"===== PAGE {p['page']} =====\n{p['text']}\n")
    return stem


for tag, stem, sf, group in (
    ('08', '08_bpharm_scheme-syllabus_2026-27', starts_08, 13),
    ('10', '10_bpharm_y1-4_syllabus_2019-20', starts_10, 13),
):
    rec, pgs = load(stem)
    n = len(pgs)
    starts = sf(pgs)
    # first segment starts at page 1 (cover/PO/scheme tables -> non_subject_rows)
    bounds = [1] + starts[:]
    segs = []
    cur = [bounds[0]]
    cnt = 0
    for j, b in enumerate(bounds[1:], 1):
        cur.append(b)
        cnt += 1
        nxt = bounds[j + 1] if j + 1 < len(bounds) else None
        if cnt >= group and (nxt is None or nxt - b > 1):
            segs.append((cur[0], nxt - 1 if nxt else n, cur[1:]))
            cur, cnt = [], 0
    if cur:
        seg_start = cur[0]
        seg_subjects = cur[1:]
        segs.append((seg_start, n, seg_subjects))

    print(f"== {tag}: n_pages={n} subject_starts={len(starts)} segments={len(segs)}")
    for k, (lo, hi, ss) in enumerate(segs, 1):
        sl = write_slice(rec, pgs, k, lo, hi)
        size = os.path.getsize(f'{OUT}/{sl}.fulltext.txt')
        print(f"  s{k:02d}: pages {lo}-{hi} ({hi-lo+1}pp, {size//1024}KB) starts={ss}")
