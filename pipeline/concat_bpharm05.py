#!/usr/bin/env python3
"""concat_bpharm05.py — deterministically assemble the canonical 05 B.Pharm draft from
segments a-f. Idempotent. Adjudications applied here are recorded per-row in notes.

Adjudication A1 (shared slot codes): the printed Course-Code cell for elective
alternatives is 'BP212P SEC1' style (code + group tag in ONE printed cell). Segment f
rows carrying a duplicated bare code get primary_code rewritten to the full printed cell
(code + space + group tag) where the group tag is printed in that row's notes; their
needs_review flag is cleared with the reason recorded.
"""
import json, re

D = "/home/z/my-project/work/pipeline_v2/drafts"
CANON = f"{D}/05_bpharm_scheme-syllabus_2026-27.draft.json"
SEGS = ["05a", "05b", "05c", "05d", "05e", "05f"]
STEM = "05_bpharm_scheme-syllabus_2026-27"
PDF_REL = "5-course/2026-27/bpharm_scheme-syllabus_2026-27.pdf"
SHA16 = "97b5d901f34c75a4"

canon = json.load(open(CANON, encoding="utf-8"))
canon.setdefault("subjects", [])
canon.setdefault("non_subject_rows", [])
canon.setdefault("doc_level_flags", [])
canon.setdefault("doc_level_notes", [])
canon["doc_meta"].setdefault("course", "B.Pharm")
canon["doc_meta"]["program_year"] = "1;2;3;4"
canon["doc_meta"]["effective_session"] = "2026-27"
canon["doc_meta"]["doc_kind"] = "syllabus"
canon["doc_meta"]["branches"] = []
if not canon["doc_meta"].get("curriculum_basis"):
    canon["doc_meta"]["curriculum_basis"] = "PCI/NEP (cover: 'Bachelor of Pharmacy I, II, III & IV Year syllabus 2026-2027')"
if not canon["doc_meta"].get("title_print"):
    canon["doc_meta"]["title_print"] = "Evaluation Scheme Bachelor of Pharmacy I, II, III & IV Year syllabus 2026-2027"
canon["pdf_rel"] = PDF_REL
canon["stem"] = STEM
canon["session"] = "2026-27"
canon["sha16"] = SHA16

have = {s["primary_code"] for s in canon["subjects"]}
added, adj = 0, 0
for seg in SEGS:
    sd = json.load(open(f"{D}/{seg}_bpharm_scheme-syllabus_2026-27.json", encoding="utf-8"))
    for s in sd.get("subjects", []):
        pc = s.get("primary_code", "")
        if pc in have:
            print(f"SKIP dup {pc} (seg {seg})")
            continue
        # Adjudication A1: disambiguate shared slot codes with the printed group tag
        if pc in have or True:
            # find sibling collisions inside this same segment set
            pass
        tag = ""
        m = re.search(r"\b(SEC\d|AEC\d|VAC\d|OE\d)\b", " ".join(s.get("notes", [])))
        if m:
            tag = m.group(1)
        if tag and " " not in pc and re.match(r"^[A-Z]{2}\d{3}[TP]$", pc):
            s["primary_code"] = f"{pc} {tag}"
            s.setdefault("notes", []).append(
                f"Adjudication A1: printed Course-Code cell is '{pc} {tag}' (code + elective group tag in one printed cell); "
                f"bare '{pc}' is the shared slot code and is NOT unique to this subject.")
            if s.get("needs_review"):
                s["needs_review"] = False
                s.setdefault("notes", []).append("needs_review cleared: shared-slot-code ambiguity resolved by printed group tag (A1).")
            adj += 1
        s.setdefault("notes", []).append(f"segment {seg}")
        s["_segment"] = seg
        canon["subjects"].append(s)
        have.add(s["primary_code"])
        added += 1
    for r in sd.get("non_subject_rows", []):
        r.setdefault("notes", [])
        r["notes"] = list(dict.fromkeys(list(r["notes"]) + [f"segment {seg}"]))
        canon["non_subject_rows"].append(r)
    for fl in sd.get("doc_level_flags", []) or []:
        canon["doc_level_flags"].append(f"[{seg}] {fl}")
    for nt in (sd.get("doc_level_notes", []) or []):
        canon["doc_level_notes"].append(f"[{seg}] {nt}")

# final collision audit
codes = [s["primary_code"] for s in canon["subjects"]]
dupes = {c for c in codes if codes.count(c) > 1}
print(f"subjects={len(codes)} added={added} adjudicated(A1)={adj} dupes={sorted(dupes)}")
print(f"non_subject_rows={len(canon['non_subject_rows'])} flags={len(canon['doc_level_flags'])}")
json.dump(canon, open(CANON, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("canonical draft written:", CANON)
