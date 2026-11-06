#!/usr/bin/env python3
"""b39_map_headers_d10.py — print-anchored detail-header mapping for
10_btech_y3_syllabus_2024-25 (ICE y3 2024-25; the recorded B38 doc-08 class:
line-broken codes 'BEC / -501', 'BEC- / 502', whole codes 'BEC-551', every
page carrying a running 'Curriculum & Evaluation Scheme' header). Scans
p.4-31: the code token (single line or split over <=3 lines) followed by the
CAPS name line(s) before 'L:T:P'. Writes inv/<stem>.inv.json.
"""
import json, re, sys

stem = "10_btech_y3_syllabus_2024-25"
ft = open(f"/home/z/my-project/work/pipeline_v2/parsed/{stem}.fulltext.txt").read()
parts = re.split(r"===== PAGE (\d+) =====", ft)
PAGES = dict((int(parts[i]), parts[i + 1]) for i in range(1, len(parts) - 1, 2))

RUNHDR = re.compile(r"^(?:INSTRUMENTATION AND CONTROL ENGINEERING|Curriculum & Evaluation Scheme.*|Page \d+|B\.Tech.*|V Semester|Syllabus|VI Semester)$")
CODE_TOK = re.compile(r"^([A-Z]{2,4})-?(\d{3})([A-Z]?)$")
NAME_OK = re.compile(r"^[A-Z][A-Z0-9 &/,()\-\.:'&+]+$")

entries, seen = [], set()
for pno in sorted(PAGES):
    if pno < 4:
        continue
    lines = [l.strip() for l in PAGES[pno].splitlines() if l.strip()]
    # drop the running header block
    body = [l for l in lines if not RUNHDR.match(l)]
    if not body:
        continue
    # find the first code token: may be whole ('BEC-551') or split ('BEC', '-501') / ('BEC-', '502')
    idx = code = None
    for i, l in enumerate(body[:8]):
        if CODE_TOK.match(l):
            idx, code = i, l
            break
        m = re.match(r"^([A-Z]{2,4})-?$", l)
        if m and i + 1 < len(body):
            m2 = re.match(r"^-?(\d{3}[A-Z]?)$", body[i + 1])
            if m2:
                idx = i
                code = m.group(1) + m2.group(1)
                break
    if idx is None or not CODE_TOK.match(code):
        continue
    # name = consecutive CAPS lines right after the code (may wrap, e.g. 'MICROCONTROLLERS AND SENSORS FOR IOT / DEVICES')
    nm_parts = []
    j = idx + 1 if CODE_TOK.match(body[idx]) else idx + 2
    while j < len(body) and len(nm_parts) < 3:
        l = body[j]
        if re.match(r"^\d+L:\d+T:\d+P", l) or l.startswith("Credit"):
            break
        if NAME_OK.match(l) and len(l) >= 4:
            nm_parts.append(l)
            j += 1
        else:
            break
    name = " ".join(nm_parts).strip()
    norm = re.sub(r"[^A-Z0-9]", "", code)
    if norm in seen or not name:
        continue
    seen.add(norm)
    entries.append({"class": "detail", "code_print": code, "name_print": name[:70], "page": pno})

for e in entries:
    print(e["code_print"], "|", e["name_print"], "| p.", e["page"])
print("TOTAL", len(entries))
json.dump(entries, open(f"/home/z/my-project/work/pipeline_v2/inv/{stem}.inv.json", "w"), indent=1, ensure_ascii=False)
print("INV|/home/z/my-project/work/pipeline_v2/inv/%s.inv.json" % stem)
