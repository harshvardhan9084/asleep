#!/usr/bin/env python3
"""patch_b16_verify_flags.py — add recorded evidence flags/remedies to B16
draft subjects so verify_draft.py's existing remedy classes can downgrade the
printed-design classes this batch hit (same classes as B15's recorded patch).

Evidence (all on disk, quirks carry page/print citations):

- A. assessment/practice slots whose printed description IS the complete
  content (B15 SEMINAR/RCE753 class, B04 N-era design): the doc prints a
  short prose description (report/viva/practice statement) and NO unit
  theory, NO experiments, NO CO table. Subjects:
    01 ECH651 Mass Transfer Lab-II / ECH654 Equipment Design / ECH752 Project /
       ECH851 Project (2009-10 N-era practice+project prints, desc_print held)
    04 KCH354 Mini Project/ Seminar (2019-20 K-era slot)
    05 Mini Project or Internship Assessment (codeless slot, KCH652-class) +
       KCH653 Technical Presentation
    06 RCH753 Industrial Training / RCH754 PROJECT-1 / RCH851 Seminar /
       RCH852 Project-2 (desc prints held; RCE753/754/851/852 B15 sibling
       class already recorded scheme-only)
  → flag `no_detailed_syllabus_printed` (verify "no_detailed" remedy).

- B. DE electives whose syllabus body is NOT printed in this doc (06 RCH074
  Environmental Impact Assessment p.10 blank body; RCH081 Fertilizer
  Technology p.16 blank body; RCH087 Petrochemical Technology p.22 blank
  body; RCH084 Biochemical Engg p.19-20 COURSE DETAIL table only; RCH085
  Novel Separation Process p.20-21 COURSE DETAIL table only — blank-body /
  detail-table quirks already in the draft) → `no_detailed_syllabus_printed`.

- C. draft-spec field normalization (zero content change): 08 English
  Language Lab prints a numbered "PRACTICALS" list which the subagent stored
  under the non-spec key `practicals` — items are already {"no", "exp"}
  shaped. Copied verbatim to `experiments` (RULES §7 field name) so the
  B02 lab remedy (experiments ⇒ no-units exempt) fires. Original key kept.

- D. prerequisite prints cited by GAP (v10 evidence-print class): the GAP
  codes are printed PRE-REQUISITE lines, not missing subjects:
    05 p.7 'PRE REQUISITES: KCH 301 (MEB), KCH 403 (CET)'; p.9+p.28
    'PRE-REQUISITE: KAS 302, KAS 402'; p.39 'PRE-REQUISITE: KCH 302, KCH
    303, KCH 501'  → non_subject_rows (kind=prerequisite_print)
    07 p.6 'PRE-REQUISITE: KCH 302, KCH303, KCH 402, KCH 501, KCH 503,
    KCH 603' (Plant Design and Economics) → non_subject_rows.
  The same prints already live in the subjects' prerequisites fields; the
  non_subject_rows copy is the verifier's evidence-print channel (RULES §11:
  non-subject rows stay out of the registry).

Idempotent: flags/quirks/rows only added when absent.
"""
import json, os

D = "/home/z/my-project/work/pipeline_v2/drafts"


def load(stem):
    return json.load(open(os.path.join(D, stem + ".draft.json")))


