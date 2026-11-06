#!/usr/bin/env python3
"""b39_fix_drafts.py — evidence-recorded draft repairs for B39 (post-verify).

Fixes, each anchored to the visible print (RULES §6 / recorded classes):
  doc 01: drop the junk ['EME101EME201'] empty-name row and the prompt-echo
          'verbatim' row; re-extract MANUFACTURING PROCESSES (EME-101/EME-201
          detail p.16) via one mercury call; fill the three empty-name pair
          rows from the printed p.2/p.3 pair cells (EEE151 'Electrical Engg
          Lab', ECS151 'Computer Programming Lab', GP201 'General
          Proficiency') with alternative_pair_row + scheme-citing quirks
          (B28 ALTERNATIVE-PAIR-SLOT class); GP101 name normalized to
          'General Proficiency' with the flattened print kept in name_print.
  doc 03: AUC-001 (image-page transcription) — flag
          unit_ocr_recovered_no_text_layer (v12 remedy class; quirk already
          cites pp.14-22) so unit-containment + ORPHAN downgrade with cited
          evidence.
  doc 07: both code-less non-credit subjects — add no-code evidence flags +
          page-citing quirks (v10 remedy class: no codes are printed anywhere
          in the doc; zero-guess forbids inventing them).
  doc 09: ECS-072 unit-IV filled verbatim from p.33 print ('Circuit
          complexity, lower bounds; Parallel computation and complexity;
          Counting problems; Interactive proofs.') — cross-page junction the
          extraction dropped; ECS-087 unit-II filled verbatim from p.48
          print (IEEE 802.11 line); drop the prompt-echo 'verbatim' junk
          row; EOE041 scheme-note reference recorded in non_subject_rows
          (v10 remedy class: '*Note: ECS- 088 may be opted by only those
          students who didn't opt EOE-041 as an open elective' p.4 — a note
          reference, not a subject row).
"""
import json, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

BASE = "/home/z/my-project/work/pipeline_v2"

def norm(c):
    return (c or "").replace(" ", "").replace("-", "").upper()

# ---------- doc 01 ----------
p1 = f"{BASE}/drafts/01_btech_y1_syllabus_2008-09.draft.json"
d = json.load(open(p1))
d["subjects"] = [s for s in d["subjects"] if norm((s.get("codes") or ["x"])[0]) not in ("EME101EME201",)
                 and (s.get("name") or "") != "verbatim"]
# mercury re-extract MANUFACTURING PROCESSES (p.16 detail; next detail page 17)
rec = json.load(open(f"{BASE}/parsed/01_btech_y1_syllabus_2008-09.json"))
ft = open(f"{BASE}/parsed/01_btech_y1_syllabus_2008-09.fulltext.txt").read()
PAGES = me.pages_of(ft)
sub = {"class": "detail", "code_print": "EME-101/EME-201", "name_print": "MANUFACTURING PROCESSES", "page": 16}
code, obj = me.extract_one("btech_y1_syllabus_2008-09.pdf", "\n\n".join(t for p, t in PAGES if 16 <= p < 17), rec, sub, "2008-09", "BTech")
obj.setdefault("name", obj.get("name_print", ""))
obj.setdefault("codes", ["EME101", "EME201"])
obj.setdefault("quirks", [])
obj.setdefault("flags", [])
if obj.get("units") is None: obj["units"] = {}
print("doc01 MANUFACTURING PROCESSES:", obj.get("name"), "| units:", len(obj.get("units") or {}))
d["subjects"].append(obj)
for s in d["subjects"]:
    cs = [norm(c) for c in (s.get("codes") or [])]
    if "EEE151" in cs and not s.get("name"):
        s["name"] = "Electrical Engg Lab"
        s["name_print"] = "Electrical Engg Lab / Computer Programming Lab"
        s.setdefault("flags", []).append("alternative_pair_row")
        s.setdefault("quirks", []).append(
            "scheme p.2 row 9 prints the PAIRED cell 'EEE-151/ECS-151 | Electrical Engg Lab / Computer Programming Lab' "
            "(two subjects share one printed slot row; each code keeps its half of the printed name; B28 ALTERNATIVE-PAIR-SLOT class)")
    if "ECS151" in cs and not s.get("name"):
        s["name"] = "Computer Programming Lab"
        s["name_print"] = "Electrical Engg Lab / Computer Programming Lab"
        s.setdefault("flags", []).append("alternative_pair_row")
        s.setdefault("quirks", []).append(
            "scheme p.2 row 9 paired cell 'EEE-151/ECS-151 | Electrical Engg Lab / Computer Programming Lab' (see EEE151 row quirk)")
    if "GP201" in cs and not s.get("name"):
        s["name"] = "General Proficiency"
        s["name_print"] = "General Proficiency"
        s.setdefault("flags", []).append("scheme_row_only_detailed_syllabus_not_printed")
        s.setdefault("quirks", []).append("scheme p.3 row prints 'GP-201 | General Proficiency' with '-' marks cells (audit row)")
    if "GP101" in cs and (s.get("name") or "").startswith("General Proficiency -"):
        s["name"] = "General Proficiency"
        s.setdefault("quirks", []).append("scheme p.2 row 12 name cell flattened as 'General Proficiency - - -' (dash marks cells); name_print keeps the flattened print")
