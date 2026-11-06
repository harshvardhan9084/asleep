#!/usr/bin/env python3
"""patch_b33_verify.py — evidence-anchored remedies for the B33 verify failures.

Doc 03 (btech_plastic_syllabus_2020-21, KPE-era, fulltext-verified):
1. Polymer Composites (KPE 071) CO2: draft had inserted 'the' — print reads
   'Understand of theories of composite formation and mechanism of load
   transfer' (p.46, clean text layer, no garbling; zero-guess: verbatim print
   restored, quirk records the correction).
2. Plastic Product & Mould Design Lab (KPE 553): the lab's printed content is
   THREE sections (I. Mould Design using CAD / II. CAM Programming /
   III: Mould flow Analysis — p.13, colon after III as printed), NOT a unit
   theory block. The sections were recorded only as a quirk note at draft
   time and experiments stayed null. Remedy per the recorded lab-content
   classes (B29 RME653 notes-class precedent): transcribe the printed section
   items verbatim into experiments (labels preserved inside the text) and add
   the evidence flag `practical_sections_only_no_units_printed`; verifier
   downgrades no-units via the non-empty experiments class.

Doc 07 (btech_plastic_y4_syllabus-cbcs_2019-20, RPL codes):
3. RPL753 Industrial Training / RPL754 Project-1 / RPL851 Seminar /
   RPL852 Project-2: each code appears EXACTLY ONCE in the whole 26-page
   document — only in the VII/VIII-semester scheme tables (spot-verified in
   the parsed fulltext: no detail pages, 1 UNIT mention document-wide). The
   draft quirks already carry the SCHEME-ROW-ONLY evidence with locator and
   marks reading; the formal flag token was missing. Add `scheme_only_print`
   to the four subjects (same class as patch_b03_drafts.py).
"""
import json, os

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts_b33_run"


def load(fn):
    with open(os.path.join(DRAFTS, fn), encoding="utf-8") as f:
        return json.load(f)


def save(fn, d):
    with open(os.path.join(DRAFTS, fn), "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)


def find(d, code):
    for s in d["subjects"]:
        codes = [c.replace(" ", "") for c in (s.get("codes") or [])]
        if code.replace(" ", "") in codes:
            return s
    raise KeyError(code)


# --- doc 03 ---
d3 = load("03_btech_plastic_syllabus_2020-21.draft.json")

pc = find(d3, "KPE071")
old = pc["cos"][1]["text"]
fixed = "Understand of theories of composite formation and mechanism of load transfer"
assert old == "Understand of the theories of composite formation and mechanism of load transfer", old
pc["cos"][1]["text"] = fixed
pc.setdefault("quirks", []).append(
    "CO-2 transcription carried an inserted 'the' ('Understand of the theories'); "
    "print p.46 reads 'Understand of theories of composite formation and mechanism "
    "of load transfer' — restored verbatim to print (clean text layer, no garbling).")
print("doc03 KPE071 CO2 fixed")

lab = find(d3, "KPE553")
assert not lab.get("experiments"), "experiments unexpectedly present"
lab["experiments"] = [
    {"no": 1, "exp": "I. Mould Design using CAD — a) Injection Mould design: Design "
     "calculations for No. of cavities, Selection of injection moulding machine, shot "
     "capacity, plasticizing rate, Clamping force and 2 D / 3 D Modeling for Two plate, "
     "Three Plate and split Moulds"},
    {"no": 2, "exp": "I. Mould Design using CAD — b) Compression Mould Design: Design "
     "calculations for No. of cavities, Flash thickness allowances, Design of loading "
     "chamber, Bulk factor, Pressure pad, Heaters and 2 D / 3 D Modeling for Compression "
     "Mould."},
    {"no": 3, "exp": "I. Mould Design using CAD — c) Transfer Mould Design: Design "
     "calculations for Pot, Bulk factor, Heaters and 2 D / 3 D Modeling for Pot and "
     "Plunger transfer Moulds."},
    {"no": 4, "exp": "I. Mould Design using CAD — d) Blow Mould Design: Design "
     "calculations for Clamping force, pinch-off, Head die design, Parison dimensions "
     "and 2 D /3 D Modeling for Blow Mould."},
    {"no": 5, "exp": "II. CAM Programming — Programming and Machining of mould elements "
     "(Core, Cavity, Gide Pillar and Guide Bush) using CNC Turning Center and CNC "
     "Machining Center."},
    {"no": 6, "exp": "III: Mould flow Analysis — a) Design Optimization of Plastic Part, "
     "Mould and Process parameters optimization using Moldflow Software"},
    {"no": 7, "exp": "III: Mould flow Analysis — b) Modeling, Mesh Creation, Mesh "
     "Checking, Surface repair, Creating Feed system and cooling system."},
    {"no": 8, "exp": "III: Mould flow Analysis — c) Analysis: Gate location, Moulding "
     "window Fill, Flow, Cool, Pack, Warp, Shrinkage, Stress"},
]
lab["flags"] = (lab.get("flags") or []) + ["practical_sections_only_no_units_printed"]
lab.setdefault("quirks", []).append(
    "Lab content printed as three lettered sections (I./II./'III:' with colon, p.13), "
    "not units and not a numbered experiment list; sections transcribed verbatim into "
    "experiments with their printed labels; flagged "
    "practical_sections_only_no_units_printed (evidence: p.13 fulltext).")
print("doc03 KPE553 experiments extracted:", len(lab["experiments"]))
save("03_btech_plastic_syllabus_2020-21.draft.json", d3)

# --- doc 07 ---
d7 = load("07_btech_plastic_y4_syllabus-cbcs_2019-20.draft.json")
for code in ["RPL753", "RPL754", "RPL851", "RPL852"]:
    s = find(d7, code)
    fl = s.get("flags") or []
    if "scheme_only_print" not in fl:
        fl.append("scheme_only_print")
    s["flags"] = fl
    print(f"doc07 {code} scheme_only_print added")
save("07_btech_plastic_y4_syllabus-cbcs_2019-20.draft.json", d7)
print("PATCH OK")