def save(stem, d):
    with open(os.path.join(D, stem + ".draft.json"), "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)


def add_flag(s, flag):
    if flag not in (s.get("flags") or []):
        s.setdefault("flags", []).append(flag)


def add_quirk(s, q):
    if q not in (s.get("quirks") or []):
        s.setdefault("quirks", []).append(q)


def match_name(s, names, codes=None):
    nm = s.get("name", "")
    if nm in names:
        return True
    if codes:
        return bool(set(s.get("codes") or []) & set(codes))
    return False


NO_DET = "no_detailed_syllabus_printed"
Q_A = ("patch-b16 evidence: printed description/practice statement is the "
       "complete syllabus content — no unit theory, experiments or CO table "
       "printed in this document (assessment/practice slot by print design; "
       "zero-guess forbids inventing units)")
Q_B = ("patch-b16 evidence: this doc does not print the elective's unit "
       "theory (blank syllabus body / COURSE DETAIL table only — see the "
       "recorded blank-body quirks with page cites; sibling-era docs of the "
       "same elective family supply the detail)")


def patch_a(stem, names_codes, extra_quirk=None):
    d = load(stem)
    n = 0
    for s in d["subjects"]:
        if match_name(s, names_codes[0], names_codes[1]):
            add_flag(s, NO_DET)
            add_quirk(s, extra_quirk or Q_A)
            n += 1
    save(stem, d)
    print(f"patch-a|{stem}|flagged {n}")


def patch_c(stem, names):
    d = load(stem)
    n = 0
    for s in d["subjects"]:
        nm = s.get("name", "").lower()
        if any(t in nm for t in names):
            prac = s.get("practicals") or []
            if prac and not s.get("experiments"):
                s["experiments"] = prac
                add_quirk(s, ("patch-b16: numbered PRACTICALS list copied "
                              "verbatim to the RULES §7 `experiments` field "
                              "(subagent stored it under the non-spec key "
                              "`practicals`; same items, zero content change)"))
                n += 1
    save(stem, d)
    print(f"patch-c|{stem}|normalized {n}")


def patch_d(stem, rows):
    d = load(stem)
    have = {(r.get("kind"), r.get("print")) for r in d.get("non_subject_rows", [])}
    n = 0
    for kind, print_txt, locator in rows:
        if (kind, print_txt) not in have:
            d.setdefault("non_subject_rows", []).append(
                {"kind": kind, "print": print_txt, "locator": locator})
            n += 1
    save(stem, d)
    print(f"patch-d|{stem}|added {n} evidence rows")


def main():
    # A: description-is-complete-content slots
    patch_a("01_btech_che_y2-4_syllabus_2009-10",
            (["MASS TRANSFER LAB-II", "EQUIPMENT DESIGN", "PROJECT"], ["ECH651", "ECH654", "ECH752", "ECH851"]))
    patch_a("04_btech_che_y2_syllabus_2019-20",
            (["Mini Project/ Seminar"], ["KCH354"]))
    patch_a("05_btech_che_y3_syllabus_2020-21",
            (["Mini Project or Internship Assessment", "Technical Presentation"], ["KCH653"]))
    patch_a("06_btech_che_y4_syllabus_2019-20",
            (["Industrial Training", "PROJECT – 1", "Seminar", "Project-2"],
             ["RCH753", "RCH754", "RCH851", "RCH852"]))
    # B: DE electives with no unit theory printed in this doc
    d6 = load("06_btech_che_y4_syllabus_2019-20")
    n = 0
    for s in d6["subjects"]:
        if set(s.get("codes") or []) & {"RCH074", "RCH081", "RCH084", "RCH085", "RCH087"}:
            add_flag(s, NO_DET)
            add_quirk(s, Q_B)
            n += 1
    save("06_btech_che_y4_syllabus_2019-20", d6)
    print(f"patch-b|06|flagged {n}")
    # C: practicals → experiments field normalization
    patch_c("08_btech_common-ex-ag-bt_y1_syllabus_2022-23", ["english language lab"])
    # D: prerequisite evidence prints
    patch_d("05_btech_che_y3_syllabus_2020-21", [
        ("prerequisite_print", "PRE REQUISITES:  KCH 301 (MEB),   KCH 403 (CET)", "p.7"),
        ("prerequisite_print", "PRE-REQUISITE: KAS 302, KAS 402", "p.9"),
        ("prerequisite_print", "PRE-REQUISITE: KAS 302, KAS 402", "p.28"),
        ("prerequisite_print", "PRE-REQUISITE: KCH 302, KCH 303, KCH 501", "p.39"),
    ])
    patch_d("07_btech_che_y4_syllabus_2021-22", [
        ("prerequisite_print", "PRE-REQUISITE: KCH 302, KCH303, KCH 402, KCH 501, KCH 503, KCH 603", "p.6"),
    ])
    print("PATCH_B16_DONE")


if __name__ == "__main__":
    main()
