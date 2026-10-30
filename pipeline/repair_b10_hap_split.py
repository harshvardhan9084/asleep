#!/usr/bin/env python3
"""repair_b10_hap_split.py — B10 recorded repair (post-commit, precedent:
repair_bca_project_b09.py).

Live-commit Tier-2 fuzzy 92/34 wrongly converged 09::08 'HUMAN ANATOMY AND
PHYSIOLOGY' (EBM-401, sem-IV) into the human-anatomy-physiology row
('HUMAN ANATOMY & PHYSIOLOGY', EBM-503, sem-V). They are TWO different
subjects per the 2011-12 BME print's own structure:

  EBM-401  sem-4  L-T-P 3-1-0  Cr 4  marks 30/20/50 | 100 | 150
           u1 'Basic cell Structure, various cell organelles...and their
           function. Tissue...' u2 Blood/Lymph/Circulation, u3 Respiratory,
           u4 Renal, u5 Nervous system and special senses (OCR p.14,
           unit_ocr_recovered_no_text_layer, page-image verified)
           + its own printed sem-IV lab EBM-451 'ANATOMY & PHYSIOLOGY LAB'
  EBM-503  sem-5  L-T-P 3-0-0  Cr 3  marks 15/10/25 | 50 | 75
           u1 'Structure & functions of cell. Polarization & depolarization
           of cell...' u2-u4 CV/cardiovascular/blood (text layer, contained)

RULES §11 (never merge two different subjects) — the codes differ, the
semester slots differ, the printed LTP/credit/marks differ and the unit
texts share no content. The commit left the row in a MIXED state: units 1-4
= EBM-503 (09::18's fieldwise-wins overwrite) but unit5 = EBM-401 residue,
and all_codes = 'EBM-503;EBM-401' (EBM-401 mis-owned).

Repair:
  1. human-anatomy-physiology row: drop the EBM-401 residue (unit5_text='',
     units_count=4, all_codes='EBM-503') and record the narrative in
     code_history_all + change_note.
  2. Append the missing sem-IV subject row 'HUMAN ANATOMY AND PHYSIOLOGY'
     (EBM-401) built from the 09::08 draft verbatim, with the OCR evidence
     note, branch Biomedical Engineering (cover print), and provenance
     citation to the 2011-12 doc.
  3. Re-check G2 (single ownership per code, within course), G3 (subject_id
     and (name, course) uniqueness) inline.
"""
import csv, json, re, shutil, sys
from datetime import datetime

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
DRAFT = "/home/z/my-project/work/pipeline_v2/drafts/09_btech_bme_syllabus_2011-12.draft.json"
HEADER = None  # loaded at runtime


def norm_code(c):
    return re.sub(r"[^A-Z0-9]", "", str(c).upper())


