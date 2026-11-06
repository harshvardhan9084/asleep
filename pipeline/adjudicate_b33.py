#!/usr/bin/env python3
"""adjudicate_b33.py — B33 merge adjudications (two parts, both idempotent).

PART 1 — draft-side code adjudication (doc 01, EPL-065 conflict, page-evidenced):
  Doc 01 (2009-10) prints:
    - Elective lists (p.7 + p.61, two independent lists):
        'EPL-063 / EMT601: Pneumatics & Hydraulics'  AND  'EPL-065 / EME-065: Energy Management'
    - Detail p.63: 'EMT-601 / EPL 065: Pneumatics &Hydraulics'  (outlier print)
    - Detail p.65: 'EME-065 / EPL 065 : ENERGY MANAGEMENT'      (consistent with lists)
  EPL-065 is claimed by TWO different subjects in the same document; G2 (one
  owner per code within BTech) forces a single owner. Weight of print: Energy
  Management carries EPL-065 on THREE independent print locations (list x2 +
  its own detail page); Pneumatics' list code is EPL-063 on the same two
  lists. Ruling (recorded RETARGET_KEEP_PUBLISHED_CODE_OWNER / print-misprint
  class): EPL-065 belongs to Energy Management; Pneumatics keeps EMT-601 +
  list print EPL-063; the p.63 'EPL 065' detail print is recorded verbatim as
  a print misprint in the row's quirks (zero-guess: no third code invented).

PART 2 — TIER2_OVERRIDES injection (5 entries, marker-guarded):
  2x FORCE_APPEND wrong-subject Tier-2 hits (recorded B30 EMT-011 class),
  1x RETARGET same-course per-unit-verbatim-identity (recorded B37 dual-print
  class), 2x ALLOW name-variant same-subject (recorded TIER2 ALLOW class).
"""
import json, os, re

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts_b33_run"
D1 = os.path.join(DRAFTS, "01_btech_plastic_syllabus_2009-10.draft.json")
D2 = os.path.join(DRAFTS, "02_btech_plastic_syllabus_2018-19.draft.json")
MERGE = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"

# ---------- PART 1 ----------
d1 = json.load(open(D1, encoding="utf-8"))
for s in d1["subjects"]:
    if s["name"] == "PNEUMATICS & HYDRAULICS":
        codes = [c.replace(" ", "") for c in s["codes"]]
        if "EPL065" in codes and "EPL063" not in codes:
            s["codes"] = ["EMT601", "EPL063"]
            s.setdefault("quirks", []).append(
                "ADJUDICATED (B33): detail page p.63 prints 'EMT-601 / EPL 065' but the "
                "document's own elective lists (p.7 + p.61) print 'EPL-063 / EMT601: "
                "Pneumatics & Hydraulics'; EPL-065 is carried by ENERGY MANAGEMENT on "
                "three consistent prints (p.7 list, p.61 list, p.65 detail) — G2 "
                "single-ownership within BTech: EPL-065 belongs to Energy Management, "
                "this row keeps the list print EPL-063 and the p.63 'EPL 065' print is "
                "recorded here verbatim as a print misprint (no code invented).")
            s["flags"] = [
                "elective_code_conflict_EPL065_RESOLVED (adjudicated B33: EPL-065 -> "
                "energy-management (3 consistent prints); this row keeps EMT-601 + "
                "EPL-063 list print; p.63 detail 'EPL 065' = recorded misprint)"]
            print("doc01 PNEUMATICS & HYDRAULICS codes ->", s["codes"])
    if s["name"] == "ENERGY MANAGEMENT":
        s["flags"] = [
            "elective_code_conflict_EPL065_RESOLVED (adjudicated B33: EPL-065 owned by "
            "this row — p.7 list 'EPL-065 / EME-065', p.61 list 'EME-065 / EPL 065', "
            "p.65 detail 'EME-065 / EPL 065 : ENERGY MANAGEMENT' all agree; the "
            "competing p.63 Pneumatics detail print is the outlier/misprint)"]
        print("doc01 ENERGY MANAGEMENT flag resolved")
    if s["name"] == "MOULD & DIE MANUFACTURING LAB":
        s["flags"] = [
            "code_conflict_EME755_vs_EPL752_RESOLVED (adjudicated B33: same-document "
            "dual print — scheme p.6 prints 'EPL-752 Mould & Die Manufacturing Lab', "
            "detail p.30 prints 'EME-755: MOULD & DIE MANUFACTURING LAB'; both codes "
            "kept on this one row (dual-print atoms class), primary = detail-page "
            "print EME-755)"]
        print("doc01 MOULD & DIE MANUFACTURING LAB flag resolved (dual print kept)")