json.dump(d, open(p1, "w"), indent=1, ensure_ascii=False)
print("doc01 fixed:", len(d["subjects"]), "subjects")

# ---------- doc 03 ----------
p3 = f"{BASE}/drafts/03_btech_y2_common-subjects-syllabus-rev_2014-15.draft.json"
d = json.load(open(p3))
for s in d["subjects"]:
    if any(norm(c) == "AUC001" for c in (s.get("codes") or [])):
        fl = s.setdefault("flags", [])
        if "unit_ocr_recovered_no_text_layer" not in fl:
            fl.append("unit_ocr_recovered_no_text_layer")
        s.setdefault("quirks", []).append(
            "patch-b39: pp.14-22 are scanned image pages (parsed text layer 5 chars/page); the AUC-001 printed syllabus was "
            "transcribed from the page images (tesseract OCR at 150/400/600 dpi + targeted crop re-passes, subagent "
            "B39-D03-AUC001); RULES §6 visible-print authoritative — text-layer containment is not expected for these units")
json.dump(d, open(p3, "w"), indent=1, ensure_ascii=False)
print("doc03 AUC-001 flagged")

# ---------- doc 07 ----------
p7 = f"{BASE}/drafts/07_btech_y2_non-credit-courses_2018-19.draft.json"
d = json.load(open(p7))
for s in d["subjects"]:
    if not s.get("codes"):
        s.setdefault("flags", []).append("no_code_printed_non_credit")
        s.setdefault("quirks", []).append(
            "patch-b39: NO course code is printed anywhere in this 4-page non-credit doc (checked every page; the doc prints only "
            "the subject name as a section header — 'COMPUTER SYSTEM SECURITY' p.2 / 'PYTHON PROGRAMMING' p.3 — with 'Mapped With' "
            "MOOC URLs; zero-guess forbids inventing codes; v10 B06 no-code class)")
json.dump(d, open(p7, "w"), indent=1, ensure_ascii=False)
print("doc07 no-code evidence recorded")

# ---------- doc 09 ----------
p9 = f"{BASE}/drafts/09_btech_y3-4_syllabus_2010-11.draft.json"
d = json.load(open(p9))
d["subjects"] = [s for s in d["subjects"] if (s.get("name") or "") != "verbatim"]
for s in d["subjects"]:
    cs = [norm(c) for c in (s.get("codes") or [])]
    if "ECS072" in cs and not (s["units"].get("4") or "").strip():
        s["units"]["4"] = ("Circuit complexity, lower bounds; Parallel computation and complexity; Counting problems;\n"
                           "Interactive proofs.")
        s.setdefault("quirks", []).append(
            "patch-b39: Unit-IV content prints at the top of p.33 while the 'UNIT-IV' header sits at the end of p.32 (cross-page "
            "junction the extraction dropped) — filled verbatim from the p.33 text-layer print")
    if "ECS087" in cs and not (s["units"].get("2") or "").strip():
        s["units"]["2"] = ("Wireless Networking, Wireless LAN Overview: MAC issues, IEEE 802.11, Blue Tooth,\n"
                           "Wireless multiple access protocols, TCP over wireless, Wireless applications, data broadcasting,\n"
                           "Mobile IP, WAP: Architecture, protocol stack, application environment, applications.")
        s.setdefault("quirks", []).append(
            "patch-b39: Unit-II prints at the top of p.48 under the p.47 detail section (cross-page junction) — filled verbatim "
            "from the p.48 text-layer print ('IEEE 802.11' present)")
# EOE041 note reference
d.setdefault("non_subject_rows", []).append({
    "kind": "scheme_note_reference",
    "print": "*Note:  ECS- 088 may be opted by only those students who didn't opt EOE-041 as an open elective",
    "locator": "p.4 note under the B.Tech 3rd Year audit scheme"})
json.dump(d, open(p9, "w"), indent=1, ensure_ascii=False)
print("doc09 fixed:", len(d["subjects"]), "subjects")
