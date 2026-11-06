#!/usr/bin/env python3
"""b40_ocr_evidence_fix.py — G6 remedy for human-values-professional-ethics
(recorded B12/B39 class, evidence verified before writing):

The row's unit1 was transcribed by B39 via OCR from the SCANNED-IMAGE pages
pp.14-22 of btech_y2_common-subjects-syllabus-rev_2014-15.pdf#d32696e27932336c
(re-verified NOW: PyMuPDF extracts only 4-char page-number stamps on pp.14-22
— the AUC-001 units are printed as raster; the text-layer containment is
structurally impossible for every resolvable copy). B39's manifest recorded
the transcription ('doc 03's pp.14-22 are SCANNED IMAGE pages (AUC-001...)
transcribed by a subagent via OCR ... and spliced into the draft (unit_ocr_
recovered_no_text_layer class, v12 remedy)') and B39's G6 ran with the
OCR_SKIP for it; the ROW's notes column, however, did not carry the evidence
marker, so this batch's touch re-probed G6 without the class context.

This batch does NOT change the row's unit1 (byte-identical to the published
CSV — verified). Fix: record the evidence marker + page-citing provenance on
the row's notes (the gate's row_ev source), preserving all existing notes.
"""
import csv

P = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
SID = "human-values-professional-ethics"
MARK = ("unit_ocr_recovered_no_text_layer: unit text transcribed by OCR from the scanned-image "
        "pages pp.14-22 of btech_y2_common-subjects-syllabus-rev_2014-15.pdf#d32696e27932336c "
        "(PyMuPDF text layer extracts only 4-char page-number stamps there — raster print, "
        "verified 2026-11-06; B39 manifest records the same transcription; RULES §6 "
        "visible-print-authoritative; G6 OCR_SKIP class B12/B39)")

rows = list(csv.DictReader(open(P)))
fields = list(rows[0].keys())
hit = False
for r in rows:
    if r["subject_id"] == SID:
        if "unit_ocr_recovered_no_text_layer" in (r.get("notes") or ""):
            print("evidence already present")
            hit = True
            break
        r["notes"] = ((r.get("notes") or "") + " | " + MARK).strip(" |")
        hit = True
        print("notes updated:", r["notes"][:120], "...")
        break
assert hit, SID
with open(P, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
print("CSV rewritten;", len(rows), "rows")
