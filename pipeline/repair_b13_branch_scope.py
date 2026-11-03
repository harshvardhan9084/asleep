#!/usr/bin/env python3
"""repair_b13_branch_scope.py — B13 recorded repair (precedent:
repair_b10_branch_scope.py).

The B13 commits (pass 1 + the doc04 pass-2 recovery) appended 118 subject rows
whose branch_names were empty and whose program_year was defaulted to '2',
because the batch's 10 sha16s had no DOC_SCOPE entries registered before the
merge. The printed covers ARE the evidence (RULES §4 determine-then-fix, keep
proof) — each draft's recorded cover quirk quotes the branch verbatim:

  2ac6e53d06c52026 (carpet y2-y4 syllabus 2009-10): cover prints
      'U.P. TECHNICAL UNIVERSITY, LUCKNOW — Syllabus 2nd , 3rd and 4th Year
      [Effective from session 2009-10] — B.TECH. CARPET & TEXTILE TECHNOLOGY'
      — multi-year doc: program_year mapped per-row from the row's own
      semester_slots (III/IV→2, V/VI→3, VII/VIII→4; structural mapping).
  85fc0a911e174919 (y2 model-curriculum 2019-20): 'Carpet & Textile
      Technology' under 'B. TECH. SECOND YEAR' → year 2.
  5e07ff5fe10cd6c3 (y2 scheme-syllabus 2017-18): 'B.Tech. Second Year Carpet
      And Textile Technology' → year 2 (cover variant 'And' recorded).
  641f700a7ab5d96d (y3 model-curriculum 2020-21): cover 'B.TECH. THIRD YEAR
      CARPET & TEXTILE TECHNOLOGY' (per draft quirk) → year 3.
  c891df6c0f371cb2 (y3 syllabus 2018-19): 'B. TECH. THIRD YEAR (CARPET AND
      TEXTILE TECHNOLOGY)' → year 3 (cover variant 'AND' recorded).
  020ea64f9757080b (y3 syllabus 2024-25): 'B. TECH. THIRD YEAR / Carpet &
      Textile Technology' → year 3.
  fe2cf38bfff60b34 (y4 syllabus-cbcs 2019-20): 'B. TECH 4th YEAR Carpet &
      Textile Technology' → year 4.
  37283cd70588ae6e (y4 syllabus 2021-22): cover doubled-glyph garble
      'CARPET C T & TEX XTILE TE ECHNOL LOGY', reconstructed CARPET & TEXTILE
      TECHNOLOGY (page-image evidence in draft quirks) → year 4.
  874148082be7bca8 (y4 syllabus 2025-26): 'B. TECH. FOURTH YEAR' + 'Carpet &
      Textile Technology' → year 4.
  fb01885f539db1af (ce-cse y4 2025-26): cover prints THREE branches
      'Computer Science', 'Computer Engineering', 'Computer Science and
      Engineering' (combined CS/CE/CSE scheme; cover authoritative) → year 4.

Canonical branch form 'Carpet & Textile Technology' = the majority cover print
(6 of 9 covers print '&' as printed; the 'And'/'AND' variants of docs 03/05 are
kept verbatim in this record and the change notes).

Backfill rule: ONLY rows whose FIRST source_syllabus citation is one of the
B13 docs (rows established by this batch) AND whose branch_names is currently
EMPTY — never overwrites any existing scope (e.g. the Mathematics-III/OE slot
row intentionally carries the sister-common-subject branch profile per the
recorded SCOPE-FROM-MATHS-IV adjudication). program_year is corrected only
where the merge-time default '2' contradicts the establishing doc's printed
year (never guesses: the year comes from the same cover evidence).
"""
import csv, re, shutil, sys
from datetime import datetime

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"

