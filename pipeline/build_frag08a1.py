#!/usr/bin/env python3
"""build_frag08a1.py — doc08 slice A1 (pages 1-5) fragments, hand-extracted by the
main agent after 10 subagent transport failures on this doc (RULES §8 degradation,
recorded in worklog). Verbatim strings transcribed from the parsed text layer of
staging/batch25/08_btech_env_y3_scheme-syllabus_2018-19.pdf (sha16 332ce6312d25dcd7).
Every string is containment-checked against the parsed fulltext before writing.
Covers: cover (p.1), Sem-V scheme table (p.2, 10 rows + TOTAL), REV501 (p.3-4),
REV502 (p.4 + books 6-7 at p.5 top). REV503+ belongs to slice A2 (frag08a2).
"""
import json, os, re, sys

FT = "/home/z/my-project/work/pipeline_v2/parsed/08_btech_env_y3_scheme-syllabus_2018-19.fulltext.txt"
OUT = "/home/z/my-project/work/pipeline_v2/drafts/B25/frag08a1"

def norm(s):
    return re.sub(r"\s+", "", s).lower()

full = norm(open(FT, encoding="utf-8").read())

def check(label, s):
    n = norm(s)
    if n not in full:
        print(f"CONTAINMENT-FAIL {label}: {s[:80]!r}")
        return False
    return True

REV501_UNITS = {
 "1": "Air pollution: composition and structure of atmosphere, global implications of air pollution. Classification of air pollutants: particulates, hydrocarbon, carbon monoxide, oxides of sulphur, oxides of nitrogen and photo chemical oxidants. Indoor air pollution, Effects of air pollutants on humans, animals, property and plants. [8]",
 "2": "Air pollution chemistry, meteorological aspects of air pollution dispersion; temperature lapse rate and stability, wind velocity and turbulence, plume behaviour, dispersion of air pollutants, the Gaussian Plume Model, stack height and dispersion. [8]",
 "3": "Ambient air quality and standards, air sampling and measurements; Ambient air sampling, collection of gaseous air pollutants, collection of particulate air pollutants, stack sampling. Control devices for particulate contaminants: gravitational settling chambers, yclonee separators, wet collectors, fabric filters (Bag-house filter), electrostatic precipitators (ESP). [8]",
 "4": "Control of gaseous contaminants: Absorption, Adsorption, Condensation and Combustion, Control of sulphur oxides, nitrogen oxides, carbon monoxide, and hydro carbons. Automotive emission control, catalytic convertor, Euro-I, Euro-II and Euro-III specifications, Indian specifications. [8]",
 "5": "NOISE POLLUTION: Basics of acoustics and specification of sound; sound power, sound intensity and sound pressure levels; plane, point and line sources, multiple sources; outdoor and indoor noise propagation; psycho-acoustics and noise criteria, effects of noise on health, annoyance rating schemes; special noise environments: Infra-sound, ultrasound, impulsive sound and sonic boom; noise standards and limit values; noise instrumentation and monitoring procedure. Noise indices. [8]",
}
REV501_REFS = [
 "Peavy, Rowe and Tchobanoglous: Environmental Engineering.",
 "Martin Crawford: Air Pollution Control Theory.",
 "Warkand Warner: Air Pollution: Its Origin and Control.",
 "Rao and Rao: Air Pollution Control Engineering.",
 "Keshav Kant and Rajni Kant, \"Air Pollution and Control Engineering\", Khanna Publishing House.",
 "Environmental Pollution Control Engineering-CS Rao, Wiley Eastern Ltd., New Delhi, 1996.",
 "C.S. Rao, Air pollutionand control",
 "Environmental Noise Pollution \u2013 PE Cunniff, McGraw Hill, New York, 1987",
 "Nevers: Air Pollution Control Engineering.",
 "M. P. Poonia and S C Sharma,\" Environmental Engineering, Khanna Publishing House.",
 "My cock, Mc Kenna and Theodore: Handbook of Air Pollution Control Engineering and Technology. Suess and Crax ford: W.H.O. Manualon Urban Air Quality Management",
 "OP Gupta,Elements of Environmental Polluton Control, Khanna Publishing House.",
]
REV502_UNITS = {
 "1": "Concrete technology: Constituent materials and their Properties, Fresh concrete, Work ability, strength, elasticity and fracture of hardened concrete, Time dependent properties of concrete, Durability of concrete, concrete and mixtures, Mix design methods, BIS code provisions, Special concretes. Introduction to various design philosophies, Assumptions in working stress and limit state design method, Factor of safety applied to different materials, IS-456 provisions, Load consideration for design of concrete structures as per relevant IS code. [8]",
 "2": "Beam design by limit state: Moment of resistance of a beam of rectangular and flange section and their design using limit state, Spacing of vertical and inclined stirrups, Development length of reinforcement, Detailing of reinforcement as per IS-456 and IS-13920. [8]",
 "3": "Column design by limit state: Short column under axial loading and uni-axial bending, column with epical reinforcement. Detailing of reinforcement as per IS-456 and IS-13920. Solid Slab design using limit state: Design of one way and two way slab. [8]",
 "4": "Retaining wall: Structural behaviour, stability of retaining wall against over turning and sliding, Design of T-shaped retaining wall, Concept of counter for retaining wall. [8]",
 "5": "Water Tanks: Design of circular and rectangular tanks situated on the ground, underground and over head tanks. [8]",
}
REV502_NOTE = "Note: The students should be given a comprehensive problem at the end which requires inputs/ knowledge/ application from all the units of the syllabus. It may be evaluated as a part of TA."
REV502_BOOKS = [
 "Jain ,O.P. & Krishna, J.\u201cPlain and Reinforced Concrete, Vol. I & II\u201d, Nem Chand & Bros.",
 "Dayaratnam, P. \u201cReinforced Concrete Design\u201d, Oxford & IBH.",
 "Sinha, S.N.  \u201cReinforced Concrete Design\u2019\u2019, Mc- Graw Hill.",
 "Pillai, S.U.  & Menon, D.  \u201cReinforced Concrete Design, Mc- Graw Hill.",
 "Gambhir, M.L. \u201cFundamentals of Reinforced Concrete Design\u201d, PHI Learning.",
 "Park ,R. and Pauley,  T. \u201cReinforced Concrete Structures\u201d, John Wiley.",
 "IS: 456\u20132000: Code of Practice for Plain and Reinforced Concrete, Bureau of Indian Standards.",
]

