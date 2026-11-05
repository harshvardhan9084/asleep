#!/usr/bin/env python3
"""b37_doc09_inv.py — deterministic inventory for the NEP first-year TX-stream
doc (09_btech_textile-tech_course-structure_2026-27) whose per-subject sections
follow the fixed print template:
    Course Code \\n <code(s)> \\n Title of the Course \\n <title lines...> \\n Total Credits...
Scheme cells (paired prints) on 'Scheme of Teaching' pages contribute
scheme_only entries only for codes never covered by a detail section."""
import json, re, sys

stem = "09_btech_textile-tech_course-structure_2026-27"
fulltext = open(f"/home/z/my-project/work/pipeline_v2/parsed/{stem}.fulltext.txt").read()
parts = re.split(r"===== PAGE (\d+) =====", fulltext)
PAGES = [(int(parts[i]), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]

detail, order = {}, []
for pno, ptext in PAGES:
    lines = [l.strip() for l in ptext.splitlines()]
    for i, ln in enumerate(lines):
        if ln == "Course Code":
            codes, j = [], i + 1
            while j < len(lines) and lines[j] != "Title of the Course" and j < i + 4:
                for tok in re.findall(r"([A-Z]{2,4}\s?\d{3}[A-Z]?)", lines[j]):
                    codes.append(re.sub(r"[^A-Z0-9]", "", tok))
                j += 1
            if not codes or j >= len(lines) or lines[j] != "Title of the Course":
                continue
            title, j2 = [], j + 1
            while j2 < len(lines) and not re.match(r"^(Total Credits|NCrF|Course Category|Course Code)", lines[j2]) and j2 < j + 5:
                if lines[j2]:
                    title.append(lines[j2])
                j2 += 1
            nm = " ".join(title).strip()
            if not nm or nm.lower().startswith("title of"):
                continue
            ncode = codes[0]
            if ncode not in detail:
                detail[ncode] = {"class": "detail", "code_print": "/".join(codes),
                                 "name_print": nm[:80], "page": pno}
                order.append(ncode)

det_norms = set(detail)
scheme, scheme_pages = {}, set()
for pno, ptext in PAGES:
    if re.search(r"Scheme of Teaching|Study and Evaluation", ptext, re.I):
        scheme_pages.add(pno)
for pno in sorted(scheme_pages):
    lines = [l.strip() for l in dict(PAGES)[pno].splitlines()]
    for i, ln in enumerate(lines):
        toks = re.findall(r"([A-Z]{2,4}\s?\d{3}[A-Z]?)", ln)
        for tok in toks:
            ncode = re.sub(r"[^A-Z0-9]", "", tok)
            if ncode in det_norms or ncode in scheme:
                continue
            name_parts = []
            for nxt in lines[i + 1: i + 6]:
                if not nxt or re.match(r"^\d", nxt) or re.search(r"[A-Z]{2,4}\s?\d{3}", nxt):
                    break
                name_parts.append(nxt)
                if len(" ".join(name_parts)) > 60:
                    break
            nm = " ".join(name_parts).strip()
            scheme[ncode] = {"class": "scheme_only", "code_print": ncode,
                             "name_print": nm[:70] if re.search(r"[A-Za-z]{3}", nm) else "", "page": pno}

inv = list(detail.values()) + list(scheme.values())
print(f"doc09 inv: detail={len(detail)} scheme={len(scheme)} (scheme pages: {len(scheme_pages)})")
json.dump(inv, open(f"/home/z/my-project/work/pipeline_v2/inv/{stem}.inv.json", "w"), indent=1, ensure_ascii=False)
print("INV updated")
