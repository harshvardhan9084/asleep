#!/usr/bin/env python3
"""patch_b14_verify_fixes.py — B14 verify remedies (RULES §6/§7, zero-guess,
evidence-recorded; B12/B13 patch-script pattern).

Two hard FAILs, each investigated to a root-cause class:

(a) doc04 (btech_ce_syllabus_2010-11) ECE504 STRUCTURAL ANALYSIS II:
    "unit4 containment 0.00".
    ROOT CAUSE: the printed per-unit lecture-count column ("8") sits on its
    OWN LINE in the text layer (count-column interleave, the exact furniture
    class verify_draft.py's strip_furniture_deep removes from the haystack);
    the draft's unit4 tail carries that "8", making the needle
    "…matrixmethodsforbeamsframestrusses8" (66 chars <= the 70-char whole-
    needle shortcut) unmatchable against the stripped haystack -> cov 0.00.
    The subject's longer units (1/2/3/5) pass via window coverage because the
    1-char tail is <15% of the needle.
    REMEDY (B04-repair lecture-count precedent, 66 unit-text normalizations;
    strip_furniture_deep design intent): strip the trailing standalone count
    digit from ECE504's unit texts — the count is the printed lectures-per-
    unit column, already recorded in lectures_per_unit=8 — and add a quirk
    citing the evidence. Prose itself unchanged.

(b) doc05 (btech_ce_syllabus_2015-16): "GAP codes on scheme-like lines not in
    draft: ESE100".
    ROOT CAUSE: every detailed-subject header prints the marks-column header
    "CT–30, TA–20, ESE -100"; the scheme-line regex extracts "ESE100" from
    "ESE -100". It is the END-SEMESTER-EXAM MARKS column (100 marks), not a
    course code — zero-guess forbids drafting it as a subject.
    REMEDY (v10 remedy class, B06 evidence: "a pool/slot code recorded as
    printed non-subject evidence is not a missing subject"): append a
    non_subject_row to the draft carrying the verbatim printed marks header —
    it then flows through the verifier's non_subject_rows exemption
    (c.lower() in content_corpus).

Benign WARN adjudicated, no patch: doc02 "book not found: Hunter Rouse,
Elementary Mechanics of F…" — truncated/split book-title print class
(B02/B06/B07 recorded classes; title split across printed lines).

Idempotent: patches only when the target state is absent.
"""
import json, re, sys

D04 = "/home/z/my-project/work/pipeline_v2/drafts/04_btech_ce_syllabus_2010-11.draft.json"
D05 = "/home/z/my-project/work/pipeline_v2/drafts/05_btech_ce_syllabus_2015-16.draft.json"

QUIRK_A = ("patch-b14: printed per-unit lecture-count column ('8') sits on its own text-"
           "layer line and interleaved into the unit-prose tail; count is the printed "
           "lectures-per-unit column (lectures_per_unit=8), stripped from unit prose per "
           "the B04-repair lecture-count normalization precedent / "
           "strip_furniture_deep furniture class; prose unchanged")

NSNR_B = {
    "kind": "marks_header_print",
    "print": "CT–30, TA–20, ESE -100",
    "locator": ("printed on every detailed-subject header line of the 2015-16 Civil "
                "syllabus (e.g. above NCE-501..NCE-024 pages) — 'ESE -100' is the "
                "End-Semester-Exam MARKS column (100 marks), not a course code; "
                "patch-b14 evidence for the verifier GAP exemption (v10 class)"),
}


def main():
    n_a = 0
    d4 = json.load(open(D04))
    for s in d4["subjects"]:
        if s.get("codes") == ["ECE504"]:
            units = s.get("units") or {}
            for uk, ut in list(units.items()):
                m = re.search(r"\s(\d{1,2})\s*$", ut or "")
                if m and int(m.group(1)) == int(s.get("lectures_per_unit", -1)):
                    units[uk] = re.sub(r"\s\d{1,2}\s*$", "", ut)
                    n_a += 1
            if QUIRK_A not in (s.get("quirks") or []):
                s.setdefault("quirks", []).append(QUIRK_A)
    if n_a:
        with open(D04, "w") as f:
            json.dump(d4, f, ensure_ascii=False, indent=1)
    print(f"PATCH_A|doc04 ECE504 units normalized: {n_a}")

    d5 = json.load(open(D05))
    have = any(r.get("kind") == "marks_header_print" for r in d5.get("non_subject_rows", []))
    if not have:
        d5.setdefault("non_subject_rows", []).append(NSNR_B)
        with open(D05, "w") as f:
            json.dump(d5, f, ensure_ascii=False, indent=1)
    print(f"PATCH_B|doc05 marks-header nsnr appended: {not have}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
