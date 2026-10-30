#!/usr/bin/env python3
"""repair_b10_branch_scope.py — B10 recorded repair (precedent:
repair_bca_project_b09.py / repair_baseline_g2g3.py).

The B10 commit appended 103 subject rows whose branch_names were empty
because the batch's sha16s had no DOC_SCOPE entries (the doc-level scope
mechanism keys on per-batch sha16 evidence recorded before the merge; B10's
covers were never registered). The printed covers ARE the evidence (RULES §4
brain clause: determine-then-fix, keep proof) — each doc's cover names its
program/branches verbatim:

  5237159af8a1340a (AE/ECE-EI 2016-17 _2): "1. B.Tech. Electronics &
      Instrumentation Engineering 2. B.Tech. Instrumentation & Control
      Engineering 3. B. Tech. Applied Electronics and Control Engineering"
  b2dc3fa57caad0e2 / 75947478b3678052 / 5d9d6484c223ec7d /
  6278e31233d5562d (AU y4 2019-20/2016-17/2021-22/2025-26):
      "B. TECH (.) 4th YEAR AUTOMOBILE ENGINEERING"
  3e82cd204b7939f2 / 339f5932bb1f1bd8 (Bioinformatics y2 2025-26 / y3
      2026-27): "B. TECH. (2nd/THIRD) YEAR BIOINFORMATICS"
  5cc5a89a9c439987 / d71e761d73879ea5 (BME 2009-10/2011-12):
      "B.TECH. BIOMEDICAL ENGINEERING"
  ba8f92863189a2b2 (BME y2 model-curriculum 2019-20): "B. TECH. SECOND YEAR
      BIOMEDICAL ENGINEERING" — its appended subjects (Network Analysis and
      Synthesis + Lab, Communication Engineering Lab) get exactly this cover
      scope; zero extrapolation to the E&C-common 15-branch list that other
      docs' covers print (SCOPE-FROM-DOC rule).

Backfill rule: ONLY rows whose FIRST source_syllabus citation is one of the
B10 docs (rows established by this batch) AND whose branch_names is currently
EMPTY — never overwrites any existing scope (including the multi-branch
E&C-common scope the pre-existing rows carry).
"""
import csv, re, shutil, sys
from datetime import datetime

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"

BRANCH_SCOPE = {
    "5237159af8a1340a": "Electronics & Instrumentation Engineering;Instrumentation & Control Engineering;Applied Electronics and Control Engineering",
    "b2dc3fa57caad0e2": "Automobile Engineering",
    "75947478b3678052": "Automobile Engineering",
    "5d9d6484c223ec7d": "Automobile Engineering",
    "6278e31233d5562d": "Automobile Engineering",
    "3e82cd204b7939f2": "Bioinformatics",
    "339f5932bb1f1bd8": "Bioinformatics",
    "5cc5a89a9c439987": "Biomedical Engineering",
    "d71e761d73879ea5": "Biomedical Engineering",
    "ba8f92863189a2b2": "Biomedical Engineering",
}
COVER_EVIDENCE = {
    "5237159af8a1340a": "cover prints '1. B.Tech. Electronics & Instrumentation Engineering 2. B.Tech. Instrumentation & Control Engineering 3. B. Tech. Applied Electronics and Control Engineering'",
    "b2dc3fa57caad0e2": "cover prints 'STUDY & EVALUATION SCHEME WITH SYLLABUS FOR B. TECH 4th YEAR AUTOMOBILE ENGINEERING ON CHOICE BASED CREDIT SYSTEM'",
    "75947478b3678052": "cover prints 'YEAR IV, SEMESTER-VII B.Tech. Automobile Engineering'",
    "5d9d6484c223ec7d": "cover prints 'STUDY & EVALUATION SCHEME WITH SYLLABUS FOR B. TECH. 4th YEAR AUTOMOBILE ENGINEERING'",
    "6278e31233d5562d": "cover prints 'COURSE STRUCTURE/EVALUATION SCHEME FOR B.TECH. 4th YEAR AUTOMOBILE ENGINEERING'",
    "3e82cd204b7939f2": "cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. 2nd YEAR BIOINFORMATICS Based On AICTE Model Curriculum & NEP2020'",
    "339f5932bb1f1bd8": "cover prints 'EVALUATION SCHEME & SYLLABUS B. TECH. THIRD YEAR BIOINFORMATICS (As per AICTE Model Curriculum & NEP 2020)'",
    "5cc5a89a9c439987": "cover prints 'Syllabus 3rd Year (V & VI Semester) B.TECH. BIOMEDICAL ENGINEERING'",
    "d71e761d73879ea5": "cover prints 'Syllabus B.TECH. BIOMEDICAL ENGINEERING (Effective from Session 2011-12)'",
    "ba8f92863189a2b2": "cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. SECOND YEAR BIOMEDICAL ENGINEERING AS PER AICTE MODEL CURRICULUM'",
}


def main():
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        rows = list(reader)
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    n = 0
    per_sha = {}
    for r in rows:
        if r.get("row_kind") != "subject":
            continue
        if (r.get("branch_names", "") or "").strip():
            continue
        src = r.get("source_syllabus", "") or ""
        m = re.search(r"#([0-9a-f]{16})", src)
        if not m or m.group(1) not in BRANCH_SCOPE:
            continue
        sha = m.group(1)
        r["branch_names"] = BRANCH_SCOPE[sha]
        note = (f"B10 branch-scope repair ({ts}): branch_names backfilled from the establishing "
                f"document's own cover — {COVER_EVIDENCE[sha]} (repair_b10_branch_scope.py; "
                f"SCOPE-FROM-DOC rule, zero extrapolation)")
        r["change_note_vs_previous"] = ((r.get("change_note_vs_previous", "") + "; ") if r.get("change_note_vs_previous", "") else "") + note
        per_sha[sha] = per_sha.get(sha, 0) + 1
        n += 1
    bkp = CSV_PATH.replace(".csv", ".pre_b10_branch_repair.csv")
    shutil.copy(CSV_PATH, bkp)
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in header})
    print(f"BRANCH_REPAIR|rows_backfilled={n}|backup={bkp}")
    for sha, c in sorted(per_sha.items()):
        print(f"  {sha}: {c} rows -> {BRANCH_SCOPE[sha]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
