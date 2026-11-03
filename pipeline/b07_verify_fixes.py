#!/usr/bin/env python3
"""b07_verify_fixes.py — remediate the two verify_draft FAILs:
D03: mark RVE301/RAS302/RME101/RCE151 as scheme-only (no detail sections printed).
D10: mark RAG753/RAG754/RAG851/RAG852 scheme-only with scheme-row evidence;
     move RAG085(+noc19-ar01 NPTEL pool item) from subjects to elective_pool nsr.
Print evidence from fulltext pages cited. Idempotent.
"""
import json

D3 = "/home/z/my-project/work/pipeline_v2/drafts/03_btech_ag_y2_scheme-syllabus_2017-18.draft.json"
D10 = "/home/z/my-project/work/pipeline_v2/drafts/10_btech_ag_y4_syllabus-cbcs_2019-20.draft.json"

def fix_d3():
    d = json.load(open(D3))
    n = 0
    for s in d["subjects"]:
        c0 = (s.get("codes") or [None])[0]
        if c0 in ("RVE301", "RAS302", "RME101", "RCE151") and "scheme-only" not in (s.get("flags") or []):
            s.setdefault("flags", []).append("scheme-only")
            s.setdefault("quirks", []).append(
                "Scheme-only in this doc: the printed scheme table carries the row but no detail "
                "section (units/COs/books) is printed anywhere in the 18-page document (pp.2-3 scheme).")
            n += 1
    json.dump(d, open(D3, "w"), indent=1, ensure_ascii=False)
    print("D3 scheme-only flags added:", n)

def fix_d10():
    d = json.load(open(D10))
    SR = {
        "RAG753": "8 RAG753 Industrial Training Lab core Department 0---0---3 100 100 2 (Sem-VII scheme p.2)",
        "RAG754": "9 RAG754 Project-1 Lab 0---0---6 200 200 3 (Sem-VII scheme p.2)",
        "RAG851": "4 RAG851 GD & Seminar core Department 0---0---3 100 100 2 (Sem-VIII scheme p.3)",
        "RAG852": "5 RAG852 Project-2 core Department 0---0---12 350 250 600 12 (Sem-VIII scheme p.3)",
    }
    n = 0
    keep = []
    removed_rag085 = None
    for s in d["subjects"]:
        c0 = (s.get("codes") or [None])[0]
        if c0 == "RAG085":
            removed_rag085 = s
            continue  # move to elective_pool nsr (pool-only NPTEL item, same class as RAG091)
        if c0 in SR and "scheme-only" not in (s.get("flags") or []):
            s.setdefault("flags", []).append("scheme-only")
            s.setdefault("scheme_rows", []).append({"semester": s.get("semester"), "print": SR[c0]})
            s.setdefault("quirks", []).append(
                "Scheme-only assessment row: printed in the semester scheme table only; the document "
                "prints no detail section (units/COs/books) for it.")
            n += 1
        keep.append(s)
    d["subjects"] = keep
    if removed_rag085 is not None:
        pool = {"kind": "elective_pool",
                "print": ("Deptt. Elective course-5 pool item 6: RAG085 Novel Technologies for Food "
                          "Processing and Shelf Life | Extension (NPTEL) (p.3); Department Elective "
                          "course-6 listing: noc19-ar01 Novel Technologies for Food Processing and "
                          "Shelf Life (Note- As per NPTEL course content) (p.16)"),
                "locator": "pp.3,16",
                "note": ("Converted from a draft subject entry during verify remediation: both printed "
                         "occurrences are elective-pool listings (the p.16 one carries the NPTEL course "
                         "code noc19-ar01 and note 'As per NPTEL course content'); no detail section "
                         "printed — same class as RAG091 which the draft already recorded as pool-only."),
                "codes_print": ["RAG085", "noc19-ar01"]}
        if not any("RAG085" in str(r.get("codes_print") or "") for r in d.get("non_subject_rows", [])):
            d.setdefault("non_subject_rows", []).append(pool)
    json.dump(d, open(D10, "w"), indent=1, ensure_ascii=False)
    print("D10 scheme-only flags added:", n, "| RAG085 moved to nsr:", removed_rag085 is not None,
          "| subjects:", len(d["subjects"]))

if __name__ == "__main__":
    fix_d3()
    fix_d10()
