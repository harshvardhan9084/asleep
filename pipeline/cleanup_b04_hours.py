#!/usr/bin/env python3
"""B04 verify closeout round 2:
1. All batch04 drafts: unit texts leading with the printed lecture-count cell
   ('10 Hours ...' — 2019-20 doc prints the count at the START of each unit row)
   -> strip the leading fragment from unit text, preserve into
   lectures_per_unit = {'1': N, ...} (CSV-established format from B02 BPharm rows).
2. draft 04: the SECOND BP611P subject (idx order: '(Practical)' appendix detail
   block, p.249-250) gets experiments_only_no_units + empty-printed-list quirk
   (first patch hit the '(elective pool)' entry — same code, two entries).
"""
import json, re

D = "/home/z/my-project/work/pipeline_v2/drafts"
STEMS = [
    "01_bca_y3_syllabus_2026-27", "02_bpharm_ordinances_2019-20",
    "03_bpharm_regulations-ordinances_2026-27", "04_bpharm_scheme-syllabus_2026-27",
    "05_bpharm_y1-2_syllabus_2013-14", "06_bpharm_y1-4_syllabus_2019-20",
    "07_bpharm_y1_scheme_2016-17", "08_bpharm_y1_syllabus_2017-18",
    "09_bpharm_y2_scheme-syllabus_2017-18", "10_bpharm_y2_scheme-syllabus_2017-18_2",
]
LEAD = re.compile(r"^\s*(\d{1,3})\s*hours?\s+", re.I)

tot_units, tot_stripped = 0, 0
for stem in STEMS:
    p = f"{D}/{stem}.draft.json"
    doc = json.load(open(p))
    n_stripped, subjects_touched = 0, 0
    for s in doc.get("subjects", []):
        units = s.get("units")
        if not isinstance(units, dict) or not units:
            continue
        lpu = {}
        new_units = {}
        touched = False
        for uk, ut in sorted(units.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 99):
            tot_units += 1
            t = str(ut)
            m = LEAD.match(t)
            if m:
                lpu[str(uk)] = int(m.group(1))
                t2 = t[m.end():]
                if t2.strip():
                    new_units[str(uk)] = t2
                    tot_stripped += 1
                    n_stripped += 1
                else:
                    new_units[str(uk)] = t2  # pure count: keep empty (flagged if verify complains)
                touched = True
            else:
                new_units[str(uk)] = t
        if touched:
            s["units"] = new_units
            existing = s.get("lectures_per_unit")
            if not existing and lpu:
                s["lectures_per_unit"] = str(lpu)
            subjects_touched += 1
            resid = sum(1 for v in new_units.values() if re.search(r"\d{1,3}\s*hours\b", str(v), re.I))
            if resid:
                print(f"  NOTE {stem} {s['name']!r}: {resid} unit(s) still contain mid-text 'N hours' (left as printed)")
    if n_stripped:
        with open(p, "w") as f:
            json.dump(doc, f, indent=1, ensure_ascii=False)
        print(f"{stem}: stripped leading-hours from {n_stripped} units in {subjects_touched} subjects")

# ---- 2: draft 04 second BP611P ('(Practical)' detail block) ----
p4 = f"{D}/04_bpharm_scheme-syllabus_2026-27.draft.json"
d4 = json.load(open(p4))
hits = [s for s in d4["subjects"] if s.get("name") == "Professional Skills (Practical)"]
print(f"\n04 'Professional Skills (Practical)' entries: {len(hits)}")
for s in hits:
    fl = s.setdefault("flags", [])
    if not any("experiments_only_no_units" in str(f) for f in fl):
        fl.append("experiments_only_no_units")
    q = ("Print shows 'Detailed Syllabus / List of Practical / (Perform any 12 Experiments)' with NO experiment "
         "items printed — the printed experiment list is empty in the source document (printed p.250); the "
         "Recommended References follow immediately. Nothing to parse: zero-guess rule forbids inventing experiments.")
    if q not in (s.get("quirks") or []):
        s.setdefault("quirks", []).append(q)
    print("  fixed entry flags:", fl)
with open(p4, "w") as f:
    json.dump(d4, f, indent=1, ensure_ascii=False)

print(f"\nTOTAL: {tot_stripped}/{tot_units} unit texts stripped")
print("CLEANUP DONE")
