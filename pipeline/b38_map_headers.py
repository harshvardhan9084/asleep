#!/usr/bin/env python3
"""b38_map_headers.py — build detail entries for docs whose headers the
deterministic inventory misses (line-broken codes / lecture-plan tables /
Hindi-medium pages). Print-anchored: codes + names come from the page text.
Usage: python3 b38_map_headers.py <08|09|10>  (writes tmp/invNN_detail.json)
"""
import json, re, sys

WHICH = sys.argv[1]
DOCS = {
    "08": "08_btech_vlsi_y3_syllabus-rev_2025-26",
    "09": "09_btech_vlsi_y4_syllabus_2026-27",
    "10": "10_btech_y1_syllabus-hindi_2021-22",
}
stem = DOCS[WHICH]
ft = json.load(open(f"/home/z/my-project/work/pipeline_v2/parsed/{stem}.json"))
fp = {p["no"]: p["text"] for p in ft["pages"]}

entries = []
if WHICH == "08":
    HDRS = [5, 6, 7, 8, 9, 10, 11, 13, 14, 16, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 31, 32, 33]
    for n in HDRS:
        t = fp[n]
        m = re.search(r"([A-Z]{2,4})\s*\n?\s*-\s*\n?\s*(\d{3}[A-Z]?)", t)
        code = (m.group(1) + m.group(2)) if m else "?"
        seg = t[m.end():m.end() + 400] if m else t
        nm = ""
        for ln in seg.splitlines():
            l = ln.strip()
            if len(l) >= 6 and re.match(r"^[A-Z][A-Z0-9 &/,()\-\.]+$", l):
                nm = l
                break
        entries.append({"class": "detail", "code_print": code, "name_print": nm or "?", "page": n})
elif WHICH == "09":
    # p.5 BEC-701 detail; scan every page for CODE headers with content beyond scheme cells
    for n in sorted(fp):
        t = fp[n]
        m = re.search(r"^([A-Z]{2,4}\s?-?\s?\d{3}[A-Z]?)\s*$", t, re.M)
        if n >= 5 and m:
            code = re.sub(r"\s", "", m.group(1))
            seg = t[m.end():]
            nm = ""
            for ln in seg.splitlines():
                l = ln.strip()
                if len(l) >= 6 and re.match(r"^[A-Z][A-Z0-9 &/,()\-\.]+$", l):
                    nm = l
                    break
            entries.append({"class": "detail", "code_print": code, "name_print": nm or "?", "page": n})
elif WHICH == "10":
    # Hindi y1: detail pages p.18+; header = CODE line (ASCII digits) possibly with
    # Hindi name on the same or next line
    for n in sorted(fp):
        if n < 18:
            continue
        t = fp[n]
        m = re.search(r"\b([A-Z]{2,4}\s?-?\s?\d{3}[A-Z]?)\b", t)
        if not m:
            continue
        code = re.sub(r"\s", "", m.group(1))
        # Hindi name: first non-ASCII line with Devanagari after the code position
        seg = t[m.end():m.end() + 300]
        nm = ""
        for ln in seg.splitlines():
            l = ln.strip()
            if re.search(r"[\u0900-\u097F]", l) and len(l) >= 3:
                nm = l
                break
        entries.append({"class": "detail", "code_print": code, "name_print": nm, "page": n})

json.dump(entries, open(f"/home/z/my-project/work/pipeline_v2/tmp/inv{WHICH}_detail.json", "w"), indent=1, ensure_ascii=False)
for e in entries:
    print(f"p{e['page']:2d} {e['code_print']:10s} {e['name_print'][:56]}")
print(f"{len(entries)} detail entries -> tmp/inv{WHICH}_detail.json")
