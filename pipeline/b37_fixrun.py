#!/usr/bin/env python3
"""b37_fixrun.py — per-doc targeted verify repairs (uses b37_verify_fix helpers)."""
import json, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
from b37_verify_fix import (load, save, row_codes, common, has_detail,
                            scheme_pages_of, reextract, me)

BASE = "/home/z/my-project/work/pipeline_v2"

def flag_scheme_only(d, full, stem, name_pat):
    sp = scheme_pages_of(full)
    n = 0
    for s in d["subjects"]:
        nm = (s.get("name") or s.get("name_print") or "")
        if re.search(name_pat, nm, re.I) and not (s.get("units") or s.get("experiments")):
            if has_detail(full, nm, sp) is None:
                s.setdefault("flags", []).append("scheme_row_only_detailed_syllabus_not_printed")
                s.setdefault("quirks", []).append(
                    "subject prints only in the scheme/evaluation table of this document; no detail page (print evidence, B37 verify repair)")
                n += 1
    return n

results = {}

# ---- doc 01: fill KNC row names from the printed non-credit list
stem = "01_btech_s5-6_non-credit-courses_2020-21"
d, full, pa = load(stem)
FILL = {"KNC501": "CONSTITUTION OF INDIA, LAW AND ENGINEERING",
        "KNC502": "INDIAN TRADITION, CULTURE AND SOCIETY"}
for s in d["subjects"]:
    cs = row_codes(s)
    nm = (s.get("name") or s.get("name_print") or "")
    for c in cs:
        if c[:6] in FILL and not nm:
            s["name"] = FILL[c[:6]]; s["name_print"] = FILL[c[:6]]
            s.setdefault("quirks", []).append("name from the printed non-credit course list cell (KNC501/KNC601 paired print)")
            s.setdefault("flags", []).append("scheme_row_only_detailed_syllabus_not_printed")
save(d, stem); results[stem] = "knc rows filled+flagged"

# ---- doc 02: EIC551 experiment 10 (IC 555) verbatim append
stem = "02_btech_syllabus_2009-10"
d, full, pa = load(stem)
for s in d["subjects"]:
    if "EIC551" in row_codes(s):
        exps = [e.get("exp", "") for e in (s.get("experiments") or [])]
        if not any("ic 555" in e.lower() or "ic555" in e.lower() for e in exps):
            n = len(exps) + 1
            s.setdefault("experiments", []).append(
                {"no": n, "exp": "Astable and monostable multivibrator using IC 555."})
            s.setdefault("quirks", []).append(
                "experiment 10 'Astable and monostable multivibrator using IC 555.' appended verbatim from the printed EIC-551 lab list (verify GAP repair; IC 555 is the printed chip designator, not a course code)")
            results[stem] = "EIC551 exp10 appended"
save(d, stem)

# ---- doc 03: remove garbage NEE row -> re-extract; add NCS151/252 lab row
stem = "03_btech_syllabus_2013-14"
d, full, pa = load(stem)
d, log = common(d, full, pa, stem)
targets = []
for s in d["subjects"]:
    cs = row_codes(s)
    if "NEE101" in cs and not (s.get("units") or s.get("experiments")):
        targets.append((s, 11))
reextract(stem, d, full, targets)
# Computer Programming Lab row (missed: lab page has no Unit markers)
have = {c for s in d["subjects"] for c in row_codes(s)}
if "NCS151" not in have:
    code, obj = me.extract_one(stem + ".pdf",
        "\n\n".join(t for p, t in me.pages_of(full) if 22 <= p <= 23),
        {"file": stem + ".pdf"},
        {"class": "detail", "code_print": "NCS-151/NCS-252", "name_print": "Computer Programming Lab", "page": 22},
        d.get("session", ""), d.get("course", "BTech"))
    if isinstance(obj, list):
        obj = next((x for x in obj if isinstance(x, dict)), {})
    if not obj.get("scheme_row_only"):
        obj["name"] = "Computer Programming Lab"; obj["name_print"] = "Computer Programming Lab"
        obj["codes"] = ["NCS151", "NCS252"]
        obj.setdefault("quirks", []).append("lab detail page prints experiment list (WAP tasks); no Unit theory (print design)")
        obj.setdefault("flags", []).append("experiments_only_no_units")
        d["subjects"].append(obj)
        results[stem] = f"NEE re-extract + NCS lab added ({len(obj.get('experiments') or [])} exps)"
save(d, stem)

# ---- doc 04: orphan strip + compound split; Industrial Chemistry re-extract
stem = "04_btech_textile-chem-texteng-mmft_y2_syllabus_2009-10"
d, full, pa = load(stem)
d, log = common(d, full, pa, stem)
i = full.find("Industrial Chemistry (EC302)")
page = full[:i].count("===== PAGE") if i >= 0 else None
targets = []
for s in d["subjects"]:
    cs = row_codes(s)
    if "EC302" in cs and "Industrial Chemistry" in (s.get("name") or "") and not (s.get("units") or s.get("experiments")):
        targets.append((s, page))
reextract(stem, d, full, targets)
save(d, stem)
results[stem] = f"common repairs ({len(log)}) + industrial-chemistry re-extract"

# ---- docs 05/06/08: scheme-only flags for no-detail lab/training rows
for stem, pat in [("05_btech_textile-chemistry_y2_model-curriculum_2019-20", r"Dyeing|Lab|MOOC"),
                  ("06_btech_textile-chemistry_y2_scheme-syllabus_2017-18", r"Dyeing|Lab"),
                  ("08_btech_textile-chemistry_y4_syllabus-cbcs_2019-20", r"Industrial Training|Project|Lab")]:
    d, full, pa = load(stem)
    n = flag_scheme_only(d, full, stem, pat)
    save(d, stem)
    results[stem] = f"scheme-only flags: {n}"

# ---- docs 07/10: no-code literal flags (common)
for stem in ["07_btech_textile-chemistry_y3_syllabus_2018-19",
             "10_btech_textile-tech_syllabus_2018-19"]:
    d, full, pa = load(stem)
    d, log = common(d, full, pa, stem)
    save(d, stem)
    results[stem] = f"no-code flags ({len(log)} ops)"

# ---- doc 09: AME junk removal; AAS103E + labs re-extract
stem = "09_btech_textile-tech_course-structure_2026-27"
d, full, pa = load(stem)
d, log = common(d, full, pa, stem)
inv = json.load(open(f"{BASE}/inv/{stem}.inv.json"))
targets = []
for s in d["subjects"]:
    cs = row_codes(s)
    nm = (s.get("name") or s.get("name_print") or "")
    if not (s.get("units") or s.get("experiments")):
        if "AAS103E" in cs or "Calculus" in nm:
            targets.append((s, 16))
        elif "AAS151" in cs:
            targets.append((s, next((x["page"] for x in inv if "AAS151" in x.get("code_print", "")), 55)))
        elif "AEE151B" in cs or "AEE251B" in cs:
            targets.append((s, next((x["page"] for x in inv if "AEE151B" in x.get("code_print", "")), 56)))
        elif "AEC151B" in cs or "AEC251B" in cs:
            targets.append((s, next((x["page"] for x in inv if "AEC151B" in x.get("code_print", "")), 57)))
reextract(stem, d, full, targets)
save(d, stem)
results[stem] = f"common repairs ({len(log)}) + {len(targets)} re-extracts"

for k, v in results.items():
    print(f"FIX|{k[:44]}|{v}")
