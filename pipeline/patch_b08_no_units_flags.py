#!/usr/bin/env python3
"""patch_b08_no_units_flags.py — B08 verify remediation (B02 patch precedent).

verify_draft.py hard-fails subjects with no units unless they carry
experiments or a scheme-only flag. B08's failing subjects are two
evidence-verified print classes where zero-guess forbids inventing units:

1. SCHEME-ONLY rows (flag `scheme_row_only_no_detailed_syllabus`, the exact
   string the verifier already recognizes — used by draft 02's subagent):
   fulltext evidence — each code appears EXACTLY ONCE, inside the printed
   scheme table line, with no Unit/CO/book content anywhere:
     01: GP-101, GP201 (G.P. rows in 2008-09 scheme tables)
     06: BNC501/502, BNC601/602 (Constitution of India/EITK scheme rows), BCS554
     07: KCS751A (Departmental Elective Lab scheme row)
2. CO-ONLY project/assessment rows (new flag `co_only_no_units_printed`):
   printed CO table exists (all CO texts passed verifier containment vs the
   fulltext) but the document prints NO unit theory for these courses — the
   project/mini-project/internship-assessment print design. Requires a
   verifier v11 remedy: flag `co_only` + non-empty cos → WARN (downgrade).
     07: KCS354/KCS554/KCS752 Mini Project or Internship Assessment,
         KCS753/KCS851 Project (CO-only blocks p.22, subagent evidence)
     08: BCS752 / BCS753 / BCS851 (BCS753+BCS851 share one printed CO section)

Idempotent: flags only added when absent.
"""
import json, os, sys

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"

SCHEME_ONLY = {
    "01_btech_ag_y4_syllabus_2008-09": ["GP-101", "GP201"],
    "06_btech_ai-ds_y3_syllabus_2024-25": ["BNC501", "BNC502", "BNC601", "BNC602", "BCS554"],
    "07_btech_ai-ds_y4_syllabus_2024-25": ["KCS751A"],
}
CO_ONLY = {
    "07_btech_ai-ds_y4_syllabus_2024-25": ["KCS354", "KCS554", "KCS752", "KCS753", "KCS851"],
    "08_btech_ai-ds_y4_syllabus_2025-26": ["BCS752", "BCS753", "BCS851"],
}
FLAG_SCHEME = "scheme_row_only_no_detailed_syllabus"
FLAG_CO = "co_only_no_units_printed"


def patch(stem, needles, flag, note):
    path = os.path.join(DRAFTS, f"{stem}.draft.json")
    d = json.load(open(path))
    n = 0
    for s in d.get("subjects", []):
        codes = {str(c).upper().replace("-", "").replace(" ", "") for c in (s.get("codes") or [])}
        if any(str(x).upper().replace("-", "").replace(" ", "") in codes for x in needles):
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
    print(f"PATCHED|{stem}|{flag}|{n} subjects")


def main():
    note_scheme = ("PATCH-B08: fulltext evidence — code appears exactly once, inside the "
                   "printed scheme table line; no unit/CO/book content printed anywhere in "
                   "this document (zero-guess: units not invented).")
    note_co = ("PATCH-B08: printed CO table transcribed (CO texts containment-verified) but "
               "no unit theory is printed for this project/assessment course — the printed "
               "design; zero-guess forbids inventing units.")
    for stem, codes in SCHEME_ONLY.items():
        patch(stem, codes, FLAG_SCHEME, note_scheme)
    for stem, codes in CO_ONLY.items():
        patch(stem, codes, FLAG_CO, note_co)
    return 0


if __name__ == "__main__":
    sys.exit(main())
