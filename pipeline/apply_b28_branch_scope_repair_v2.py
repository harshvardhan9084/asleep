#!/usr/bin/env python3
"""apply_b28_branch_scope_repair_v2.py — corrects v1 of the B28 scope repair.

v1's predicate (change_note startswith 'First ingestion' AND batch sha16 in
source_syllabus) ALSO matched pre-existing rows: apply_update fieldwise-wins
the source_syllabus citation to the newest doc, so a B01-era row updated by a
B28 IT doc now cites the B28 sha while keeping its ORIGINAL 'First ingestion'
note. v1 overwrote those rows' established branch_names.

v2 (this script):
 1. REVERT: for every row carrying the v1 repair marker whose subject_id
    exists in the B27 baseline CSV, restore branch_names from B27 and strip
    the v1 note segments (both the notes ' | B28 post-commit repair...' tail
    and the '; B28 repair...' change_note suffix).
 2. REAPPLY with the corrected predicate: the First-ingestion note must name
    one of the 10 B28 STEM FILES ('verbatim from <stem>.pdf') — the stem file
    is the append-time evidence (source_syllabus citations drift to newer docs,
    the append note does not).
"""
import csv, re, sys

CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
B27 = "/home/z/my-project/work/repo_asleep/syllabus_catalog/syllabus_extreme_rich.csv"

STEM_SCOPE = {
    "btech_it_syllabus_2015-16.pdf": "Information Technology",
    "btech_it_syllabus_2016-17.pdf": "Information Technology",
    "btech_it_y2_model-curriculum_2019-20.pdf": "Information Technology",
    "btech_it_y2_scheme-syllabus_2009-10.pdf": "Information Technology",
    "btech_it_y2_scheme-syllabus_2017-18.pdf": "Information Technology",
    "btech_it_y2_syllabus-rev_2014-15.pdf": "Information Technology",
    "btech_it_y4_syllabus-cbcs_2019-20.pdf": "Information Technology",
    "btech_it_y4_syllabus_2021-22.pdf": "Information Technology",
    "btech_me-ind-pe-ipe_y4_syllabus_2016-17.pdf": (
        "Mechanical Engineering;Production Engineering;"
        "Industrial & Production Engineering;"
        "Mechanical & Industrial Engineering"),
    "btech_me-ind_syllabus_2020-21.pdf": "Mechanical & Industrial Engineering",
}

SUBJECT_SCOPE = {
    "NPI-801": ("Production Engineering;Industrial & Production Engineering;"
                "Mechanical & Industrial Engineering"),
}


def first_ingestion_stem(cn):
    """the 'verbatim from <file>.pdf' of the FIRST 'First ingestion' segment"""
    seg = cn.split(";")[0] if cn else ""
    m = re.search(r"verbatim from (.+?\.pdf)", seg)
    return m.group(1) if m else None


def main():
    b27 = {}
    with open(B27, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            b27[r["subject_id"]] = r

    with open(CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    fieldnames = list(rows[0].keys())

    reverted = reapplied = 0
    for r in rows:
        notes = r.get("notes") or ""
        cn = r.get("change_note_vs_previous") or ""
        if "B28 post-commit repair" in notes or "B28 repair: branch_names" in cn:
            sid = r["subject_id"]
            if sid in b27:
                # pre-existing row: restore the B27-established scope verbatim
                r["branch_names"] = b27[sid].get("branch_names") or ""
                r["notes"] = notes.replace(
                    " | B28 post-commit repair: branch_names set from the document's "
                    "printed scope (printed cover scope; SCOPE-FROM-DOC recorded class — "
                    "the merge ran without DOC_SCOPE entries for the batch stems)", ""
                ).replace(
                    " | B28 post-commit repair: branch_names set from the document's printed "
                    "scope (printed cover scope; SCOPE-FROM-DOC recorded class — the merge "
                    "ran without DOC_SCOPE entries for the batch stems)", "")
                # generic strip: any ' | B28 post-commit repair: ...)' tail
                r["notes"] = re.sub(r" \| B28 post-commit repair: branch_names set from [^|]*?\)\s*$", "", r["notes"])
                r["change_note_vs_previous"] = re.sub(r"; B28 repair: branch_names recorded from the printed cover scope", "", cn)
                reverted += 1
                continue
            # genuine B28 append: keep the v1 scope but normalize via v2 logic below
        # reapply (corrected predicate) — also normalizes kept v1 rows
        stem = first_ingestion_stem(cn)
        if not stem or stem not in STEM_SCOPE:
            continue
        primary = (r.get("primary_code") or "").strip()
        scope = SUBJECT_SCOPE.get(primary, STEM_SCOPE[stem])
        if (r.get("branch_names") or "").strip() == scope:
            continue
        r["branch_names"] = scope
        if "B28 post-commit repair" not in (r.get("notes") or ""):
            r["notes"] = (r.get("notes") or "") + (
                " | B28 post-commit repair v2: branch_names set from the append-time "
                "document's printed scope (stem " + stem + "; SCOPE-FROM-DOC recorded "
                "class — the merge ran without DOC_SCOPE entries for the batch stems)")
        if "B28 repair: branch_names" not in (r.get("change_note_vs_previous") or ""):
            r["change_note_vs_previous"] = (r.get("change_note_vs_previous") or "") + \
                "; B28 repair: branch_names recorded from the printed cover scope"
        reapplied += 1

    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"REPAIR-v2|reverted {reverted} pre-existing rows to B27 scope; reapplied/normalized {reapplied} B28-append rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
