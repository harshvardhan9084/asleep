#!/usr/bin/env python3
"""patch_b17_verify_flags.py — evidence patches for the B17 verify hard-fails,
per the recorded patch-time flag classes (B16 precedent: patch_b16_verify_flags.py).

Class A (B15/B16 SEMINAR/assessment-slot class): project / mini-project /
internship / startup-assessment / non-credit scheme subjects print NO unit
theory anywhere — the printed design of these slots. Subjects with a printed
CO table get flag `co_only_no_units_printed` (v11/B08 remedy: downgraded to
WARN when cos are present); pure scheme-row subjects get flag
`no_detailed_syllabus_printed` (B16 class A remedy). Zero-guess: no units
invented; every patched subject's quirk already cites the page evidence
(p.2 scheme row, p.9 CO table, or 'no detailed syllabus ... printed').

Class B (RULES §6 dropped-fragment class, page-image verified): draft 01
KAS203T Engineering Mathematics-II Unit-V — the PRINT (p.11, verified on
300/600-dpi page renders) shows THREE real-integral types:
  integral_0^{2*pi} f(cosθ, sinθ) dθ ,  integral_0^{pi} f(cosθ, sinθ) dθ
  and  integral_{-pi}^{pi} f(cosθ, sinθ) dθ  only.
The PyMuPDF text layer carries only TWO scrambled glyph runs (the
integral_0^{2*pi} run is dropped entirely, the integral_{-pi}^{pi} run's
glyph order is scrambled: '∫− π π θ θ θ d f ) sin , (cos'). The draft had
transcribed from the text layer (2 integrals + an inline editorial note).
Fix: transcribe the VISIBLE PRINT (three integrals, draft's existing
ASCII-bound convention), move the editorial note into quirks, and flag
`unit_table_interleave_print` (v12/B10 class: text layer scrambles/reorders
printed fragments so linear containment is structurally impossible) with a
page-citing quirk — containment problems downgrade to WARN with flag cited.

Idempotent: flags appended only when absent.
"""
import json, os, sys

D = "/home/z/my-project/work/pipeline_v2/drafts"

CO_ONLY = "co_only_no_units_printed"
NO_DET = "no_detailed_syllabus_printed"


def patch(fname, name_pred, add_flag, extra_quirk=None, unit_fix=None):
    path = os.path.join(D, fname)
    d = json.load(open(path))
    n = 0
    for s in d.get("subjects", []):
        if not name_pred(s):
            continue
        flags = s.setdefault("flags", [])
        if add_flag and add_flag not in [str(f) for f in flags]:
            flags.append(add_flag)
        if extra_quirk:
            q = s.setdefault("quirks", [])
            if extra_quirk not in [str(x) for x in q]:
                q.append(extra_quirk)
        if unit_fix:
            unit_fix(s)
        n += 1
    if n:
        with open(path, "w") as f:
            json.dump(d, f, indent=1, ensure_ascii=False)
    print(f"PATCHED|{fname}|{n} subject(s) <- {add_flag}")