CARPET = "Carpet & Textile Technology"
BRANCH_SCOPE = {
    "2ac6e53d06c52026": CARPET,
    "85fc0a911e174919": CARPET,
    "5e07ff5fe10cd6c3": CARPET,
    "641f700a7ab5d96d": CARPET,
    "c891df6c0f371cb2": CARPET,
    "020ea64f9757080b": CARPET,
    "fe2cf38bfff60b34": CARPET,
    "37283cd70588ae6e": CARPET,
    "874148082be7bca8": CARPET,
    "fb01885f539db1af": "Computer Science;Computer Engineering;Computer Science and Engineering",
}
# doc-level printed program year; None → per-row semester mapping (doc01).
DOC_YEAR = {
    "2ac6e53d06c52026": None,
    "85fc0a911e174919": "2",
    "5e07ff5fe10cd6c3": "2",
    "641f700a7ab5d96d": "3",
    "c891df6c0f371cb2": "3",
    "020ea64f9757080b": "3",
    "fe2cf38bfff60b34": "4",
    "37283cd70588ae6e": "4",
    "874148082be7bca8": "4",
    "fb01885f539db1af": "4",
}
COVER_EVIDENCE = {
    "2ac6e53d06c52026": "cover prints 'Syllabus 2nd, 3rd and 4th Year [Effective from session 2009-10] — B.TECH. CARPET & TEXTILE TECHNOLOGY'",
    "85fc0a911e174919": "cover prints 'Carpet & Textile Technology' under 'B. TECH. SECOND YEAR'",
    "5e07ff5fe10cd6c3": "cover prints 'Study & Evaluation Scheme with Syllabus for B.Tech. Second Year Carpet And Textile Technology On Choice Based Credit System'",
    "641f700a7ab5d96d": "cover prints 'B.TECH. THIRD YEAR CARPET & TEXTILE TECHNOLOGY' (model-curriculum 2020-21)",
    "c891df6c0f371cb2": "cover prints 'B. TECH. THIRD YEAR (CARPET AND TEXTILE TECHNOLOGY)'",
    "020ea64f9757080b": "cover prints 'B. TECH. THIRD YEAR / Carpet & Textile Technology' [Effective from the Session: 2024-25]",
    "fe2cf38bfff60b34": "cover prints 'B. TECH 4th YEAR Carpet & Textile Technology'",
    "37283cd70588ae6e": "cover doubled-glyph garble 'CARPET C T & TEX XTILE TE ECHNOL LOGY' reconstructed to CARPET & TEXTILE TECHNOLOGY (page-image evidence)",
    "874148082be7bca8": "cover prints 'B. TECH. FOURTH YEAR' + branch 'Carpet & Textile Technology'",
    "fb01885f539db1af": "cover prints three branches 'Computer Science', 'Computer Engineering', 'Computer Science and Engineering' (combined CS/CE/CSE scheme)",
}


def year_for_row(sha, sem):
    y = DOC_YEAR[sha]
    if y is not None:
        return y
    s = str(sem or "")
    nums = [int(x) for x in re.findall(r"\d+", s)]
    n = nums[0] if nums else 0
    if n in (3, 4):
        return "2"
    if n in (5, 6):
        return "3"
    if n in (7, 8):
        return "4"
    return ""


def main():
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        rows = list(reader)
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    n_branch = n_year = 0
    per_sha = {}
    for r in rows:
        if r.get("row_kind") != "subject":
            continue
        src = r.get("source_syllabus", "") or ""
        m = re.search(r"#([0-9a-f]{16})", src)
        if not m or m.group(1) not in BRANCH_SCOPE:
            continue
        sha = m.group(1)
        ev = (f"B13 branch-scope repair ({ts}): from the establishing document's own "
              f"cover — {COVER_EVIDENCE[sha]} (repair_b13_branch_scope.py; "
              f"SCOPE-FROM-DOC rule, zero extrapolation)")
        if not (r.get("branch_names", "") or "").strip():
            r["branch_names"] = BRANCH_SCOPE[sha]
            r["change_note_vs_previous"] = ((r.get("change_note_vs_previous", "") + "; ")
                                            if r.get("change_note_vs_previous", "") else "") + ev
            n_branch += 1
            per_sha[sha] = per_sha.get(sha, 0) + 1
        cur_py = (r.get("program_year", "") or "").strip()
        want_py = year_for_row(sha, r.get("semester_slots", ""))
        if cur_py != want_py and want_py:
            note = (f"B13 program-year repair ({ts}): merge-time default '2' contradicted "
                    f"the establishing doc's printed year; set '{want_py}' from the same "
                    f"cover evidence (repair_b13_branch_scope.py)")
            r["program_year"] = want_py
            r["change_note_vs_previous"] = ((r.get("change_note_vs_previous", "") + "; ")
                                            if r.get("change_note_vs_previous", "") else "") + note
            n_year += 1
    bkp = CSV_PATH.replace(".csv", ".pre_b13_branch_repair.csv")
    shutil.copy(CSV_PATH, bkp)
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in header})
    print(f"BRANCH_REPAIR|branch_backfilled={n_branch}|year_fixed={n_year}|backup={bkp}")
    for sha, c in sorted(per_sha.items()):
        print(f"  {sha}: {c} rows -> {BRANCH_SCOPE[sha]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
