#!/usr/bin/env python3
"""patch_b19_verify_fixes.py — B19 verify remediation (B02/B08/B18 precedent).

First verify run: 6 PASS / 4 FAIL / 2 WARN. Every finding investigated to the
printed-evidence root cause (RULES §6: visible print authoritative):

1. doc 02 (2015-16) ORPHAN codes NHU501/NHU601/NGP501/NGP601/NCS654 — page-
   image proof pp.2-3: the printed Course-Code CELL wraps the token over two
   lines inside one cell ('NHU5'/'01', 'NHU'/'601', 'NGP'/'501', 'NGP'/'601',
   'NCS'/'654'), so the linear text layer can never contain the composed code.
   The composed codes ARE the visible print. Flag
   `code_cell_wrap_page_image_attested` + page-citing quirk → verifier v14
   downgrades these ORPHAN hits to WARN.

2. doc 05 (2009-10) no-units subjects EHU-301/302 (Industrial Psychology/
   Industrial Sociology), EHU-111 (Human Values & PE), EHU-401/402 (Industrial
   Sociology/Psychology), GP-301, GP-401 — the codes print ONLY inside the
   scheme-table lines (1 occurrence each; EHU-111 twice = printed in both
   semester schemes, matching the draft's recorded flag). No detailed
   syllabus anywhere. Flag `scheme_row_only_no_detailed_syllabus` (B02/B18
   class).

3. doc 08 (2024-25 Hindi) no-units subjects BCS554H (Mini Project or
   Internship Assessment*), BNC501H/502H + BNC601H/602H (Constitution of
   India/ Essence of Indian Traditional Knowledge) — same evidence: 1
   scheme-table occurrence each, no detail pages. Flag `scheme_row_only_
   no_detailed_syllabus` (B18 class).

4. doc 09 (2018-19) no-units labs RCS-551 (DBMS Lab), RCS-552 (DAA Lab),
   RCS-553 (PPL Lab) — the detailed page prints an 'Objectives :' list only
   (11/10/9 verbatim items, containment-checked) and NO unit theory and NO
   experiment list anywhere: the printed design of these lab prints. The
   lists stay transcribed verbatim under objectives_print (zero-guess: the
   print labels them Objectives — NOT reclassified as experiments). Flag
   `objectives_only_no_units_printed` → verifier v14 downgrade.

5. doc 01 WARN: Electrical Engineering Lab (AEE151A) experiment 'Three-Phase
   Power Measurement – Two-Wattmeter Method' splits across the PAGE JUNCTION
   pp.66-67 (text layer: '...Two-' ends p.66, 'Wattmeter Method' opens p.67).
   The composed title is the visible print (B01/B02 junction class). Evidence
   quirk recorded; WARN adjudicated.

6. doc 06 WARN: Operating Systems (KCS401H) book 4 'D M Dhamdhere, "Operating
   Systems : A Concept based Approach", 2nd Edition,' — the publisher 'TMH'
   wraps to the next text-layer line and visually merges with reference 5's
   numbering ('TMH 5. William Stallings'). Documented split/interleave print
   class (B01 Mowbray / B02 Dhamdhere). Evidence quirk recorded; WARN
   adjudicated.

Idempotent: flags/quirks only added when absent.
"""
import json, os

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"

FLAG_WRAP = "code_cell_wrap_page_image_attested"
FLAG_SCHEME = "scheme_row_only_no_detailed_syllabus"
FLAG_OBJ = "objectives_only_no_units_printed"

NOTE_WRAP = ("B19 evidence: page-image proof pp.2-3 — the printed Course-Code cell wraps "
             "the token over two lines inside one cell (NHU5/01, NHU/601, NGP/501, NGP/601, "
             "NCS/654 stacked); the composed code is the visible print (RULES §6), the "
             "linear text layer cannot contain it (verifier v14 downgrade).")
NOTE_SCHEME = ("B19 evidence: the codes print ONLY inside the scheme-table lines (1 "
               "occurrence each in the parsed fulltext); no detailed syllabus anywhere in "
               "the document — scheme-row-only, zero-guess forbids inventing units "
               "(B02/B18 remedy class).")
NOTE_SCHEME_111 = ("B19 evidence: EHU-111 prints only inside scheme-table lines, TWICE "
                   "(once per semester scheme — the printed double-listing the draft flag "
                   "records); no detailed syllabus anywhere (B02/B18 remedy class).")