def main():
    global HEADER
    d = json.load(open(DRAFT))
    s401 = d["subjects"][8]
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        HEADER = reader.fieldnames
        rows = list(reader)
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    by_sid = {r["subject_id"]: r for r in rows}
    assert "human-anatomy-physiology" in by_sid, "target row missing"
    # §1b: subject_id is GLOBALLY unique — the bare slug is owned by the
    # BPharm row ('HUMAN ANATOMY AND PHYSIOLOGY', bpharm_y1-4_syllabus_2019-20,
    # BP107P history). Different course + same name = TWO subjects (RULES
    # §1b); suffix the course per the recorded convention.
    NEW_SID = "human-anatomy-and-physiology-btech"
    assert NEW_SID not in by_sid, "new sid already taken"

    # 1. clean the EBM-503 row
    row = by_sid["human-anatomy-physiology"]
    assert "EBM401" in [norm_code(c) for c in row["all_codes"].split(";")], "expected EBM-401 residue"
    row["all_codes"] = "EBM-503"
    row["unit5_text"] = ""
    row["units_count"] = "4"
    row["code_history_all"] = (row.get("code_history_all", "") + "; EBM-401 moved to the separate "
        f"sem-IV course row {NEW_SID} — the 2011-12 print carries BOTH courses "
        f"(sem-IV EBM-401 3-1-0 Cr4 + its own lab EBM-451, and sem-V EBM-503 3-0-0 Cr3); live-commit "
        f"fuzzy 92/34 had wrongly converged them (repair_b10_hap_split.py, {ts})").strip("; ")
    row["change_note_vs_previous"] = (row.get("change_note_vs_previous", "") + "; " if row.get("change_note_vs_previous", "") else "") + \
        (f"HAP split repair ({ts}): EBM-401 (sem-IV) residue removed from this sem-V course row; "
         f"unit5 residue cleared (units 1-4 are the EBM-503 print); the sem-IV subject now has its own row")

    # 2. build the EBM-401 row (mirror build_append field semantics)
    src = "btech_bme_syllabus_2011-12.pdf#d71e761d73879ea5 pp.13-14"
    new = {c: "" for c in HEADER}
    new.update({
        "subject_id": NEW_SID,
        "row_kind": "subject",
        "subject_name": "HUMAN ANATOMY AND PHYSIOLOGY",
        "subject_name_print": s401.get("name_print", "EBM 401 HUMAN ANATOMY AND PHYSIOLOGY"),
        "primary_code": "EBM-401",
        "all_codes": "EBM-401",
        "code_history_all": "EBM-401 (2011-12, sem-4)",
        "status": "latest",
        "university_name": "Dr. A.P.J. Abdul Kalam Technical University, Lucknow",
        "course_name": "BTech",
        "branch_names": "Biomedical Engineering",
        "program_year": "2",
        "semester_slots": "4",
        "effective_session_latest": "2011-12",
        "first_introduced_session": "2011-12",
        "subject_type": "core",
        "l": "3", "t": "1", "p": "0",
        "credit": "4",
        "sessional_ct": "30", "sessional_ta": "20", "sessional_total": "50",
        "ese_te_pe": "100", "total_marks": "150",
        "lectures_per_unit": "",
        "source_syllabus": src,
        "source_scheme_line": f"{src} (EBM 401 HUMAN ANATOMY AND PHYSIOLOGY, 3-1-0, 30/20/50|100|150 — sem-IV scheme row)",
        "source_history": f"{src} (detailed syllabus ingested 2011-12)",
        "has_detailed_syllabus": "TRUE",
        "change_note_vs_previous": (f"Row appended by repair_b10_hap_split.py ({ts}): the 2011-12 BME print's "
            f"sem-IV course, split from the wrongful live-commit convergence into the sem-V EBM-503 row "
            f"(fuzzy 92/34 rejected with recorded evidence — different codes, semester slots, LTP/credit/"
            f"marks and unit content; RULES §11)"),
    })
    units = s401.get("units") or {}
    for n in range(1, 6):
        new[f"unit{n}_text"] = units.get(str(n), "")
    new["units_count"] = str(sum(1 for n in range(1, 6) if new[f"unit{n}_text"]))
    cos = s401.get("cos") or []
    if cos:
        new["co1_text"] = cos[0].get("text", "")
        new["co_count"] = str(len(cos))
    new["notes"] = ("PATCH-B10: unit text transcribed from scanned-image page 14 whose PyMuPDF text layer is "
        "EMPTY (parsed json: text_len 0); page-image spot-check confirms the transcription is faithful to the "
        "visible print (RULES §6: visible print authoritative) — unit_ocr_recovered_no_text_layer evidence "
        "(patch_b10_verify_fixes.py / repair_b10_hap_split.py) | Course-boundary crossref (RULES §1b): same "
        "subject name exists as the BPharm row human-anatomy-and-physiology (BP107P, sem-1 practical print) — "
        "kept separate; course boundaries are real.")
    rows.append(new)

    # 3. gate spot-checks — reuse the pipeline's REAL gates (import keeps the
    # probe semantically identical to the commit-time G2/G3, incl. the
    # course-scoped ownership semantics of RULES §5)
    sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
    import merge_draft as md
    g2, ncodes = md.gate_g2(rows)
    g3 = md.gate_g3(rows)
    if g2 or g3:
        print(f"GATE_PROBE|G2: {g2}")
        print(f"GATE_PROBE|G3: {g3}")
        return 2
    print(f"GATE_PROBE|G2 PASS codes={ncodes}; G3 PASS")

    bkp = CSV_PATH.replace(".csv", ".pre_b10_hap_repair.csv")
    shutil.copy(CSV_PATH, bkp)
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in HEADER})
    print(f"HAP_SPLIT_OK|rows={len(rows)-1} backup={bkp}")
    print(f"  human-anatomy-physiology: EBM-401 residue removed (all_codes=EBM-503, unit5 cleared)")
    print(f"  {NEW_SID}: appended (EBM-401, sem-4, 2011-12, 5 units, OCR-evidenced, §1b crossref to the BPharm row)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
