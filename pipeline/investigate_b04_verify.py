#!/usr/bin/env python3
"""Investigate every B04 verify hard failure with fulltext evidence."""
import json, re, sys

BASE = "/home/z/my-project/work/pipeline_v2"
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())

def pages_of(stem):
    d = json.load(open(f"{BASE}/parsed/{stem}.json"))
    # parsed json structure: list of pages or dict with pages
    if isinstance(d, dict):
        for k in ("pages", "page_texts", "data"):
            if k in d:
                return d[k]
    return d

def page_text(p):
    if isinstance(p, dict):
        return p.get("text") or p.get("content") or ""
    return str(p)

def best_page(needle_norm, pages):
    """find page with max containment of needle via 40-char chunks"""
    best, bi = 0.0, -1
    n = len(needle_norm)
    if n == 0:
        return 0.0, -1
    chunk = needle_norm[:40]
    for i, p in enumerate(pages):
        hay = norm(page_text(p))
        j = hay.find(chunk)
        if j >= 0:
            # extend match length
            k = j
            m = 0
            while k < len(hay) and m < n and hay[k] == needle_norm[m]:
                k += 1; m += 1
            cov = m / n
            if cov > best:
                best, bi = cov, i
    return best, bi

print("========== DRAFT 04 (scheme-syllabus 2026-27) ==========")
d4 = json.load(open(f"{BASE}/drafts_b04_verify/04_bpharm_scheme-syllabus_2026-27.draft.json"))
p4 = pages_of("04_bpharm_scheme-syllabus_2026-27")
print(f"parsed pages: {len(p4)}")
targets4 = ["Drug Store and Business Management (Theory)", "Bio-similars, Vaccines and Macromolecule Sciences (Theory)",
            "Industrial Safety and Waste Management (Theory)", "Internship", "Research Project", "Professional Skills (Practical)"]
for s in d4["subjects"]:
    nm = s["name"]
    if not any(t.lower() in nm.lower() for t in targets4):
        continue
    print(f"\n-- SUBJECT: {nm!r} codes={s.get('codes')} sem={s.get('semester')} ltp={s.get('ltp')}")
    units = s.get("units") or {}
    if isinstance(units, str):
        try: units = json.loads(units.replace("'", '"'))
        except Exception: units = {"?": units}
    for uk, uv in (units.items() if isinstance(units, dict) else []):
        uvn = norm(str(uv))
        cov, pi = best_page(uvn, p4)
        print(f"   unit{uk}: len={len(uvn)} best_containment={cov:.2f} on parsed page idx {pi}")
        print(f"   unit{uk} head: {str(uv)[:180]!r}")
    if not units:
        print("   units: EMPTY — flags:", s.get("flags"), "| quirks:", str(s.get("quirks"))[:200])

print("\n========== DRAFT 06 (y1-4 2019-20) no-units slots ==========")
d6 = json.load(open(f"{BASE}/drafts_b04_verify/06_bpharm_y1-4_syllabus_2019-20.draft.json"))
targets6 = ["HOSPITAL TRAINING-I", "REPORT ON INDUSTRIAL TRAINING", "PRACTICE SCHOOL",
            "HOSPITAL TRAINING-II", "PROJECT WORK", "REPORT ON INDUSTRIAL TOUR"]
for s in d6["subjects"]:
    if not any(t.lower() in s["name"].lower() for t in targets6):
        continue
    units = s.get("units") or {}
    print(f"-- {s['name']!r} codes={s.get('codes')} sem={s.get('semester')} units={units if not isinstance(units, dict) else list(units.keys())}")
    print(f"   flags: {s.get('flags')}")
    print(f"   quirks: {str(s.get('quirks'))[:250]}")

print("\n========== DRAFT 10 (y2 2017-18_2) no-units slot ==========")
d10 = json.load(open(f"{BASE}/drafts_b04_verify/10_bpharm_y2_scheme-syllabus_2017-18_2.draft.json"))
for s in d10["subjects"]:
    if "jurisprudence project" in s["name"].lower():
        print(f"-- {s['name']!r} codes={s.get('codes')} sem={s.get('semester')}")
        print(f"   units: {s.get('units')}")
        print(f"   flags: {s.get('flags')}")
        print(f"   quirks: {str(s.get('quirks'))[:250]}")

print("\n========== FULLTEXT GREP for 04 problem subjects ==========")
ft = open(f"{BASE}/parsed/04_bpharm_scheme-syllabus_2026-27.fulltext.txt").read()
for phrase in ["BIO-SIMILARS", "Biosimilars", "Bio-similars", "DRUG STORE AND BUSINESS", "Drug Store",
               "INDUSTRIAL SAFETY", "Industrial Safety", "PROFESSIONAL SKILLS", "RESEARCH PROJECT", "INTERNSHIP"]:
    idxs = [m.start() for m in re.finditer(re.escape(phrase), ft)]
    print(f"  {phrase!r}: {len(idxs)} hits at {idxs[:6]}")
    for ix in idxs[:2]:
        print(f"     ...{ft[max(0,ix-80):ix+200]!r}...")