ok = True
for k, v in REV501_UNITS.items():
    ok &= check(f"REV501-unit{k}", v)
for i, b in enumerate(REV501_REFS, 1):
    ok &= check(f"REV501-ref{i}", b)
for k, v in REV502_UNITS.items():
    ok &= check(f"REV502-unit{k}", v)
ok &= check("REV502-note", REV502_NOTE)
for i, b in enumerate(REV502_BOOKS, 1):
    ok &= check(f"REV502-book{i}", b)
# scheme table row probes
for probe in ["MANEGIRIAL ECONOMICS", "SOCIOLOGY /CYBER SECURITY", "AIR AND NOISE POLLUTION CONTROL ENGINEERING",
              "DESIGN OF CONCRETE STRUCTURE", "SOLID WASTE MANAGEMENT", "ELECTIVE -1", "BUILDING PLANNING AND DRAWING LAB"]:
    ok &= check(f"scheme:{probe}", probe)
if not ok:
    print("ABORT: containment failures — fragments not written")
    sys.exit(2)

os.makedirs(OUT, exist_ok=True)

s1 = {
 "name": "Air and Noise Pollution and Control Engineering",
 "name_print": "REV 501: Air and Noise Pollution and Control Engineering",
 "codes": ["REV 501", "REV501"],
 "semester": 5,
 "ltp": {"l": 3, "t": 0, "p": 0},
 "credit": 3,
 "marks": {"sessional_ct": 20, "sessional_ta": 10, "sessional_total": 30, "ese_te_pe": 70, "total": 100},
 "subject_type": "core",
 "units": REV501_UNITS,
 "reference_books": [{"no": i, "book": b} for i, b in enumerate(REV501_REFS, 1)],
 "quirks": [
   "unit-III prints 'yclonee separators' (cyclone) — kept verbatim",
   "ref 3 prints 'Warkand Warner' (Wark and Warner) — kept verbatim",
   "ref 11 prints 'My cock, Mc Kenna and Theodore' and 'Manualon Urban Air Quality Management' and 'Crax ford' — page-image check confirms these are the printed forms (likely Mycock/McKenna/Manual-on/Craxford); kept verbatim",
   "ref list prints item '10.' a second time for OP Gupta after item 11 — duplicated ordinal kept verbatim",
   "no COs/K-levels/objectives/eligibility printed anywhere in this 2018-19 doc — omitted per printed-blank",
 ],
 "flags": [],
}
s2 = {
 "name": "Design of Concrete Structures",
 "name_print": "REV 502:       Design of Concrete Structures",
 "codes": ["REV 502", "REV502"],
 "semester": 5,
 "ltp": {"l": 3, "t": 1, "p": 0},
 "credit": 4,
 "marks": {"sessional_ct": 20, "sessional_ta": 10, "sessional_total": 30, "ese_te_pe": 70, "total": 100},
 "subject_type": "core",
 "units": REV502_UNITS,
 "note_print": REV502_NOTE,
 "textbooks": [{"no": i, "book": b} for i, b in enumerate(REV502_BOOKS[:5], 1)],
 "reference_books": [{"no": i, "book": b} for i, b in enumerate(REV502_BOOKS[5:], 6)],
 "quirks": [
   "unit texts head 'Unit 1'..'Unit 5' (digit form) unlike REV501's roman-unit form",
   "book list headed 'Books' (single list 1-7 spanning pp.4-5; items 6-7 print at p.5 top)",
   "book 1/3/4 quote-glyph mix (\u201c vs \u2019\u2019) kept verbatim",
   "no COs/K-levels/objectives/eligibility printed anywhere — omitted per printed-blank",
 ],
 "flags": [],
}
NSR = [
 {"kind": "cover", "print": "DR. A.P.J ABDUL KALAM TECHNICAL UNIVERSITY, LUCKNOW — EVALUATION SCHEME & SYLLABUS FOR B. TECH. III YEAR (ENVIRONMENTAL ENGINEERING) On Choice Based Credit System [Effective from session 2018-19]", "locator": "p.1"},
 {"kind": "scheme_table_row", "print": "1 | RAS501 | MANEGIRIAL ECONOMICS | Applied Science | 3—0---0 | 70 20 10 100 | 3", "locator": "p.2 (scheme row: scheme-only subject RAS501, no detail page)"},
 {"kind": "scheme_table_row", "print": "2 | RAS502/RUC501 | SOCIOLOGY /CYBER SECURITY | Applied Science | 3—0---0 | 70 20 10 100 | 3", "locator": "p.2 (scheme row: scheme-only subjects RAS502/RUC501)"},
 {"kind": "scheme_table_row", "print": "3 | REV 501 | AIR AND NOISE POLLUTION CONTROL ENGINEERING | Core Deptt. | 3—0---0 | 70 20 10 100 | 3", "locator": "p.2"},
 {"kind": "scheme_table_row", "print": "4 | REV 502 | DESIGN OF CONCRETE STRUCTURE | Core Deptt. | 3—1---0 | 70 20 10 100 | 4", "locator": "p.2"},
 {"kind": "scheme_table_row", "print": "5 | REV 503 | SOLID WASTE MANAGEMENT | Core Deptt. | 3—0---0 | 70 20 10 100 | 3", "locator": "p.2"},
 {"kind": "scheme_table_row", "print": "6 | RCE 051 RCE052 RCE 053 | ELECTIVE -1 MODERN CONSTRUCTION MATERIALS CONCRETE TECHNOLOGY GEOENVIRONMENTAL ENGINEERING | Core Deptt. | 3—1--0 | 70 20 10 100 | 4", "locator": "p.2 (elective slot: scheme prints RCE 051/052/053; detail pages print RCE 011/012/013)"},
 {"kind": "scheme_table_row", "print": "7 | REV 551 | AIR POLLUTION CONTROL ENGINEERING LAB | Core Deptt. | 0—0---2 | 50 50 100 | 1", "locator": "p.2"},
 {"kind": "scheme_table_row", "print": "8 | REV 552 | ENVIRONMENTAL SANITATION LAB | Core Deptt. | 0—0---2 | 50 50 100 | 1", "locator": "p.2"},
 {"kind": "scheme_table_row", "print": "9 | REV 553 | SOLID WASTE MANAGEMENT LAB | Core Deptt. | 0—0---2 | 50 50 100 | 1", "locator": "p.2"},
 {"kind": "scheme_table_row", "print": "10 | REV 554 | BUILDING PLANNING AND DRAWING LAB | Core Deptt. | 0—0---2 | 50 50 100 | 1", "locator": "p.2"},
 {"kind": "scheme_total_row", "print": "TOTAL 620 120 260 1000 24", "locator": "p.2"},
 {"kind": "scheme_header", "print": "FIFTH SEMESTER ENVIRONMENTAL ENGINEERING SESSION 2018-19", "locator": "p.2"},
]
QF = {
 "quirks": [
   "scheme p.2 header prints 'MANEGIRIAL ECONOMICS' (Managerial) — kept verbatim",
   "scheme L-T-P column prints em-dash runs ('3—0---0') — kept verbatim",
   "scheme table subject codes print spaced forms ('REV 501') while detail headers also print spaced forms; elective slot prints RCE 051/RCE052/RCE 053 but detail pages print RCE 011/012/013 (slice-A2 evidence)",
   "cover prints 'DR. A.P.J ABDUL KALAM TECHNICAL UNIVERSITY, LUCKNOW' with dotted abbreviation kept verbatim",
   "REV502 unit-1 runs 'concrete and mixtures, Mix design methods' — print as-is",
 ],
 "flags": [
   "SCHEME-ONLY-SUBJECTS: RAS501, RAS502/RUC501 (no detail pages printed) — recorded as scheme rows only, per zero-guessing",
   "ELECTIVE-CODES-SCHEME-VS-DETAIL: scheme RCE 051/052/053 vs detail RCE 011/012/013 (A2 slice evidence) — both prints recorded",
   "lab CT-column blank in scheme rows 7-10 (ESE 50 + sessional 50 = 100 printed) — slice-A2 evidence",
 ],
}

json.dump(s1, open(f"{OUT}/s1_REV501.json", "w"), indent=1, ensure_ascii=False)
json.dump(s2, open(f"{OUT}/s2_REV502.json", "w"), indent=1, ensure_ascii=False)
json.dump(NSR, open(f"{OUT}/nsr.json", "w"), indent=1, ensure_ascii=False)
json.dump(QF, open(f"{OUT}/quirks_flags.json", "w"), indent=1, ensure_ascii=False)
print("WROTE", OUT, "subjects=2 nsr=", len(NSR))
