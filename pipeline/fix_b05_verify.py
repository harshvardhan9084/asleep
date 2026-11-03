#!/usr/bin/env python3
"""B05 verify-closeout fixes — every edit evidence-backed:

F1. draft 01 (BPharm y2 2019-20): 45 unit texts carry the printed unit-cell
    furniture ('Unit III' row label + '10 Hours' lecture count + Wingdings
    \\uf0b7 bullet chars) — strip the leading label/count (hours ->
    lectures_per_unit, CSV-established dict format) and the \\uf0b7 decode
    artifacts; topics text verbatim-unchanged.
F2. draft 07 (BTech AE 2020-21): leading '(8 Hours)' parenthesized
    lecture-count fragments — same treatment.
F3. draft 02 (BPharm y3): MedChem-III unit5 — text layer scrambles line order
    ('of combinatorial' extracted AFTER 'chemistry: solid phase...'); PAGE
    IMAGE (drafts/_b05s02_medchem-22.png, printed p.22) confirms the visual
    print reads the draft's logical order — evidence quirk recorded (RULES §6).
F4. draft 10: BAE057 CO1 dropped one printed 's' (draft 'loadeffects' vs print
    'loadseffects') — restored verbatim (kerning-collapse artifact already
    quirked by the extraction agent).
F5. detailed_syllabus_not_printed flags for scheme-row-only slots confirmed by
    fulltext (no detail blocks anywhere in the docs):
    03: RPH-843(C)P Clinical Pharmacy Project (print gives 'Projects based on-' list)
    04: BP706PS / BP707P / BP814PW / BP815P
    05: BEC554 Mini Project + BNC501/BNC502/BNC601/BNC602
    09: RAS501 / RAS502+RUC501 / RAE559 / RAS601 / RAS602+RUC601
    10: Mini Project or Internship Assessment + BNC501/BNC502/BNC601/BNC602 rows
"""
import json, re

D = "/home/z/my-project/work/pipeline_v2/drafts"

def load(stem):
    return json.load(open(f"{D}/{stem}.draft.json"))

