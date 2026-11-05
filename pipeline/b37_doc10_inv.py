#!/usr/bin/env python3
"""b37_doc10_inv.py <stem> — deterministic inventory for docs whose detail
sections are NUMBERED LISTS with no printed codes (codes only in scheme
tables), e.g. 10_btech_textile-tech_syllabus_2018-19:
  '5th Semester B. Tech. Textile Technology' / '1. Managerial Economics'
  / '3. Textile Testing-I (L T P 3-1-0= 4)' + 'Unit (1): ...' prose.
Method: scheme-table rows supply (code_print, name_print, page); each detail
section header (numbered line whose following text holds Unit markers) is
name-matched (difflib >= 0.72) to a scheme row -> class=detail with the
scheme row's codes and the section's start page; unmatched detail sections
become scheme_only entries with the header name (no code, flagged).
Output: the standard inv json consumed by b37_resume.py."""
import json, re, sys
from difflib import SequenceMatcher
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")

stem = sys.argv[1]
parsed_dir = "/home/z/my-project/work/pipeline_v2/parsed"
fulltext = open(f"{parsed_dir}/{stem}.fulltext.txt").read()
PAGES = []
parts = re.split(r"===== PAGE (\d+) =====", fulltext)
for i in range(1, len(parts) - 1, 2):
    PAGES.append((int(parts[i]), parts[i + 1]))

scheme_pages = {p for p, t in PAGES if re.search(r"Evaluation\s+Scheme|Study\s+and\s+Evaluation", t, re.I)}
inv = json.load(open(f"/home/z/my-project/work/pipeline_v2/inv/{stem}.inv.json"))
scheme_rows = [x for x in inv if x.get("class") != "detail"]

# detail sections: numbered/lettered headers whose SPAN (until the next
# numbered/lettered header) holds >=2 Unit markers (or >=1 with an LTP print)
sections = []
HDR = re.compile(r"^\s*(\d{1,2}|[a-e])[\.\)]\s+([A-Za-z][^\n]{3,70})")
UNIT = re.compile(r"Unit\s*\(?[0-9IVX]{1,3}\)?\s*[:\.]|Unit\s+[0-9IVX]\b", re.I)
for pno, ptext in PAGES:
    if pno in scheme_pages:
        continue
    lines = ptext.splitlines()
    starts = [i for i, ln in enumerate(lines) if HDR.match(ln.strip())]
    for k, i in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        span = "\n".join(lines[i:end])
        m = HDR.match(lines[i].strip())
        n_units = len(UNIT.findall(span))
        has_ltp = "(L T P" in span or "(LTP" in span
        if n_units >= 2 or (n_units >= 1 and has_ltp):
            name = re.sub(r"\s*\(.*$", "", m.group(2)).strip()
            name = re.sub(r"\s*[:\-–]\s*(As per.*|Per concerned.*)$", "", name, flags=re.I).strip()
            sections.append({"name": name, "page": pno})
# dedupe by normalized name+page-adjacency
seen = {}
for s in sections:
    k = re.sub(r"[^a-z0-9]", "", s["name"].lower())
    if k in seen and abs(seen[k]["page"] - s["page"]) <= 1:
        continue
    seen[k] = s
sections = list(seen.values())
print(f"doc10 sections: {len(sections)}; scheme rows: {len(scheme_rows)}")

def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

used_rows = set()
out = []
for sec in sections:
    best, br = None, 0.0
    for i, r in enumerate(scheme_rows):
        if i in used_rows:
            continue
        score = SequenceMatcher(None, norm(sec["name"]), norm(r.get("name_print", ""))).ratio()
        if score > br:
            br, best = score, i
    if best is not None and br >= 0.72:
        r = scheme_rows[best]
        used_rows.add(best)
        out.append({"class": "detail", "code_print": r.get("code_print", ""),
                    "name_print": sec["name"], "page": sec["page"], "_scheme_name": r.get("name_print", "")})
    else:
        out.append({"class": "scheme_only", "code_print": "", "name_print": sec["name"],
                    "page": sec["page"], "_unmatched_detail": True})

for i, r in enumerate(scheme_rows):
    if i not in used_rows:
        e = dict(r)
        e.setdefault("class", "scheme_only")
        out.append(e)

n_unmatched = sum(1 for x in out if x.get("_unmatched_detail"))
print(f"doc10 inv: detail={sum(1 for x in out if x['class']=='detail')} "
      f"matched; unmatched-detail={n_unmatched}; total={len(out)}")
json.dump(out, open(f"/home/z/my-project/work/pipeline_v2/inv/{stem}.inv.json", "w"), indent=1, ensure_ascii=False)
print("INV updated")
