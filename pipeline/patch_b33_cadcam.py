#!/usr/bin/env python3
"""patch_b33_cadcam.py — verbatim-item remedy for EME751 CAD/CAM LAB (doc 01).

The draft prefixed every experiment with the printed section label
('A. CAD Experiments — ' / 'B. CAM Experiments — '). The labels ARE printed
(section headers), but the em-dash join is a draft-side decoration that breaks
verbatim containment for short items (§7: extracted strings are verbatim).
Strip the prefixes so each exp is the printed item verbatim; the section
structure stays recorded in the existing quirk (which already documents the
A/B split and the printed 'TEN Experiments' note-vs-lists mismatch).
"""
import json, os

P = "/home/z/my-project/work/pipeline_v2/drafts_b33_run/01_btech_plastic_syllabus_2009-10.draft.json"
d = json.load(open(P, encoding="utf-8"))
for s in d["subjects"]:
    if "CAD/CAM LAB" in s["name"]:
        n = 0
        for e in s.get("experiments") or []:
            for pre in ("A. CAD Experiments — ", "B. CAM Experiments — "):
                if e["exp"].startswith(pre):
                    e["exp"] = e["exp"][len(pre):]
                    n += 1
        # strengthen the quirk: prefixes removed, verbatim items only
        for i, q in enumerate(s.get("quirks") or []):
            if "section prefixes added for disambiguation" in q:
                s["quirks"][i] = (
                    "Printed note: 'Total TEN Experiments are to carried out. FIVE "
                    "Experiments each from CAD and CAM.' but the lists print EIGHT CAD "
                    "experiments (section A, items 1-8) and NINE CAM experiments "
                    "(section B, items 1-9); stored verbatim in printed order under "
                    "their printed section headers 'A. CAD Experiments' and "
                    "'B. CAM Experiments' (p.29-30).")
        print("stripped prefixes on", n, "experiments of", s["name"])
json.dump(d, open(P, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("PATCH OK")
