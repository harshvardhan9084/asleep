#!/usr/bin/env python3
"""patch_b11_verify_fixes.py — CRON-20261031-B11 verify-remedy patches.

Evidence-recorded draft patches after verify_draft.py first run (B09/B10
precedent: every downgrade carries its computed fulltext / page-image
evidence).

doc02 (btech_bme_y4_syllabus-cbcs_2019-20, sha16 5ebb94b097938308):
  (a) 5 subjects print their units on SCANNED pages with an EMPTY text layer
      (parsed json text_len: p4=52, p8=58, p16=89, p17=101, p19=120 chars —
      header line only). Units were recovered from the page images (RULES §6,
      visible print authoritative). Page-image spot-checks by the orchestrator
      (Read tool, pages 4/8/16/17-19) confirmed the transcriptions faithful:
      RBM701 (p4: 'Harmrd'/'ANLYSIS' verbatim print typos), RBM071 (p8:
      'Polymeric chain reaction' verbatim), RBM083 (p16: 'acceptancecalibrat-
      ion'/'Chistrmis' run-on verbatim), RBM084 (p17: 'Softwre', UNIT-II
      headingless), RBM086 (p19: Fuzzy/ART units + 4-book list). Flag
      `unit_ocr_recovered_no_text_layer` added per v12 remedy (B10 class);
      existing page-citing quirks kept.
  (b) REC753/REC754/REC851/REC852 (Industrial Training Viva-Voce / Project-I /
      GD &Seminar / Project): each code occurs EXACTLY ONCE in the fulltext —
      in the semester scheme table only; no syllabus page, units, COs or books
      printed anywhere (B02/B08/B10 scheme-row precedent). Flag
      `scheme_row_only_no_detailed_syllabus` added beside the existing
      `syllabus-not-printed`.
  (c) Open Elective-I**/II**: no code, no pool list, no syllabus printed
      anywhere in the doc (quirk: 'Other/Dept.' column). Flags
      `no-code-printed-open-elective-pool-not-in-doc` (v10 no-code remedy
      class) + `scheme_row_only_no_detailed_syllabus` added.

doc07 (btech_bt_syllabus_2015-16): NHU-501 Engineering Economics, NGP-501 GP,
  NHU-601 Industrial Management, NBT-654 Seminar, NGP-601 GP — each code occurs
  EXACTLY ONCE in the fulltext, in the scheme table row only (evidence strings
  recorded in the script run log); no detailed syllabus printed. Flag
  `scheme_row_only_no_detailed_syllabus` + evidence quirk added.

doc08 (btech_bt_syllabus_2016-17): NBT752 Industrial Training, NBT753 Project,
  NBT851 Seminar, NBT852 Project — same single-occurrence scheme-row evidence.
  Flag + evidence quirk added.

doc09 (btech_bt_syllabus_2018-19): RAS501 Managerial Economics, RAS502/RUC501
  'Sociology/ Cyber Security', RAS601 Industrial Management, RUC601/RAS602
  'Cyber Security/ Sociology' — each code occurs EXACTLY ONCE, scheme table
  only (dual-slot applied-science prints). Flag + evidence quirk added.

Idempotent: flags/quirks only added when absent.
"""
import json, os, sys

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"

OCR_FLAG = "unit_ocr_recovered_no_text_layer"
SCHEME_FLAG = "scheme_row_only_no_detailed_syllabus"
NOCODE_FLAG = "no-code-printed-open-elective-pool-not-in-doc"

OCR_SUBJECTS_02 = [
    "Biomedical Image Processing",
    "Bioinformatics",
    "Principles of Radio Diagnosis and Radio Therapy",
    "Design and Modelling of Biomedical Systems",
    "Artificial Intelligence & its Applications in Biomedical Engineering",
]


def add_flag(sub, flag):
    fl = sub.get("flags") or []
    if flag not in fl:
        fl.append(flag)
        sub["flags"] = fl
        return True
    return False


def add_quirk(sub, quirk):
    qs = sub.get("quirks") or []
    if not any(q[:40] == quirk[:40] for q in qs):
        qs.append(quirk)
        sub["quirks"] = qs
        return True
    return False


def patch(stem, mutations):
    path = os.path.join(DRAFTS, f"{stem}.draft.json")
    d = json.load(open(path))
    n = 0
    for pred, flag, quirk in mutations:
        for s in d.get("subjects", []):
            if pred(s):
                if flag and add_flag(s, flag):
                    n += 1
                if quirk and add_quirk(s, quirk):
                    n += 1
    with open(path, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    print(f"PATCHED|{stem}|{n} mutations")
    return n


def main():
    total = 0
    # doc02 (a): OCR-recovered units — page-image spot-checks 4/8/16/17/19 done
    total += patch("02_btech_bme_y4_syllabus-cbcs_2019-20", [
        (lambda s: s.get("name") in OCR_SUBJECTS_02, OCR_FLAG,
         "patch-b11: units transcribed from scanned page with empty text layer "
         "(page-image spot-check by orchestrator confirmed faithful print; "
         "RULES §6 visible print authoritative)."),
    ])
    # doc02 (b): scheme-row-only assessment subjects (single fulltext occurrence)
    total += patch("02_btech_bme_y4_syllabus-cbcs_2019-20", [
        (lambda s: (s.get("codes") or [""])[0] in ("REC753", "REC754", "REC851", "REC852"),
         SCHEME_FLAG,
         "patch-b11: scheme-row subject only — code occurs exactly once in the "
         "fulltext (semester scheme table); no syllabus page/units/COs printed."),
    ])
    # doc02 (c): open-elective pool slots — no code/pool/syllabus printed
    total += patch("02_btech_bme_y4_syllabus-cbcs_2019-20", [
        (lambda s: str(s.get("name", "")).startswith("Open Elective-"),
         NOCODE_FLAG,
         "patch-b11: open-elective slot prints no code and no pool list in this "
         "doc ('Other/Dept.' column); scheme-row only."),
        (lambda s: str(s.get("name", "")).startswith("Open Elective-"),
         SCHEME_FLAG, None),
    ])
    # doc07: 5 scheme-row-only subjects (single fulltext occurrence each)
    total += patch("07_btech_bt_syllabus_2015-16", [
        (lambda s: (s.get("codes") or [""])[0] in ("NHU-501", "NGP-501", "NHU-601",
                                                   "NBT-654", "NGP-601"),
         SCHEME_FLAG,
         "patch-b11: scheme-row subject only — code occurs exactly once in the "
         "fulltext (scheme table); no detailed syllabus printed in this doc."),
    ])
    # doc08: 4 scheme-row-only subjects (single fulltext occurrence each)
    total += patch("08_btech_bt_syllabus_2016-17", [
        (lambda s: (s.get("codes") or [""])[0] in ("NBT752", "NBT753", "NBT851", "NBT852"),
         SCHEME_FLAG,
         "patch-b11: scheme-row subject only — code occurs exactly once in the "
         "fulltext (scheme table); no detailed syllabus printed in this doc."),
    ])
    # doc09: 4 scheme-row-only subjects incl. 2 dual-slot applied-science prints
    total += patch("09_btech_bt_syllabus_2018-19", [
        (lambda s: any(c in ("RAS501", "RAS502", "RUC501", "RAS601", "RUC601", "RAS602")
                       for c in (s.get("codes") or [])),
         SCHEME_FLAG,
         "patch-b11: scheme-row subject only — code occurs exactly once in the "
         "fulltext (scheme table; dual-slot applied-science print for the "
         "slash-named rows); no detailed syllabus printed in this doc."),
    ])
    print(f"PATCH_TOTAL|{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