def main():
    # ---- Class A: CO-only assessment slots (printed CO table, no unit theory)
    patch("05_btech_csbs_y4_syllabus_2025-26.draft.json",
          lambda s: s.get("name") in ("Mini Project or Internship Assessment",
                                      "Project-1", "Project-II"),
          CO_ONLY,
          "VERIFY-PATCH-B17: no unit theory printed anywhere in this doc for this "
          "subject (scheme row p.2 + CO table p.9 only) — printed design of the "
          "project/assessment slot; flag co_only_no_units_printed per recorded "
          "v11/B08 class. Zero-guess: no units invented.")
    patch("07_btech_csd_y4_syllabus_2024-25.draft.json",
          lambda s: s.get("name") in ("Mini Project or Internship Assessment",
                                      "Project"),
          CO_ONLY,
          "VERIFY-PATCH-B17: no unit theory printed anywhere in this doc for this "
          "subject (CO table only) — printed design of the project/assessment "
          "slot; flag co_only_no_units_printed per recorded v11/B08 class.")
    patch("08_btech_csd_y4_syllabus_2025-26.draft.json",
          lambda s: s.get("name") in ("Mini Project or Internship Assessment",
                                      "Project-I", "Project-II"),
          CO_ONLY,
          "VERIFY-PATCH-B17: no unit theory printed anywhere in this doc for this "
          "subject (scheme row p.2 + shared CO table p.9 only) — printed design "
          "of the project/assessment slot; flag co_only_no_units_printed per "
          "recorded v11/B08 class.")
    patch("10_btech_cse-ai_y4_syllabus_2025-26.draft.json",
          lambda s: s.get("name") in ("Project-1", "Project-II",
                                      "Mini Project or Internship Assessment"),
          CO_ONLY,
          "VERIFY-PATCH-B17: no unit theory printed anywhere in this doc for this "
          "subject (CO table p.9 / scheme row p.2 only) — printed design of the "
          "project/assessment slot; flag co_only_no_units_printed per recorded "
          "v11/B08 class.")

    # ---- Class A: pure scheme-row subjects (no CO table either)
    patch("06_btech_csd_y3_syllabus_2024-25.draft.json",
          lambda s: str(s.get("name", "")).startswith("Mini Project or Internship"),
          NO_DET,
          "VERIFY-PATCH-B17: subject appears only in the Semester-V scheme row "
          "(p.2) + summer-internship footnote — no detailed syllabus printed; "
          "flag no_detailed_syllabus_printed per recorded B16 class A.")
    patch("06_btech_csd_y3_syllabus_2024-25.draft.json",
          lambda s: str(s.get("name", "")).startswith("Constitution of India/"),
          NO_DET,
          "VERIFY-PATCH-B17: combined BNC scheme row prints no detailed syllabus, "
          "COs, units or books in this PDF (scheme row only, marks/credit cells "
          "blank as printed) — flag no_detailed_syllabus_printed per recorded B16 "
          "class A; needs_review (combined alternative-subjects row) carried for "
          "merge-time adjudication.")
    patch("10_btech_cse-ai_y4_syllabus_2025-26.draft.json",
          lambda s: str(s.get("name", "")).startswith("Startup and Entrepreneurial"),
          NO_DET,
          "VERIFY-PATCH-B17: scheme-row-only subject (p.2 row + '#' footnote); no "
          "CO table, no units printed — flag no_detailed_syllabus_printed per "
          "recorded B16 class A.")

    # ---- Class B: draft 01 KAS203T Unit-V — visible print (p.11) is three
    # integrals; text layer drops/scrambles. Transcribe print, flag interleave.
    def fix_unit5(s):
        u = s.get("units") or {}
        u5 = u.get("5")
        if not u5 or "text-layer artifact" not in u5:
            return
        new5 = u5.split("[text-layer artifact:")[0].strip()
        if "∫0^2π" not in new5:
            new5 = new5.replace(
                "Evaluation of real integrals of the types  ∫0^π f(cosθ, sinθ) dθ "
                "and ∫−π^π f(cosθ, sinθ) dθ only.",
                "Evaluation of real integrals of the types  ∫0^2π f(cosθ, sinθ) dθ , "
                "∫0^π f(cosθ, sinθ)dθ and ∫−π^π f(cosθ, sinθ)dθ only.")
        u["5"] = new5
        s["units"] = u

    def mat2_pred(s):
        return "Mathematics-II" in str(s.get("name", "")) and "KAS203T" in [c.replace(" ", "") for c in (s.get("codes") or [])]

    path = os.path.join(D, "01_btech_common_y1_model-curriculum_2020-21.draft.json")
    d = json.load(open(path))
    hit = 0
    for s in d.get("subjects", []):
        if mat2_pred(s):
            hit += 1
            fix_unit5(s)
            flags = s.setdefault("flags", [])
            if "unit_table_interleave_print" not in [str(f) for f in flags]:
                flags.append("unit_table_interleave_print")
            q = s.setdefault("quirks", [])
            ev = ("VERIFY-PATCH-B17 p.11 (page-image evidence, RULES §6): the PRINT "
                  "shows THREE real-integral types — ∫0^2π f(cosθ, sinθ) dθ , "
                  "∫0^π f(cosθ, sinθ)dθ and ∫−π^π f(cosθ, sinθ)dθ only — but the "
                  "PyMuPDF text layer carries only TWO scrambled glyph runs (the "
                  "∫0^2π run is dropped entirely; the ∫−π^π run prints glyph-"
                  "scrambled as '∫− π π θ θ θ d f ) sin , (cos'). Transcribed from "
                  "300/600-dpi renders of p.11; flag unit_table_interleave_print "
                  "per recorded v12/B10 class (structural text-layer reorder).")
            if ev not in [str(x) for x in q]:
                q.append(ev)
    if hit:
        with open(path, "w") as f:
            json.dump(d, f, indent=1, ensure_ascii=False)
    print(f"PATCHED|01...20-21.draft.json|{hit} subject(s) <- unit_table_interleave_print + print-faithful unit5")

    return 0


if __name__ == "__main__":
    sys.exit(main())
