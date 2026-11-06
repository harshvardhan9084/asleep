#!/usr/bin/env python3
"""adjudicate_b40.py — inject the B40 TIER2_OVERRIDES adjudications into
merge_draft.py (marker: adjudicate_b40). Every entry is evidence-recorded
(registry row + parsed fulltext verified before writing). All 14 TIER2 flags
resolve as same-subject ALLOWs; the 2 CODE-REASSIGNED-ACROSS-SESSIONS flags
run via the pre-adjudicated RESOLVE_APPEND executor."""
import json

rep = json.load(open("/home/z/my-project/work/pipeline_v2/decisions_report.json"))
keys = sorted({k for k, c, i in rep["flags"] if c.startswith("TIER2")})
assert len(keys) == 14, keys

ALLOW_GENERIC = ("B40 TIER2 same-subject ALLOW ({ev}): the draft unit-I is a verbatim print of the "
                 "target row's unit-I (the '{row}' accumulator, owner of {codes}); the name delta is the "
                 "recorded print-variance class ({varclass}). The draft's OE codes are unowned in BTech so "
                 "they accumulate cleanly (G2).")

EV = {
    "02_btech_y3s6_open-elective-1-aicte_2020-21::00::embedded-system": {
        "action": "ALLOW",
        "reason": ("B40 TIER2 same-subject ALLOW (fuzzy 97, overlap 28; name-identity + era-rewording class): "
                   "draft 'EMBEDDED SYSTEM' (KOE-062, 2020-21 AICTE OE-I print) vs the embedded-systems row "
                   "'Embedded Systems' (NCS-087;RCS070;KEN-062;BEN062;EEC-047;ECS-083, sess 2016-17) — singular/"
                   "plural print variance (recorded B29/B33 class) and the row is ALREADY the multi-era multi-branch "
                   "Embedded Systems accumulator (6 codes across IT/CEC/EI eras). Unit-I is era-reworded, not a "
                   "different course: the 2020-21 print ('The build process for embedded systems, Structural units in "
                   "Embedded processor, selection of processor') vs the 2016-17 print ('Classification, Characteristics "
                   "and requirements, Applications') are two treatments of the same university OE course — the recorded "
                   "B39 ITC REC406 era-rewording precedent ('the multi-era accumulator, era rewording not a different "
                   "subject'); 28 shared distinctive domain terms pass the §2 overlap threshold. Newest-session fieldwise "
                   "(2020-21 ≥ 2016-17, RULES §3): the row's units update to the 2020-21 print; the older print "
                   "corroborates in source_history. KOE-062/KOE062 unowned in BTech, accumulates cleanly.")},
    "02_btech_y3s6_open-elective-1-aicte_2020-21::07::gis-remote-sensing": {
        "action": "ALLOW",
        "reason": ("B40 TIER2 same-subject ALLOW (fuzzy 90, overlap 108): draft 'GIS & REMOTE SENSING' (KOE-066/"
                   "KOE066, 2020-21 AICTE OE-I print) vs the remote-sensing-and-gis row 'Remote Sensing and GIS' "
                   "(KAG-062;RAG070, sess 2020-21) — word-order + '&'/and print-variance class (recorded B29/B33); "
                   "unit-I VERBATIM ('Basic component of remote sensing (RS), advantages and limitations of RS, possible "
                   "use of RS techniques in assessment and monitoring of land and water resources...'). KOE066 unowned, "
                   "accumulates cleanly.")},
    "02_btech_y3s6_open-elective-1-aicte_2020-21::08::real-time-systems": {
        "action": "ALLOW",
        "reason": ("B40 TIER2 same-subject ALLOW (fuzzy 97, overlap 105): draft 'REAL TIME SYSTEMS' (KOE-061, 2020-21 "
                   "AICTE OE-I print) vs the real-time-system row 'Real Time System' (NCS-082;KCS-063;NEC013R;REC053;"
                   "ECS-081, sess 2016-17) — plural print variance (recorded class); unit-I VERBATIM ('Definition, "
                   "Typical Real Time Applications: Digital Control, High Level Controls, Signal Processing etc., Release "
                   "Times, Dead-lines, and Timing Constraints...'). KOE-061 unowned, accumulates cleanly.")},
    "03_btech_y3s6_open-elective-1_2020-21::01::real-time-systems": {
        "action": "ALLOW",
        "reason": ("B40 TIER2 same-subject ALLOW (fuzzy 97, overlap 105): same row + class as 02::08 — the non-AICTE "
                   "2020-21 OE-I doc prints the identical KOE-061 'REAL TIME SYSTEMS' course with identical unit-I "
                   "(corroborating copy of the AICTE wave). KOE-061 accumulates on the same real-time-system row.")},
    "03_btech_y3s6_open-elective-1_2020-21::08::embedded-system": {
        "action": "ALLOW",
        "reason": ("B40 TIER2 same-subject ALLOW (fuzzy 97, overlap 28): same row + class as 02::00 — the non-AICTE "
                   "2020-21 doc prints the identical KOE-062 'EMBEDDED SYSTEM' course (corroborating copy); era-rewording "
                   "precented, newest-session fieldwise updates the units.")},
    "03_btech_y3s6_open-elective-1_2020-21::09::gis-remote-sensing": {
        "action": "ALLOW",
        "reason": ("B40 TIER2 same-subject ALLOW (fuzzy 90, overlap 108): same row + class as 02::07 — the non-AICTE "
                   "2020-21 doc prints the identical KOE-066 'GIS & REMOTE SENSING' course with identical unit-I "
                   "(corroborating copy).")},
    "04_btech_y3s6_open-elective-1_2024-25::05::embedded-system": {
        "action": "ALLOW",
        "reason": ("B40 TIER2 same-subject ALLOW (fuzzy 97, overlap 28): same row + class as 02::00 — the 2024-25 NEP "
                   "doc prints the identical course as BOE-062 'EMBEDDED SYSTEM' (B-era reprint of the KOE-062 syllabus); "
                   "BOE-062 unowned, accumulates on the embedded-systems accumulator; 2024-25 is the newest session so "
                   "its print wins fieldwise.")},
    "04_btech_y3s6_open-elective-1_2024-25::07::gis-remote-sensing": {
        "action": "ALLOW",
        "reason": ("B40 TIER2 same-subject ALLOW (fuzzy 90, overlap 108): same row + class as 02::07 — the 2024-25 NEP "
                   "doc prints the identical course as BOE-066 'GIS & REMOTE SENSING'; BOE-066 unowned, accumulates.")},
    "05_btech_y4_open-electives_2020-21::03::computerized-process-control": {
        "action": "ALLOW",
        "reason": ("B40 TIER2 same-subject ALLOW (fuzzy 96, overlap 82): draft 'COMPUTERIZED PROCESS CONTROL' (ROE-076, "
                   "2020-21 y4 OE print) vs the computerised-process-control row 'Computerised Process Control' "
                   "(REC078;KIC077;EIC-031, sess 2019-20) — z/s spelling print variance (recorded keep-print-verbatim "
                   "class); unit-I VERBATIM ('Basics of Computer-Aided Process Control: Role of computers in process "
                   "control, Elements of a computer aided Process control System...'). ROE-076 unowned, accumulates.")},
    "05_btech_y4_open-electives_2020-21::06::gis-remote-sensing": {
        "action": "ALLOW",
        "reason": ("B40 TIER2 same-subject ALLOW (fuzzy 90, overlap 108): same row + class as 02::07 — the 2020-21 y4 "
                   "OE doc prints the identical course as ROE-079 'GIS & REMOTE SENSING' with identical unit-I; ROE-079 "
                   "unowned, accumulates.")},
    "06_btech_y4_syllabus_2016-17::20::biomedical-signal-processing": {
        "action": "ALLOW",
        "reason": ("B40 TIER2 same-subject ALLOW (fuzzy 98, overlap 88): draft 'Biomedical Signal Processing' (NIC041, "
                   "2016-17 NIC DE-III print) vs the bio-medical-signal-processing row 'BIO-MEDICAL SIGNAL PROCESSING' "
                   "(EBM-603;RBM602;BEC-056;RIC080;EIC-032;BIC-062, sess 2010-11) — hyphen print variance (recorded "
                   "class); unit-I VERBATIM ('Introduction to Bio-Medical Signals: Classification, Acquisition and "
                   "Difficulties during Acquisition. Basics of Electrocardiography, Electroencephalography, "
                   "Electromyogr...'). NIC041 unowned, accumulates cleanly.")},
    "08_btech_y4_syllabus_2025-26::03::ai-in-bio-medical-instrumentation": {
        "action": "ALLOW",
        "reason": ("B40 TIER2 same-subject ALLOW (fuzzy 90, overlap 46; same-core restructuring class): draft 'AI in "
                   "Bio-Medical Instrumentation' (BIC701, 2025-26 NEP ICE sem-7 DE print) vs the bio-medical-"
                   "instrumentation row 'Bio-Medical Instrumentation' (REE062;KEN051;EIC-802, sess 2018-19). Unit-by-unit: "
                   "u2 'Introduction of Bio-Medical Instrumentation System: Man-Instrumentation system Components, "
                   "Problems encountered in measuring a living system... Bioelectric potentials' and u3 'Cardiovascular "
                   "Measurements: Electrocardiography – ECG amplifiers, Electrodes and Leads... Holter recording, Blood "
                   "pressure' share the classical BMI core with the row's u1/u2 prints; u4 Spirometer/respiratory and u5 "
                   "Ophthalmoscope/Tonometer are the classical measurement topics of the row's u3/u5 territory with "
                   "AI-powered equipment ADDITIONS; u1 is the new AI-introduction module of the 2025-26 restructure. "
                   "This is the university's AI-restructured successor of the same DE-slot course (era-restructure "
                   "variant of the B39 ITC era-rewording precedent), not a different subject sharing a skeleton — the "
                   "name's substantive token core ('Bio Medical Instrumentation') is identical and the majority of unit "
                   "vocabulary is the BMI measurement canon. Newest-session fieldwise (2025-26 ≥ 2018-19, RULES §3): "
                   "units update to the 2025-26 print; the 2018-19 print corroborates in source_history with the "
                   "restructure recorded in change_note. BIC701 unowned, accumulates cleanly.")},
    "08_btech_y4_syllabus_2025-26::12::micro-smart-systems": {
        "action": "ALLOW",
        "reason": ("B40 TIER2 same-subject ALLOW (fuzzy 90, overlap 108): draft 'Micro & Smart Systems' (BIC073, 2025-26 "
                   "NEP ICE print) vs the micro-and-smart-systems row 'Micro and Smart Systems' (KEC-077;KEC077;REC088;"
                   "EIC-034;EOE-075;ROE084, sess 2021-22) — '&'/and print-variance class (recorded B29/B33); unit-I "
                   "VERBATIM ('Miniaturization: Introduction, Need of miniaturization, Microsystems versus MEMS, Need of "
                   "micro fabrication, smart materials, structures and systems...'). BIC073 unowned, accumulates. Note: "
                   "doc 06's NIC043 'Micro and Smart Systems' (2016-17) Tier-1-matches this same row (exact name).")},
    "10_btech_y4s7_open-electives_2025-26::03::renewable-energy-resources": {
        "action": "ALLOW",
        "reason": ("B40 TIER2 same-subject ALLOW (fuzzy 96, overlap 64): draft 'RENEWABLE ENERGY RESOURCES' (BOE074, "
                   "2025-26 NEP OE-II print) vs the renewable-energy-sources row 'Renewable Energy Sources' (KAG-057;"
                   "BAG057;NAG-081;KOE074;ROE086;KOE060A, sess 2020-21) — SOURCES/RESOURCES print variance of the same "
                   "OE course (the row ALREADY owns ROE086 — doc 05's 2020-21 print of this exact course); unit-I "
                   "VERBATIM ('Introduction: Various non-conventional energy resources- Introduction, availability, "
                   "classification, relative merits and demerits. Solar Cells: Theory of solar cells.'). BOE074 unowned, "
                   "accumulates cleanly.")},
}

missing = [k for k in keys if k not in EV]
assert not missing, f"no evidence entry for {missing}"
extra = [k for k in EV if k not in keys]
assert not extra, f"entries not in flags: {extra}"

MARK = "    # --- B40 commit-run adjudications (adjudicate_b40 marker) ---\n"
lines = [MARK]
for k in keys:
    reason = EV[k]["reason"].replace('"', '\\"')
    lines.append(f'    "{k}": {{\n        "action": "ALLOW",\n        "reason": ("{reason}")}},\n')

src = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
text = open(src).read()
if "adjudicate_b40 marker" in text:
    print("already injected")
else:
    anchor = "TIER2_OVERRIDES = {"
    i = text.index(anchor) + len(anchor)
    text = text[:i] + "\n" + "".join(lines) + text[i:]
    open(src, "w").write(text)
    print("injected", len(keys), "B40 TIER2_OVERRIDES entries")
