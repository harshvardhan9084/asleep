#!/usr/bin/env python3
"""patch_b38_verify.py — evidence-anchored remedies for the B38 verify failures.

Doc 02: RTT351 lab detail not printed anywhere in the doc (only scheme row
p.4) -> scheme_only_print flag + quirk. RTT353 prints ONE prose block (p.7,
microscopy lab) -> verbatim into notes_print + practical-turns flag class.

Doc 03: drop 4 junk rows (2 no-code scheme stubs duplicating extracted detail
rows, 1 instruction-string row, 1 empty-name KNC502); add KNC501/KNC502
scheme rows with printed names; KTT652/653 headers print on p.22 with NO
content (document ends) -> scheme_only_print + quirk; KTT651 truncated
fragment transcribed; KTT552/553 p.13 lab prose -> verbatim experiments.

Doc 04: drop the instruction-string junk row (kills the fabricated BPE071/074
ORPHANs — the recorded code-run-collapse class); add BTT503 scheme-only row
(scheme p.2 row 3, marks printed).

Doc 07: BTT071 empty-name row -> re-extract (p.8-9); BTT751 name fix +
p.12 numbered experiment list; BTT752 = 'Mini Project or Internship
Assessment*' per scheme row p.2 + scheme_only_print.

Doc 10: KAS154PH row name -> 'ENGLISH LAB' (p.29 header); Course Objectives
prose -> objectives_print + objectives_only flag.
"""
import json, os, re, sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

D = "/home/z/my-project/work/pipeline_v2/drafts_b38_run"
P = "/home/z/my-project/work/pipeline_v2/parsed"


def load(stem):
    return json.load(open(f"{D}/{stem}.draft.json", encoding="utf-8"))


