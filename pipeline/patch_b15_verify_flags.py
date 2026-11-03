#!/usr/bin/env python3
"""patch_b15_verify_flags.py — add recorded evidence flags to B15 draft subjects
so verify_draft.py's existing remedy classes (B02 scheme-only / B08 co_only /
B10 unit_ocr_recovered_no_text_layer) can downgrade the printed-design classes.

Evidence (all on disk):
- 03 raster doc: parsed text-layer lens [0,0,1286,0,0,0,0,0,0,0,0,0,1834] —
  pages 1,2,4-12 EMPTY; content transcribed from 300-450dpi renders + tesseract
  OCR + z-ai VLM cross-checks (RULES §6: visible print authoritative). The B10
  v12 remedy class (unit_ocr_recovered_no_text_layer + page-citing quirk)
  applies to every subject of this doc.
- 02 RCE753/RCE754/RCE851/RCE852: scheme-only assessment slots (quirks cite the
  scheme pages p.2/p.15, 'no unit text/experiments printed') — B02 class.
- 07 BCH653 + 08 BCH752/753/754/851: CO table printed, no unit theory anywhere
  (v11 B08 class: co_only_no_units_printed + printed cos).
- 09 NCH654 SEMINAR: printed description is the complete syllabus content
  (no_detailed_syllabus_printed class).

Idempotent: flags/quirks only added when absent.
"""
import json, os

D = "/home/z/my-project/work/pipeline_v2/drafts"

OCR_QUIRK = ("patch-b15 OCR evidence: units/COs transcribed from page images "
             "(raster doc; parsed text layer EMPTY on pages 1,2,4-12; 300-450dpi "
             "renders + tesseract OCR + VLM cross-check per RULES §6 — visible "
             "print authoritative)")


def load(stem):
    return json.load(open(os.path.join(D, stem + ".draft.json")))


def save(stem, d):
    with open(os.path.join(D, stem + ".draft.json"), "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)


def add_flag(s, flag):
    if flag not in (s.get("flags") or []):
        s.setdefault("flags", []).append(flag)


def add_quirk(s, q):
    if q not in (s.get("quirks") or []):
        s.setdefault("quirks", []).append(q)


def patch(stem, matcher, flags, quirk=None):
    d = load(stem)
    n = 0
    for s in d["subjects"]:
        if matcher(s):
            for fl in flags:
                add_flag(s, fl)
            if quirk:
                add_quirk(s, quirk)
            n += 1
    save(stem, d)
    print(f"PATCHED|{stem}|{n}|{flags}")


# 02: four scheme-only assessment slots (RCE753/754/851/852)
patch("02_btech_ce_y4_syllabus-cbcs_2019-20",
      lambda s: s.get("codes") and any(c in ("RCE753", "RCE754", "RCE851", "RCE852") for c in s["codes"]),
      ["scheme-only"])

# 03: every subject is OCR-recovered (raster); project slots also carry the
# no-detailed-syllabus class (objective+guidelines only, no units/COs/exps)
d3 = load("03_btech_ce_y4_syllabus-rev_2025-26")
for s in d3["subjects"]:
    add_flag(s, "unit_ocr_recovered_no_text_layer")
    add_quirk(s, OCR_QUIRK)
    codes = s.get("codes") or []
    if any(c in ("BCE753", "BCE754", "BCE851") for c in codes):
        add_flag(s, "no_detailed_syllabus_printed")
save("03_btech_ce_y4_syllabus-rev_2025-26", d3)
print("PATCHED|03_btech_ce_y4_syllabus-rev_2025-26|all|unit_ocr_recovered_no_text_layer")

# 07: BCH653 Technical Presentation — CO table printed, no unit theory
patch("07_btech_che_s5-6_syllabus_2024-25",
      lambda s: "BCH653" in (s.get("codes") or []),
      ["co_only_no_units_printed"])

# 08: BCH752/753/754/851 — CO table printed, no unit theory
patch("08_btech_che_s7-8_syllabus_2025-26",
      lambda s: any(c in ("BCH752", "BCH753", "BCH754", "BCH851") for c in (s.get("codes") or [])),
      ["co_only_no_units_printed"])

# 09: NCH654 SEMINAR — printed description is the complete content
patch("09_btech_che_syllabus_2015-16",
      lambda s: "NCH654" in (s.get("codes") or []),
      ["no_detailed_syllabus_printed"])

print("DONE")
