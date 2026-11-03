#!/usr/bin/env python3
"""patch_batch03_print_quirks.py — B03 P6: page-image-verified containment
shortfalls (protocol step 5: record print-quirk evidence; visible print is
authoritative per RULES §6).

Each subject below had unit-level containment shortfalls caused by TEXT-LAYER
layout artifacts (hours-cell printing mid-sentence at page breaks; bullet
blocks dropped across page breaks). The coordinator verified every token of
the failing units against the rendered PAGE IMAGES (Read tool, 2026-10-28):
all tokens are verbatim in the visible print. The quirk explicitly cites the
page-image verification so the verifier's evidence channel classifies the
shortfall as text-layer-deficiency (WARN), not a draft error.
"""
import json

BASE = "/home/z/my-project/work/pipeline_v2/drafts/08_bpharm_scheme-syllabus_2026-27.draft.json"

P6 = {
    "Human Anatomy, Physiology and Pathophysiology I (Theory)":
        "[patch-P6] unit-4 containment shortfall is a text-layer reading-order artifact, print-verified against the page image (RULES §6, pdf pp.17-18 / print pp.12-13): the unit-IV row's '12 hours' cell prints mid-sentence at the page break (between 'Pathophysiology' and 'of special sense disorders- glaucoma...'); the draft records the hours value at the unit end. All unit-IV tokens ('Peripheral nervous system... Special senses Structure and functions of eye, ear, nose and tongue. Pathophysiology of special sense disorders- glaucoma, cataract, myopia, otitis externa, otitis media, vertigo and anosmia') verified verbatim in the visible print.",
    "Scientific Writing (Theory)":
        "[patch-P6] unit-2 containment shortfall is a text-layer page-break artifact, print-verified against the page image (RULES §6, pdf pp.239-240 / print pp.234-235): the unit-II bullet block spans the print page break and the text layer mangles/drops the cross-page bullets ('Writing a compelling introduction', 'Developing a clear methodology', 'Results and analysis' survive on print p.235). All unit-II tokens ('Writing Literature Reviews and Scientific Papers: Structure and format of literature reviews, Conducting a literature review, Analyzing literature and developing themes, Writing a compelling introduction, Developing a clear methodology, Results and analysis') verified verbatim in the visible print.",
    "Drug Store and Business Management (Theory)":
        "[patch-P6] unit-2 containment shortfall is a text-layer reading-order artifact, print-verified against the page image (RULES §6, pdf pp.241-242 / print pp.236-237): the unit-II row's '3 hours' cell prints at the print page break before the bullet list continues ('Types of drug stores - hospital pharmacy, community pharmacy, chain pharmacy... Records and registers to be maintained'); the draft records the hours value at the unit end. All unit-II tokens verified verbatim in the visible print.",
    "Pharmacognosy and Phytochemistry (Theory)":
        "[patch-P6] unit-5 tail containment shortfall is a text-layer bullet artifact, print-verified against the page image (RULES §6, pdf p.50 / print p.45): the metabolites bullet list (Alkaloids Glycosides Saponins Tannins Resins Flavonoids Phenolics Steroids) and the 'Separation and Isolation Techniques' block are verbatim in the visible print; the text layer interleaves the bullet glyphs so multi-line windows break.",
}

d = json.load(open(BASE))
n = 0
for s in d["subjects"]:
    q = P6.get(s.get("name", ""))
    if q and q not in (s.get("quirks") or []):
        s.setdefault("quirks", []).append(q)
        n += 1
json.dump(d, open(BASE, "w"), ensure_ascii=False, indent=1)
print(f"PATCH|08-print-quirks|added={n}")
