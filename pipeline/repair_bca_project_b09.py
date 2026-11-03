#!/usr/bin/env python3
"""repair_bca_project_b09.py — B09 baseline course-boundary repair (RULES §1b,
owner directive 2026-10-28; B03-prep/B06-recovery precedent class).

DEFECT (discovered during B09 pre-merge adjudication, evidence: the published
777-row CSV @ 6fad305): the BCA row `project` (BBC652, 2026-27, sem-6,
scheme-only print) carries BTech/AG code ownership and detailed content that
B08's cross-draft convergence overrides wrote onto it:
    all_codes: BBC652;NAG852;KCS753;KCS851
    code_history: 'NAG852 (2016-17) ... btech_ag_y4_syllabus_2016-17.pdf' and
                  'KCS753 + KCS851 (2024-25) ... btech_ai-ds_y4_syllabus_2024-25.pdf'
Root cause: the TIER2_OVERRIDES resolution `next(r for r in rows if
r['subject_id'] == target)` matches subject_id WITHOUT a course filter — the
BCA 'project' row (created B04) precedes the BTech AG-slot row (appended in
the same commit as 'project', G3-suffixed to 'project-btech'), so the B08
overrides '02_btech_ag_y4_syllabus_2016-17::26::project' and
'07_btech_ai-ds_y4_syllabus_2024-25::16::project' updated the BCA row.
Per RULES §1b the same name in two courses is TWO subjects: the AG/BTech
project-slot codes and prints must never live on a BCA row.

REPAIR (append-only history, verbatim evidence preserved in change_note):
  1. BCA 'project' row: restored to its pre-B08 scheme-row-only state —
     all_codes='BBC652'; BTech-sourced unit/CO/book/objective fields cleared
     (the BCA 2026-27 print is scheme-only, so ALL detailed content on this
     row is BTech-sourced); has_detailed_syllabus=FALSE; source_syllabus/
     source_history reduced to the bca_y3 citations; name_print suffix from
     detailed-doc updates removed. Repair note appended to change_note.
  2. BTech 'project-btech' row (the B08-intended convergence target, NAG753,
     'Project', sem-7 AG slot): gains NAG852 (the 2016-17 AG Sem-VIII slot
     code, per the recorded B08 override '02::26' intent). KCS753/KCS851 and
     the 2024-25 CO content arrive via this batch's own doc01::15 update
     (T1 name identity 'Project'), completing the recorded B08 '07::16'
     intent course-correctly.

Idempotent; asserts preconditions; prints REPAIR_OK|... or REPAIR_SKIP.
"""
import csv, sys

CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
BCA_REL = "syllabus_catalog/syllabus_extreme_rich.csv"  # synced at push time

CLEAR_FIELDS = [
    "unit1_text", "unit2_text", "unit3_text", "unit4_text", "unit5_text",
    "co1_text", "co2_text", "co3_text", "co4_text", "co5_text", "co6_text",
    "co_kls", "units_count", "co_count", "lectures_per_unit",
    "textbooks_structured", "reference_books_structured",
    "experiments_structured", "objectives_print", "prerequisites",
    "eligibility_print",
]


def main():
    with open(CSV, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        rows = list(reader)

    bca = next((r for r in rows if r["subject_id"] == "project" and r["course_name"] == "BCA"), None)
    btech = next((r for r in rows if r["subject_id"] == "project-btech"), None)
    if not bca or not btech:
        print("REPAIR_FAIL|rows not found"); return 1

    moved = [c for c in bca["all_codes"].split(";") if c and c != "BBC652"]
    if not moved:
        print("REPAIR_SKIP|BCA project row already clean")
        return 0
    assert set(moved) == {"NAG852", "KCS753", "KCS851"}, f"unexpected codes {moved}"

    # 1. restore the BCA row
    for f in CLEAR_FIELDS:
        if bca.get(f):
            bca[f] = ""
    bca["has_detailed_syllabus"] = "FALSE"
    bca["all_codes"] = "BBC652"
    if " | detailed-doc print:" in (bca.get("subject_name_print") or ""):
        bca["subject_name_print"] = bca["subject_name_print"].split(" | detailed-doc print:")[0]
    # provenance: keep only the bca_y3 citations
    for fld in ("source_syllabus", "source_history"):
        keep = [seg.strip() for seg in (bca.get(fld) or "").split(";")
                if "bca_y3_syllabus_2026-27" in seg]
        bca[fld] = "; ".join(keep)
    note = ("B09 course-boundary repair (repair_bca_project_b09.py, RULES §1b owner "
            "directive 2026-10-28): the BTech/AG codes NAG852;KCS753;KCS851 and the BTech-docs "
            "detailed content parked on this BCA row by the B08 cross-draft convergence overrides "
            "(their subject_id match lacked a course filter and hit this B04-created BCA 'project' "
            "row instead of the BTech AG-slot row) are REMOVED — the same printed name in two "
            "courses is TWO subjects; the codes move to the BTech project-btech slot row; row "
            "restored to its pre-B08 scheme-row-only state (BCA 2026-27 print is scheme-only).")
    if "B09 course-boundary repair" not in (bca.get("change_note_vs_previous") or ""):
        bca["change_note_vs_previous"] = ((bca.get("change_note_vs_previous") or "") + "; " + note).strip("; ")

    # 2. move NAG852 to the BTech slot row (KCS753/KCS851 arrive via doc01::15)
    btech_codes = [c for c in (btech["all_codes"] or "").split(";") if c]
    added = []
    for code in moved:
        if code not in btech_codes:
            btech_codes.append(code)
            added.append(code)
    btech["all_codes"] = ";".join(btech_codes)
    if added:
        seg = ("; " + ", ".join(added) + " (2016-17/2024-25 BTech project-slot codes) - repaired "
               "from the BCA 'project' row where the B08 cross-draft convergence parked them "
               "(override subject_id match lacked a course filter); RULES §1b course-boundary "
               "repair, B09 (repair_bca_project_b09.py)")
        if "repaired from the BCA 'project' row" not in (btech.get("code_history_all") or ""):
            btech["code_history_all"] = (btech.get("code_history_all") or "") + seg
        btech["change_note_vs_previous"] = ((btech.get("change_note_vs_previous") or "") + "; " +
            f"B09 course-boundary repair: {', '.join(added)} ownership moved from the BCA project row "
            "to this BTech slot row (B08 convergence intent, course-correct); evidence in change_note "
            "of the BCA row and repair_bca_project_b09.py").strip("; ")

    with open(CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)
    print(f"REPAIR_OK|bca_project codes->BBC652; btech project-btech all_codes+={added}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