NOTE_OBJ = ("B19 evidence: the lab's detailed page prints an 'Objectives :' list only "
            "(items transcribed verbatim under objectives_print, containment-checked); NO "
            "unit theory and NO experiment list anywhere in the document — printed design; "
            "the print labels them Objectives so they are NOT reclassified as experiments "
            "(verifier v14 downgrade).")
NOTE_JUNCTION = ("B19 evidence: experiment title 'Three-Phase Power Measurement – Two-"
                 "Wattmeter Method' splits across the page junction pp.66-67 ('...Two-' "
                 "ends p.66, 'Wattmeter Method' opens p.67 in the text layer); the "
                 "composed title is the visible print (B01/B02 page-break-junction class).")
NOTE_BOOKWRAP = ("B19 evidence: book 4 publisher 'TMH' wraps to the next text-layer line "
                 "and visually merges with reference 5's numbering ('TMH 5. William "
                 "Stallings') — line-wrap/split print class (B01 Mowbray / B02 Dhamdhere); "
                 "the draft string is the visible print.")


def norm(c):
    return str(c).upper().replace("-", "").replace(" ", "")


def patch_by_codes(stem, needles, flag, note):
    path = os.path.join(DRAFTS, f"{stem}.draft.json")
    d = json.load(open(path))
    n = 0
    for s in d.get("subjects", []):
        codes = {norm(c) for c in (s.get("codes") or [])}
        if not any(norm(x) in codes for x in needles):
            continue
        fl = s.get("flags") or []
        if not any(flag in str(f) for f in fl):
            fl.append(flag)
            s["flags"] = fl
        q = s.get("quirks") or []
        if note not in q:
            q.append(note)
        s["quirks"] = q
        n += 1
    with open(path, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    print(f"PATCH|{stem}|by-codes|{flag}|{n}")


def patch_by_name(stem, name_exact, note):
    path = os.path.join(DRAFTS, f"{stem}.draft.json")
    d = json.load(open(path))
    n = 0
    for s in d.get("subjects", []):
        if s.get("name", "").strip().lower() != name_exact.lower():
            continue
        q = s.get("quirks") or []
        if note not in q:
            q.append(note)
        s["quirks"] = q
        n += 1
    with open(path, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    print(f"PATCH|{stem}|by-name|{name_exact}|{n}")


def main():
    # 1. doc 02 wrapped code cells (pp.2-3 image proof)
    patch_by_codes("02_btech_cse_syllabus_2015-16",
                   ["NHU501", "NHU601", "NGP501", "NGP601", "NCS654"],
                   FLAG_WRAP, NOTE_WRAP)
    # 2. doc 05 scheme-only rows (EHU/GP)
    patch_by_codes("05_btech_cse_y2_scheme-syllabus_2009-10",
                   ["EHU-301", "EHU-302", "EHU-111", "EHU-401", "EHU-402", "GP-301", "GP-401"],
                   FLAG_SCHEME, NOTE_SCHEME)
    # EHU-111 gets its own double-listing evidence note (2 occurrences)
    patch_by_codes("05_btech_cse_y2_scheme-syllabus_2009-10",
                   ["EHU-111"], FLAG_SCHEME, NOTE_SCHEME_111)
    # 3. doc 08 scheme-only rows (Mini Project + Constitution x2)
    patch_by_codes("08_btech_cse_y3_syllabus-hindi_2024-25",
                   ["BCS554H", "BNC501H", "BNC502H", "BNC601H", "BNC602H"],
                   FLAG_SCHEME, NOTE_SCHEME)
    # 4. doc 09 objectives-only labs
    patch_by_codes("09_btech_cse_y3_syllabus_2018-19",
                   ["RCS-551", "RCS-552", "RCS-553"],
                   FLAG_OBJ, NOTE_OBJ)
    # 5. doc 01 page-junction experiment title (WARN adjudication)
    patch_by_name("01_btech_cse_course-structure_2026-27",
                  "Electrical Engineering Lab", NOTE_JUNCTION)
    # 6. doc 06 Dhamdhere publisher line-wrap (WARN adjudication)
    patch_by_name("06_btech_cse_y2_syllabus-hindi-rev_2022-23",
                  "Operating Systems", NOTE_BOOKWRAP)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