def save(stem, doc):
    json.dump(doc, open(f"{D}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)

UNIT_LABEL = re.compile(r"^\s*Unit\s+[IVXivx0-9]{1,4}\b[^\n]*\n+", re.I)
HOURS_LINE = re.compile(r"^\s*[\(\[]?\s*(\d{1,3})\s*Hours\s*[\)\]]?\s*", re.I)
HOURS_PAREN = re.compile(r"^\s*\(\s*(\d{1,3})\s*Hours\s*\)\s*", re.I)

# ---- F1: draft 01 ----
d1 = load("01_bpharm_y2_syllabus_2019-20")
n_units, n_bullets = 0, 0
for s in d1["subjects"]:
    units = s.get("units") or {}
    if not isinstance(units, dict) or not units:
        continue
    lpu, new_units, touched = {}, {}, False
    for uk in sorted(units, key=lambda x: int(x) if str(x).isdigit() else 99):
        t = str(units[uk])
        orig = t
        m_hours = None
        m_lab = UNIT_LABEL.match(t)
        if m_lab:
            t = t[m_lab.end():]
        m_hours = HOURS_LINE.match(t) or HOURS_PAREN.match(t)
        if m_hours:
            lpu[str(uk)] = int(m_hours.group(1))
            t = t[m_hours.end():]
        # strip Wingdings bullet chars anywhere (decode artifact of printed bullets)
        if "\uf0b7" in t:
            n_bullets += t.count("\uf0b7")
            t = t.replace("\uf0b7", "")
        if t != orig:
            new_units[str(uk)] = t.strip()
            touched = True
            n_units += 1
        else:
            new_units[str(uk)] = t
    if touched:
        s["units"] = new_units
        if not s.get("lectures_per_unit") and lpu:
            s["lectures_per_unit"] = str(lpu)
q1 = d1.setdefault("quirks", [])
Q1 = ("Unit-table furniture normalized per RULES §7/B04 precedent: leading 'Unit <roman>' row labels and "
      "'<N> Hours' lecture-count cells moved from unit texts to lectures_per_unit (CSV-established dict "
      "format); Wingdings \\uf0b7 bullet decode artifacts (printed bullets) removed from unit texts — "
      "topic prose kept verbatim.")
if Q1 not in q1:
    q1.append(Q1)
save("01_bpharm_y2_syllabus_2019-20", d1)
print(f"F1 draft 01: {n_units} unit texts normalized, {n_bullets} bullet artifacts removed")

# ---- F2: draft 07 ----
d7 = load("07_btech_ae_syllabus_2020-21")
n7 = 0
for s in d7["subjects"]:
    units = s.get("units") or {}
    if not isinstance(units, dict) or not units:
        continue
    lpu, new_units, touched = {}, {}, False
    for uk in sorted(units, key=lambda x: int(x) if str(x).isdigit() else 99):
        t = str(units[uk])
        m = HOURS_PAREN.match(t) or HOURS_LINE.match(t)
        if m:
            lpu[str(uk)] = int(m.group(1))
            new_units[str(uk)] = t[m.end():].strip()
            touched = True
            n7 += 1
        else:
            new_units[str(uk)] = t
    if touched:
        s["units"] = new_units
        if not s.get("lectures_per_unit") and lpu:
            s["lectures_per_unit"] = str(lpu)
q7 = d7.setdefault("quirks", [])
Q7 = ("Leading '(N Hours)' lecture-count cells moved from unit texts to lectures_per_unit "
      "(CSV-established dict format; 2020-21 doc prints the count parenthesized at unit-row start) — "
      "topic prose kept verbatim.")
if Q7 not in q7:
    q7.append(Q7)
save("07_btech_ae_syllabus_2020-21", d7)
print(f"F2 draft 07: {n7} unit texts normalized")

# ---- F3: draft 02 MedChem-III u5 evidence quirk ----
d2 = load("02_bpharm_y3_syllabus_2019-20")
s2 = [x for x in d2["subjects"] if "MEDICINAL CHEMISTRY" in str(x.get("name", "")).upper()
      and "III" in str(x.get("name", ""))][0]
q2 = s2.setdefault("quirks", [])
Q2 = ("unit5 tail: text layer scrambles line order — 'of combinatorial' is extracted AFTER 'chemistry: "
      "solid phase and solution phase synthesis.'; PAGE IMAGE (drafts/_b05s02_medchem-22.png, printed "
      "p.22) per RULES §6 confirms the visible print reads 'Combinatorial Chemistry: Concept and "
      "applications of combinatorial chemistry: solid phase and solution phase synthesis.' — unit text "
      "keeps the visual-print reading order.")
if Q2 not in q2:
    q2.append(Q2)
save("02_bpharm_y3_syllabus_2019-20", d2)
print("F3 draft 02: MedChem-III u5 line-reorder evidence quirk recorded")

# ---- F4: draft 10 BAE057 CO1 ----
d10 = load("10_btech_ae_y3_syllabus_2024-25")
s10 = [x for x in d10["subjects"] if "aircraft design" in str(x.get("name", "")).lower()][0]
fixed = False
for c in s10.get("cos") or []:
    t = str(c.get("text", ""))
    if "balancingloadeffects" in t.replace(" ", "").lower() and "balancingloadseffects" not in t.replace(" ", "").lower():
        # print (text layer, kerned): ...balancingloadseffectsonaircraft...
        c["text"] = t.replace("loadeffects", "loadseffects", 1)
        fixed = True
print(f"F4 draft 10: BAE057 CO1 's' restored: {fixed}")
save("10_btech_ae_y3_syllabus_2024-25", d10)

# ---- F5: scheme-row-only flags ----
def flag_by_code(doc, code_tokens, extra_note=""):
    hit = []
    for s in doc["subjects"]:
        cs = {str(c).replace("-", "").replace(" ", "").upper() for c in (s.get("codes") or [])}
        if cs & {c.replace("-", "").replace(" ", "").upper() for c in code_tokens}:
            fl = s.setdefault("flags", [])
            tok = "detailed_syllabus_not_printed: print gives scheme-table row(s) only — no unit/experiment detail block anywhere in this document" + extra_note
            if not any("detailed_syllabus_not_printed" in str(f) for f in fl):
                fl.append(tok)
            hit.append(s.get("codes"))
    return hit

specs = [
    ("03_bpharm_y4_syllabus-cbcs_2019-20", [["RPH843CP"]], " (project slot prints a 'Projects based on-' description list, no numbered unit/practical table)"),
    ("04_bpharm_y4_syllabus-rev_2020-21", [["BP706PS"], ["BP707P"], ["BP814PW"], ["BP815P"]], ""),
    ("05_btech_act_y3_syllabus-rev_2025-26", [["BEC554"], ["BNC501"], ["BNC502"], ["BNC601"], ["BNC602"]], " (non-credit audit / mini-project scheme rows)"),
    ("09_btech_ae_y3_syllabus_2018-19", [["RAS501"], ["RAS502", "RUC501"], ["RAE559"], ["RAS601"], ["RAS602", "RUC601"]], ""),
    ("10_btech_ae_y3_syllabus_2024-25", [["BAE553"], ["BNC501"], ["BNC502"], ["BNC601"], ["BNC602"]], " (non-credit audit / mini-project scheme rows)"),
]
for stem, code_groups, note in specs:
    doc = load(stem)
    for group in code_groups:
        hits = flag_by_code(doc, group, note)
        print(f"F5 {stem} {group}: matched {hits if hits else 'NONE — CHECK'}")
    save(stem, doc)
print("FIXES DONE")
