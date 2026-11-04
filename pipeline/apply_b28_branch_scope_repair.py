#!/usr/bin/env python3
"""apply_b28_branch_scope_repair.py — post-commit repair (recorded B21/B24/B27 class).

The B28 merge ran without DOC_SCOPE entries for the batch's stems, so the 50
appended rows carried empty branch_names. This repair sets branch_names from
each document's PRINTED COVER (zero-guess, exactly the printed scope):

- IT docs (covers print 'Information Technology'):
    btech_it_syllabus_2015-16            p.1 'SYLLABUS Bachel[or]... Information Technology'
    btech_it_syllabus_2016-17            (stem + NIT/NOE codes; cover/running header IT)
    btech_it_y2_model-curriculum_2019-20 p.1 'B.Tech. 2nd Year (Information Technology)'
    btech_it_y2_scheme-syllabus_2009-10  p.1 'Syllabus of Information Technology 2nd Year (III & IV Sem.)'
    btech_it_y2_scheme-syllabus_2017-18  p.1 'B.Tech. Second Year Information Technology'
    btech_it_y2_syllabus-rev_2014-15     cover 'B.TECH. INFORMATION TECHNOLOGY'
    btech_it_y4_syllabus-cbcs_2019-20    p.1 'B.Tech. Fourth Year (Information Technology)'
    btech_it_y4_syllabus_2021-22         cover print (scrambled text layer) 'INFORMATION TECHNOLOGY'
  → branch_names 'Information Technology'

- btech_me-ind-pe-ipe_y4_syllabus_2016-17 p.1:
    'B. Tech. Mechanical Engineering / Production Engineering / Industrial &
     Production Engineering / Mechanical & Industrial Engineering [Effective
     from Session 20016-17 (sic)]'  — 4 printed branches
  → 'Mechanical Engineering;Production Engineering;Industrial & Production
     Engineering;Mechanical & Industrial Engineering'
  EXCEPTION (printed sem-VIII split, p.2): NPI-801 QUALITY CONTROL is printed
  under 'B. Tech. Production Engineering / Industrial & Production Engineering /
  Mechanical & Industrial Engineering' (3 branches) — the split is printed
  evidence (RULES §4: conclusive print evidence, keep proof).

- btech_me-ind_syllabus_2020-21 p.1 (scrambled text layer; draft scheme-summary
  and TOC prints 'B. Tech Mechanical & Industrial Engineering'):
  → 'Mechanical & Industrial Engineering'

Only rows appended by B28 are touched (change_note starts 'First ingestion'
AND source_syllabus cites one of the 10 batch sha16s). Gates G2/G3 are not
code-affecting; postcommit_verify re-run after the repair.
"""
import csv, sys

CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"

BATCH_SHA16S = {
    "5c9b900ce01c01e2": "Information Technology",                # 01 IT 2015-16
    "3f83735be23e91f4": "Information Technology",                # 02 IT 2016-17
    "e44ca075e8598a1c": "Information Technology",                # 03 IT y2 2019-20
    "377d5661e94123a6": "Information Technology",                # 04 IT y2 2009-10
    "3b33f0320c9b61d1": "Information Technology",                # 05 IT y2 2017-18
    "43eec64d11cdf3e2": "Information Technology",                # 06 IT y2 2014-15
    "3275781ab6bad835": "Information Technology",                # 07 IT y4 2019-20
    "7901eb38c7e30d04": "Information Technology",                # 08 IT y4 2021-22
    "567c7444bd3db972": ("Mechanical Engineering;Production Engineering;"
                         "Industrial & Production Engineering;"
                         "Mechanical & Industrial Engineering"),  # 09 ME/PE/IPE/ME&I 2016-17
    "ac5aa46cc1cddded": "Mechanical & Industrial Engineering",   # 10 ME&I 2020-21
}

# printed sem-VIII split exceptions (doc09 p.2/p.3)
SUBJECT_SCOPE = {
    "NPI-801": ("Production Engineering;Industrial & Production Engineering;"
                "Mechanical & Industrial Engineering",
                "printed sem-VIII split: scheme page p.2 headers 'B. Tech. Production "
                "Engineering / Industrial & Production Engineering / Mechanical & "
                "Industrial Engineering'"),
}


def main():
    with open(CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    fieldnames = list(rows[0].keys())
    fixed = 0
    for r in rows:
        cn = r.get("change_note_vs_previous") or ""
        if not cn.startswith("First ingestion"):
            continue
        src = r.get("source_syllabus") or ""
        sha = next((s for s in BATCH_SHA16S if s in src), None)
        if not sha:
            continue
        primary = (r.get("primary_code") or "").strip()
        scope, evidence = SUBJECT_SCOPE.get(primary, (BATCH_SHA16S[sha], "printed cover scope"))
        if (r.get("branch_names") or "").strip() == scope:
            continue
        r["branch_names"] = scope
        r["notes"] = (r.get("notes") or "") + (
            " | B28 post-commit repair: branch_names set from the document's printed "
            "scope (" + evidence + "; SCOPE-FROM-DOC recorded class — the merge ran "
            "without DOC_SCOPE entries for the batch stems)")
        r["change_note_vs_previous"] = cn + "; B28 repair: branch_names recorded from the printed cover scope"
        fixed += 1
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"REPAIR|branch_names set on {fixed} B28-appended rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