json.dump(d1, open(D1, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

d2 = json.load(open(D2, encoding="utf-8"))
d2["flags"] = [
    ("elective_code_conflict_DE_I_RESOLVED (adjudicated B33: the document's detail "
     "pages are authoritative per §6 — RPL051 Heat & Mass Transfer (also printed "
     "RME502 in scheme/lists), RPL052 Chemical Thermodynamics (detail p.20 "
     "'RPL 052: CHEMICAL THERMODYNAMICS'), RPL053 Polymer Degradation and "
     "Stabilisation (detail p.22), RPL054 Plastic Packaging and foam (detail p.24 "
     "'RPL054:'). The p.2 scheme list (RPL051-053 shifted mapping) and the p.12 "
     "list ('RPL 014' for Plastic Packaging) are two DIFFERENT misprints of the "
     "same elective block, both outranked by the detail-page prints; recorded "
     "verbatim in subject quirks."),
    ("elective_name_conflict_RPL063_RESOLVED (adjudicated B33: detail page prints "
     "'RPL063: ADDITIVES & COMPOUNDING' with full unit content; the p.12 list line "
     "'RPL 063. Plastic Extrusion Technology.' has NO detail page anywhere in this "
     "18-page document and 'Plastic Extrusion Technology' belongs to RPL-024/EPL-024 "
     "in the 2009-10 doc (own row) — the p.12 line is a list misprint; the detail "
     "print stands.)")]
json.dump(d2, open(D2, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("doc02 DOC flags resolved (2)")

# ---------- PART 2 ----------
src = open(MERGE).read()
if "adjudicate_b33 marker" in src:
    print("overrides already injected")
else:
    BLOCK = '''
    # --- B33 adjudications (adjudicate_b33 marker) ---
    "01_btech_plastic_syllabus_2009-10::03::manufacturing-technology": {
        "action": "FORCE_APPEND",
        "reason": "B33 wrong-subject FORCE_APPEND (recorded B30 EMT-011/EMT-801 class + RULES §11 never-merge-different-subjects): draft 'MANUFACTURING TECHNOLOGY' (EME-405, 2009-10 Plastic-Engineering DE print, 5 verbatim units) — the Tier-2 hit garment-manufacturing-technology (KHT-051 Fashion/Tech row, fuzzy 86, overlap 13) is a DIFFERENT subject (garment/fabric domain vs this manufacturing course: sheet-metal working, jigs & fixtures, metal cutting); it shares only a two-sentence generic intro with Manufacturing Science-I (EME402) whose unit bodies differ materially (unit1 428 vs 299 chars, different topics + hour structures). No 'Manufacturing Technology' theory row exists in BTech (only Manufacturing Science-I/II and the RME452/RME553 LAB rows). Appends as its own row owning the unclaimed EME405, with cross-reference notes to manufacturing-science-i and garment-manufacturing-technology."},
    "01_btech_plastic_syllabus_2009-10::34::instrumentation": {
        "action": "FORCE_APPEND",
        "reason": "B33 wrong-subject FORCE_APPEND (same recorded class): draft 'INSTRUMENTATION' (EPL-021, 2009-10 Plastic-Engineering DE print, 4 verbatim units: measurement fundamentals, standards/accuracy, IP quantities, telemetry) — the Tier-2 hit bio-instrumentation (EBM-501 Biomedical row, fuzzy 88, overlap 7) is a DIFFERENT subject (biomedical signals/patient safety). No unit identity with industrial-instrumentation (NIC-602), process-instrumentation (NCH604) or instrumentation-and-process-control (ECH507) either. Appends as its own row owning the unclaimed EPL021, with cross-reference notes."},
    "01_btech_plastic_syllabus_2009-10::29::chemical-thermodynamics": {
        "action": "RETARGET", "target": "chemical-engineering-thermodynamics",
        "reason": "B33 same-course RETARGET (per-unit verbatim identity class, identical evidence to 02::10): draft 'CHEMICAL THERMODYNAMICS' (EPL-012/ECH-401, 2009-10 Plastic DE-I print) — all five units are character-identical (±1 whitespace artifact) to the chemical-engineering-thermodynamics accumulator row's establishing ECH-401 print; the plastic DE list prints the CHE core course under the shortened name with the DE-list code EPL-012. The auto code-slot-collision APPEND (collapsed-name 0.80 < 0.84) would SPLIT one subject into two rows (RULES §11); the name-similarity miss is a prefix-artifact ('Engineering' inserted mid-name). RETARGET pins the update on the ECH401 accumulator: EPL-012 joins code_history, ECH-401 ownership unchanged (already the row's own), the DE print variant recorded via name_print."},
    "02_btech_plastic_syllabus_2018-19::10::chemical-thermodynamics": {
        "action": "RETARGET", "target": "chemical-engineering-thermodynamics",
        "reason": "B33 same-course RETARGET (per-unit verbatim identity class, B37 computer-programming-lab dual-print analog): draft 'CHEMICAL THERMODYNAMICS' (RPL052, 2018-19 Plastic DE-I print) — all five units are character-identical (±1 whitespace artifact) to the chemical-engineering-thermodynamics accumulator row's establishing ECH-401 print (2009-10); the R-era DE list re-codes the SAME university course as RPL-052. The Tier-2 auto hit chemical-process-thermodynamics (KCH 505, 2020-21, different unit bodies) is a different course. RETARGET pins the update on the ECH401 accumulator: RPL052 joins code_history, the canonical name stays, the 'Chemical Thermodynamics' print variant is recorded via name_print."},
    "06_btech_plastic_y3_syllabus_2024-25::11::heat-mass-transfer": {
        "action": "ALLOW",
        "reason": "B33 same-subject name-variant ALLOW (recorded TIER2 ALLOW class): 'Heat & Mass Transfer' (BPE056, 2024-25 Plastic print; the doc itself states '(Same as KME 501)' — recorded in the draft quirks) -> heat-and-mass-transfer row (fuzzy 90, overlap 180); ampersand print variance of the same BTech shared course; the doc's cross-branch same-course note is recorded on the row."},
    "08_btech_plastic_y4_syllabus_2016-17::02::industrial-safety-hazard-management": {
        "action": "ALLOW",
        "reason": "B33 same-subject name-variant ALLOW (recorded TIER2 ALLOW class): 'Industrial Safety & Hazard Management' (NPL-801, 2016-17 Plastic y4 print) -> industrial-safety-and-hazard-management row (fuzzy 95, overlap 85); '&'/'and' print variance, same subject; the ECH-043 2009-10 print (doc 01::27) stays with its published owner per the recorded CODE-REASSIGNED class."},
'''
    anchor = "TIER2_OVERRIDES = {"
    i = src.find(anchor)
    assert i > 0, "TIER2_OVERRIDES dict not found"
    j = i + len(anchor)
    src = src[:j] + BLOCK + src[j:]
    open(MERGE, "w").write(src)
    print("injected 5 B33 TIER2_OVERRIDES entries")
print("ADJUDICATE OK")