def save(stem, d):
    json.dump(d, open(f"{D}/{stem}.draft.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def row_by_code(d, code):
    for s in d["subjects"]:
        if code.replace(" ", "") in [c.replace(" ", "") for c in (s.get("codes") or [])]:
            return s
    return None


# ---------- doc 02 ----------
stem = "02_btech_textile-tech_y2_scheme-syllabus_2017-18"
d = load(stem)
r = row_by_code(d, "RTT351")
r["flags"] = (r.get("flags") or []) + ["scheme_only_print"]
r.setdefault("quirks", []).append(
    "ADJUDICATED (B38 verify): the lab detail for RTT351 is NOT printed anywhere in "
    "this 12-page document (pages 4-7 carry detail for RTT301/302/305-405 and labs "
    "RTT352/RTT353 only); RTT351 appears only in the semester scheme table (p.4, "
    "0-0-2, 50/30/20/100) — recorded B23/B25/B27 zero-GAP class.")
r2 = row_by_code(d, "RTT353")
r2["notes_print"] = ("Principle of microscopy, microscopic identification of natural "
                     "fibres, preparation and mounting of specimen for longitudinal view, "
                     "standard scheme of analysis of homogeneous fibre and blend by "
                     "physical and chemical methods, preparation of reagents used for "
                     "chemical analysis.")
r2["flags"] = (r2.get("flags") or []) + ["practical_turns_notes_only_no_units_printed"]
r2.setdefault("quirks", []).append(
    "Lab content printed as ONE prose block (p.7), no numbered experiment list and no "
    "unit structure — transcribed verbatim to notes_print; flagged "
    "practical_turns_notes_only_no_units_printed (B29 RME653 class).")
save(stem, d)
print("doc02 patched")

# ---------- doc 03 ----------
stem = "03_btech_textile-tech_y3_model-curriculum_2020-21"
d = load(stem)
d["subjects"] = [s for s in d["subjects"] if not (
    (not s.get("codes") and s["name"] in ("Chemical Processing of Textiles", "Yarn Manufacture-III Lab"))
    or "codes exactly as printed" in str(s.get("codes"))
    or (s.get("codes") == ["KNC502"] and not s["name"]))]
# KNC501/KNC502 scheme rows (printed paired-cell name, p.2/p.3)
for c, pg in (("KNC501", 2), ("KNC502", 2)):
    if not row_by_code(d, c):
        d["subjects"].append({
            "name": "Constitution of India, Law and Engineering / Essence of Indian Knowledge Tradition",
            "name_print": "Constitution of India, Law and Engineering / Essence of Indian Knowledge Tradition",
            "codes": [c], "semester": 5 if c.endswith("1") else 6,
            "units": {}, "quirks": ["scheme table paired-cell print (p.%d): audit course, "
                                    "detailed syllabus not printed in this document" % pg],
            "flags": ["scheme_row_only_detailed_syllabus_not_printed"], "experiments": []})
r = row_by_code(d, "KTT652")
if r:
    r["flags"] = (r.get("flags") or []) + ["scheme_only_print"]
    r.setdefault("quirks", []).append(
        "p.22 prints ONLY the header '7. Advance Spinning Technology (L T P 0 0 2)' "
        "under '6th Semester Lab Syllabus' — the document ends before any lab content; "
        "no content invented (zero-guess).")
r = row_by_code(d, "KTT653")
if r:
    r["flags"] = (r.get("flags") or []) + ["scheme_only_print"]
    r.setdefault("quirks", []).append(
        "p.22 prints ONLY the header '8. Advance Weaving Technology (L T P 0 0 2)' — "
        "document ends; no lab content printed.")
r = row_by_code(d, "KTT651")
if r and not r.get("experiments"):
    r["experiments"] = [{"no": 1, "exp": "Use of"}]
    r["flags"] = (r.get("flags") or []) + ["lab_header_truncated_document_end"]
    r.setdefault("quirks", []).append(
        "p.22 prints the lab header '6. Textile Testing-II (L T P 0 0 2)' and a single "
        "truncated fragment 'Use o...' before the document ends — the fragment is "
        "transcribed verbatim; no content invented.")
r = row_by_code(d, "KTT552")
if r and not r.get("experiments"):
    r["experiments"] = [
        {"no": 1, "exp": "Names of parts & their functions of ring frame and doubling frame (p.13 print continues; content transcribed from the printed lab section '7. Yarn Manufacturing-III (L T P 0 0 2)')"}]
    r["flags"] = (r.get("flags") or []) + ["practical_sections_only_no_units_printed"]
r = row_by_code(d, "KTT553")
if r and not r.get("experiments"):
    r["flags"] = (r.get("flags") or []) + ["scheme_only_print"]
# KTT053 re-extract via mercury-3 (p.9 detail '(c) Structure & properties of Fibres')
ft = open(f"{P}/{stem}.fulltext.txt").read()
rec = json.load(open(f"{P}/{stem}.json"))
pages = me.pages_of(ft)
sub = {"code_print": "KTT053", "name_print": "Structure & Properties of Fibres", "page": 9, "class": "detail"}
slice_txt = "\n\n".join(t for pp, t in pages if pp >= 9)
code, obj = me.extract_one(rec.get("file", stem + ".pdf"), slice_txt, rec, sub, "2020-21", "BTech")
old = row_by_code(d, "KTT053")
if old is not None:
    d["subjects"].remove(old)
obj.setdefault("name", obj.get("name_print", ""))
obj["codes"] = ["KTT053"]
obj.setdefault("quirks", []).append(
    "detail header prints '(c) Structure & properties of Fibres (L T P 3 0 0)' (p.9); "
    "the scheme table paired-cell prints 'KTT051/KTT052/KTT053 Fabric Structure & "
    "Analysis/ Textile Design...' (p.2) — the detail header is authoritative for the name.")
d["subjects"].append(obj)
d["flags"] = [f for f in d.get("flags", []) if not str(f).startswith("extraction_failed:KTT051")]
save(stem, d)
print("doc03 patched; subjects:", len(d["subjects"]))

# ---------- doc 04 ----------
stem = "04_btech_textile-tech_y3_syllabus_2024-25"
d = load(stem)
d["subjects"] = [s for s in d["subjects"] if "codes exactly as printed" not in str(s.get("codes"))]
if not row_by_code(d, "BTT503"):
    d["subjects"].append({
        "name": "Chemical Processing of Textiles", "name_print": "Chemical Processing of Textiles",
        "codes": ["BTT503"], "semester": 5, "ltp": {"l": 3, "t": 1, "p": 0}, "credit": 4,
        "marks": {"sessional_ct": 20, "sessional_ta": 10, "sessional_total": 30, "ese_te_pe": 70, "total": 100},
        "units": {}, "experiments": [],
        "quirks": ["scheme table row 3 (p.2, 'T PCS' = Theory PCS column print): marks "
                   "CT 20 / TA 10 / Total 30 / TE 70 / Total 100 printed; detailed "
                   "syllabus for BTT503 not printed in this document (it is the K-era "
                   "KTT503 course — the registry's KTT503 row carries the detailed print)"],
        "flags": ["scheme_row_only_detailed_syllabus_not_printed"]})
save(stem, d)
print("doc04 patched; subjects:", len(d["subjects"]))

# ---------- doc 07 ----------
stem = "07_btech_textile-tech_y4_syllabus_2025-26"
d = load(stem)
r = row_by_code(d, "BTT071")
ft = open(f"{P}/{stem}.fulltext.txt").read()
rec = json.load(open(f"{P}/{stem}.json"))
pages = me.pages_of(ft)
sub = {"code_print": "BTT071", "name_print": "Sustainability in Textile Industry", "page": 8, "class": "detail"}
slice_txt = "\n\n".join(t for pp, t in pages if pp >= 8 and pp <= 10)
code, obj = me.extract_one(rec.get("file", stem + ".pdf"), slice_txt, rec, sub, "2025-26", "BTech")
if r is not None:
    d["subjects"].remove(r)
obj.setdefault("name", obj.get("name_print", ""))
obj["codes"] = ["BTT071"]
d["subjects"].append(obj)
r = row_by_code(d, "BTT751")
if r:
    r["name"] = "Garment Manufacturing Technology Lab"
    r["name_print"] = "Garment Manufacturing Technology Lab"
    if not r.get("experiments"):
        r["experiments"] = [
            {"no": 1, "exp": "Learn how to take Body measurements related to Men's and Women's Wear."},
            {"no": 2, "exp": "Learn how to make patterns for Men's Shirt."},
            {"no": 3, "exp": "Learn how to make manual marker plan and optimize marker efficiency by trial-and-error method."},
            {"no": 4, "exp": "Develop understanding of operating an industrial lockstitch sewing machine (p.12 print continues)."}]
    r.setdefault("quirks", []).append(
        "p.12 prints 'Suggested List of Experiments:' with a numbered list; the list "
        "continues beyond the extracted page slice — items 1-4 transcribed verbatim.")
r = row_by_code(d, "BTT752")
if r:
    r["name"] = "Mini Project or Internship Assessment*"
    r["name_print"] = "Mini Project or Internship Assessment*"
    r["flags"] = (r.get("flags") or []) + ["scheme_only_print"]
    r.setdefault("quirks", []).append(
        "scheme table row 6 (p.2): 'BTT752 Mini Project or Internship Assessment* "
        "0-0-4 100 100 2' — detailed syllabus not printed in this document.")
save(stem, d)
print("doc07 patched; subjects:", len(d["subjects"]))

# ---------- doc 10 ----------
stem = "10_btech_y1_syllabus-hindi_2021-22"
d = load(stem)
r = row_by_code(d, "KAS154PH")
if r:
    r["name"] = "ENGLISH LAB"
    r["name_print"] = "ENGLISH  LAB"
    if not r.get("objectives_print"):
        r["objectives_print"] = [
            "1. To facilitate software based learning to provide the required English Language proficiency to students.",
            "2. To acquaint students with specific dimensions of communication skills i.e. Reading, Writing, Listening (p.29 print continues)."]
    r["flags"] = (r.get("flags") or []) + ["objectives_only_no_units_printed"]
    r.setdefault("quirks", []).append(
        "p.29 prints header 'KAS154PH/KAS254PH ENGLISH LAB 0L:1T:2P 1 Credit' followed "
        "by 'Course Objectives:' prose (no units, no experiment list) — objectives "
        "transcribed verbatim; flagged objectives_only_no_units_printed (verifier "
        "obj_only class).")
save(stem, d)
print("doc10 patched")
print("PATCH OK")
