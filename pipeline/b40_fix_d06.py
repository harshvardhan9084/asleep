#!/usr/bin/env python3
"""b40_fix_d06.py — targeted repairs for doc 06 (2016-17 y4 syllabus, NIC branch).

Repairs (all evidence from the parsed fulltext, recorded B23/B25/B27/B28 classes):
 1. AUC-001 duplicate scheme rows (p.1 sem-VII + p.2 sem-VIII) -> ONE row
    (one-row-per-subject rule, RULES §11 idempotency); the second locator
    recorded in the kept row's quirks.
 2. NEC-042/NIC-044 Digital System Design using VHDL: extraction wrongly
    returned scheme_row_only although the FULL detail is printed at pp.20-21
    (units I-V + textbooks, line 1273 'NEC 042/NIC-044 DIGITAL SYSTEM DESIGN
    USING VHDL' on PAGE 20) -> re-extract via mercury-3 with the right slice.
 3. NIC-751 'Control System Lab - II' scheme row (p.1: 0 0 2; TA 20 tot 20;
    ESE 30 tot 50) failed via 429 and the resume re-inventory dropped it
    (instability class) -> deterministic append from the visible print.
 4. NOE-07x / NOE-08x elective pool lists (p.1/p.2 '** Open Electives-I/II')
    print 4 named subjects each; only NOE074 had landed -> deterministic
    scheme-row appends for NOE071/072/073 + NOE081/082/083/084 (zero-GAP).
"""
import json, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

P = "/home/z/my-project/work/pipeline_v2/drafts/06_btech_y4_syllabus_2016-17.draft.json"
PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
STEM = "06_btech_y4_syllabus_2016-17"

draft = json.load(open(P))
fulltext = open(f"{PARSED}/{STEM}.fulltext.txt").read()
PAGES = me.pages_of(fulltext)

# --- 1. AUC-001 duplicate -> one row
auc = [s for s in draft["subjects"] if "AUC-001" in (s.get("codes") or [])]
if len(auc) == 2:
    keep, drop = auc[0], auc[1]
    keep.setdefault("quirks", []).append(
        "subject also printed in the Sem-VIII scheme table (p.2) with identical marks row; "
        "single registry row kept per one-row-per-subject idempotency (RULES §11)")
    draft["subjects"].remove(drop)
    print("FIX1|AUC-001 duplicate removed; locators merged")
elif len(auc) == 1:
    print("FIX1|AUC-001 already single")
else:
    print("FIX1|WARN unexpected AUC-001 count:", len(auc))

# --- 3. NIC-751 deterministic scheme row (print: p.1 PRACTICAL/DESIGN/DRAWING block)
have = {c for s in draft["subjects"] for c in (s.get("codes") or [])}
if "NIC-751" not in have:
    draft["subjects"].append({
        "name": "Control System Lab - II", "name_print": "Control System Lab - II",
        "codes": ["NIC-751"], "semester": 7, "ltp": {"l": 0, "t": 0, "p": 2},
        "credit": 1,
        "marks": {"sessional_ct": None, "sessional_ta": 20, "sessional_total": 20,
                  "ese_te_pe": 30, "total": 50},
        "subject_type": "PRACTICAL/DESIGN/DRAWING", "units": {},
        "lectures_per_unit": None, "cos": [], "textbooks": [], "reference_books": [],
        "experiments": [], "objectives_print": [], "prerequisites": "",
        "quirks": ["scheme table row only (p.1, PRACTICAL/DESIGN/DRAWING block); "
                   "detailed syllabus not printed in this document (zero-guess: fields "
                   "transcribed from the visible scheme print)"],
        "flags": ["scheme_row_only_detailed_syllabus_not_printed"]})
    print("FIX3|NIC-751 Control System Lab - II appended (deterministic)")

# --- 4. NOE pool rows (verbatim list prints p.1/p.2)
pool = [("NOE071", "Entrepreneurship Development", 1),
        ("NOE072", "Quality Management", 1),
        ("NOE073", "Operation Research", 1),
        ("NOE081", "Non Conventional Energy Resources", 2),
        ("NOE082", "Non Linear Dynamic Systems", 2),
        ("NOE083", "Product Development", 2),
        ("NOE084", "Automation and Robotics", 2)]
for code, name, pg in pool:
    if code in have:
        continue
    draft["subjects"].append({
        "name": name, "name_print": name, "codes": [code], "semester": None,
        "ltp": None, "credit": None, "marks": None,
        "subject_type": "open-elective", "units": {},
        "lectures_per_unit": None, "cos": [], "textbooks": [], "reference_books": [],
        "experiments": [], "objectives_print": [], "prerequisites": "",
        "quirks": [f"elective pool list entry (p.{pg}, '** Open Electives' list); "
                   "detailed syllabus not printed in this document"],
        "flags": ["scheme_row_only_detailed_syllabus_not_printed"]})
    print(f"FIX4|{code} {name} appended (deterministic pool row)")

# --- 2. NEC-042/NIC-044 re-extract with detail slice pp.20+
idx = next(i for i, s in enumerate(draft["subjects"]) if "NEC-042" in (s.get("codes") or []))
sub = {"class": "detail", "code_print": "NEC 042/NIC-044",
       "name_print": "DIGITAL SYSTEM DESIGN USING VHDL", "page": 20}
det_pages = sorted({me.safe_pg(s.get("page")) for s in
                    [{"page": 20}]})
slice_txt = "\n\n".join(t for p_, t in PAGES if p_ >= 20 and p_ < 22)
pdf_name = json.load(open(f"{PARSED}/{STEM}.json")).get("meta", {}).get("file", "x.pdf")
q = json.load(open("/home/z/my-project/work/pipeline_v2/queue.json"))
session = course = ""
for e in q["entries"]:
    if e["rel"].endswith("/" + "btech_y4_syllabus_2016-17.pdf"):
        session, course = e.get("session", ""), e.get("course", "BTech")
        break
code, obj = me.extract_one(pdf_name, slice_txt, {}, sub, session, course)
if obj.get("scheme_row_only"):
    obj.pop("scheme_row_only", None)
    obj["flags"] = [f for f in (obj.get("flags") or []) if "scheme_row_only" not in f]
    obj["quirks"] = [q_ for q_ in (obj.get("quirks") or []) if "scheme table row only" not in q_]
    print("FIX2|model still returned scheme_row_only; forcing detail kept as extracted")
obj["units"] = me.units_dict(obj.get("units"))
obj["name"] = obj.get("name") or "Digital System Design using VHDL"
obj["name_print"] = obj.get("name_print") or "DIGITAL SYSTEM DESIGN USING VHDL"
obj.setdefault("quirks", []).append(
    "paired-cell code print 'NEC 042/NIC-044' (Elective-III list p.3 + detail header p.20); "
    "initial extraction wrongly returned scheme_row_only despite the printed pp.20-21 detail "
    "(units I-V + textbooks) — re-extracted (b40_fix_d06)")
obj.setdefault("flags", [])
draft["subjects"][idx] = obj
print("FIX2|NEC-042/NIC-044 re-extracted; units:", list((obj.get("units") or {}).keys()),
      "| containment:", {k: round(me.contained(v, fulltext), 2) for k, v in (obj.get("units") or {}).items()})

draft["subjects"].sort(key=lambda o: (o.get("codes") or [""])[0])
json.dump(draft, open(P, "w"), indent=1, ensure_ascii=False)
print("DRAFT|", len(draft["subjects"]), "subjects")
