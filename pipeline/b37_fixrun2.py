#!/usr/bin/env python3
"""b37_fixrun2.py — second verify-repair pass (docs 03/04/05/06/08/09)."""
import json, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
from b37_verify_fix import (load, save, row_codes, common, has_detail,
                            scheme_pages_of, reextract, me)

BASE = "/home/z/my-project/work/pipeline_v2"
res = {}

# ---- doc 03: ensure NCS151/252 lab row exists
stem = "03_btech_syllabus_2013-14"
d, full, pa = load(stem)
have = {c for s in d["subjects"] for c in row_codes(s)}
if "NCS252" not in have:
    code, obj = me.extract_one(stem + ".pdf",
        "\n\n".join(t for p, t in me.pages_of(full) if 22 <= p <= 23),
        {"file": stem + ".pdf"},
        {"class": "detail", "code_print": "NCS-151/NCS-252", "name_print": "Computer Programming Lab", "page": 22},
        d.get("session", ""), d.get("course", "BTech"))
    if isinstance(obj, list):
        obj = next((x for x in obj if isinstance(x, dict)), {})
    obj["name"] = "Computer Programming Lab"; obj["name_print"] = "NCS-151/NCS-252 : Computer Programming Lab"
    obj["codes"] = ["NCS151", "NCS252"]
    obj.setdefault("flags", []).append("experiments_only_no_units")
    obj.setdefault("quirks", []).append("lab detail p.22 prints WAP experiment list; no Unit theory (print design)")
    d["subjects"].append(obj)
    res[stem] = "NCS lab row appended"
else:
    res[stem] = "NCS codes already present"
save(d, stem)

# ---- doc 04: fix the EAS paired row codes
stem = "04_btech_textile-chem-texteng-mmft_y2_syllabus_2009-10"
d, full, pa = load(stem)
fixed = 0
for s in d["subjects"]:
    raw = s.get("codes") or []
    joined = ",".join(raw)
    if "EAS301EAS401" in joined.replace(" ", ""):
        s["codes"] = ["EAS301", "EAS401"]
        s.setdefault("quirks", []).append("paired print 'EAS-301/EAS-401' split into atomic codes (both print in the PDF)")
        fixed += 1
res[stem] = f"EAS compound rows fixed: {fixed}"
save(d, stem)

# ---- doc 05: common() (MOOCs move) + Dyeing-I Lab re-extract
stem = "05_btech_textile-chemistry_y2_model-curriculum_2019-20"
d, full, pa = load(stem)
d, log = common(d, full, pa, stem)
targets = []
for s in d["subjects"]:
    nm = (s.get("name") or s.get("name_print") or "")
    if re.search(r"Dyeing\s*-?\s*I Lab", nm, re.I) and not (s.get("units") or s.get("experiments")):
        m = re.search(re.escape(re.sub(r"[^a-z0-9]", "", nm.lower()))[:16], re.sub(r"[^a-z0-9]", "", full.lower()))
        pg = None
        if m:
            pg = full[:m.start()].count("===== PAGE")
        targets.append((s, pg or 1))
reextract(stem, d, full, targets)
save(d, stem)
res[stem] = f"common({len(log)}) + dyeing-lab re-extract"

# ---- doc 06: Dyeing-I Lab re-extract
stem = "06_btech_textile-chemistry_y2_scheme-syllabus_2017-18"
d, full, pa = load(stem)
targets = []
for s in d["subjects"]:
    nm = (s.get("name") or s.get("name_print") or "")
    if re.search(r"Dyeing\s*-?\s*I\s*Lab", nm, re.I) and not (s.get("units") or s.get("experiments")):
        key = re.sub(r"[^a-z0-9]", "", nm.lower())[:16]
        m = re.search(re.escape(key), re.sub(r"[^a-z0-9]", "", full.lower()))
        pg = full[:m.start()].count("===== PAGE") if m else None
        targets.append((s, pg or 1))
reextract(stem, d, full, targets)
save(d, stem)
res[stem] = f"dyeing-lab re-extract ({len(targets)})"

# ---- doc 08: common() + force scheme-only on training/project rows
stem = "08_btech_textile-chemistry_y4_syllabus-cbcs_2019-20"
d, full, pa = load(stem)
d, log = common(d, full, pa, stem)
n = 0
for s in d["subjects"]:
    nm = (s.get("name") or s.get("name_print") or "")
    if re.search(r"Industrial Training|PROJECT", nm, re.I) and not (s.get("units") or s.get("experiments")):
        s.setdefault("flags", []).append("scheme_row_only_detailed_syllabus_not_printed")
        s.setdefault("quirks", []).append("training/project row prints only in the evaluation scheme (L-T-P 0-0-2 + marks); no detail page in this document (print evidence)")
        n += 1
save(d, stem)
res[stem] = f"common({len(log)}) + scheme-only flags {n}"

# ---- doc 09: find detail pages for the two failing labs + calculus units
stem = "09_btech_textile-tech_course-structure_2026-27"
d, full, pa = load(stem)
targets = []
for s in d["subjects"]:
    nm = (s.get("name") or s.get("name_print") or "")
    cs = row_codes(s)
    if not (s.get("units") or s.get("experiments")):
        pg = None
        for c in cs:
            m = re.search(re.escape(c[:6]) + r"[\s\-/]?", full)
            if m:
                pg = full[:m.start()].count("===== PAGE")
                break
        if nm and re.search(r"Calculus", nm, re.I) and pg is None:
            pg = 16
        if pg:
            targets.append((s, pg))
reextract(stem, d, full, targets)
save(d, stem)
res[stem] = f"re-extracts: {[(t[0].get('name','')[:18], t[1]) for t in targets]}"

for k, v in res.items():
    print(f"FIX2|{k[:44]}|{v}")
