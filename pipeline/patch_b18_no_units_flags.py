#!/usr/bin/env python3
"""patch_b18_no_units_flags.py — B18 verify remediation (B02/B08 patch precedent).

verify_draft.py hard-fails subjects with no units unless they carry
experiments, a scheme-only flag, or the co_only flag with a printed CO table.
B18's failing subjects are two evidence-verified print classes where
zero-guess forbids inventing units:

1. CO-ONLY project/assessment rows (flag `co_only_no_units_printed`, the
   exact string the verifier's v11 remedy recognizes; requires non-empty cos):
   printed CO table exists (CO texts containment-checked vs fulltext) but the
   document prints NO unit theory — the printed design of project /
   mini-project / internship-assessment courses:
     03: BCS753 Project-1, BCS851 Project-II, BCS752 Mini Project or
         Internship Assessment (cos 5 each; BCS753+BCS851 share one printed
         CO page — subject-level flag already records the sharing)
     05/07/10: BCS753+BCS851 Project (one shared CO table), BCS752
2. SCHEME-ONLY rows (flag `scheme_row_only_no_detailed_syllabus`):
   code appears only inside the printed scheme table line, no unit/CO/book
   print anywhere (cos 0 in draft):
     06: BCS554 Mini Project or Internship Assessment*; BNC501/502/BNC601/602
         Constitution of India row; Open Elective-I (code-less pool placeholder)
     08: KCS554 Mini Project or Internship Assessment*; KNC501/502 and
         KNC601/602 Constitution of India rows

Idempotent: flags only added when absent. Name-based match used only for the
code-less Open Elective-I row.
"""
import json, os

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"

CO_ONLY = {
    "03_btech_cse-aiml_y4_syllabus_2025-26": ["BCS753", "BCS851", "BCS752"],
    "05_btech_cse-cyber-security_y4_syllabus_2025-26": ["BCS753", "BCS851", "BCS752"],
    "07_btech_cse-ds_y4_syllabus_2025-26": ["BCS753", "BCS851", "BCS752"],
    "10_btech_cse-iot_y4_syllabus_2025-26": ["BCS753", "BCS851", "BCS752"],
}
SCHEME_ONLY = {
    "06_btech_cse-ds_y3_syllabus_2024-25": ["BCS554", "BNC501", "BNC502", "BNC601", "BNC602"],
    "08_btech_cse-iot_y3_syllabus-rev_2022-23": ["KCS554", "KNC501", "KNC502", "KNC601", "KNC602"],
}
FLAG_CO = "co_only_no_units_printed"
FLAG_SCHEME = "scheme_row_only_no_detailed_syllabus"

NOTE_CO = ("B18 evidence: printed CO table (CO texts containment-verified vs parsed "
           "fulltext); the document prints NO unit theory for this project/mini-project/"
           "internship-assessment course — printed design, zero-guess forbids inventing "
           "units (B08 v11 remedy class).")
NOTE_SCHEME = ("B18 evidence: code appears only in the printed scheme table line; no "
               "unit/CO/book print anywhere in the document — scheme-row-only, zero-guess "
               "forbids inventing units (B02/B08 remedy class).")


def norm(c):
    return str(c).upper().replace("-", "").replace(" ", "")


def patch(stem, needles, flag, note, name_match=None):
    path = os.path.join(DRAFTS, f"{stem}.draft.json")
    d = json.load(open(path))
    n = 0
    for s in d.get("subjects", []):
        codes = {norm(c) for c in (s.get("codes") or [])}
        hit = any(norm(x) in codes for x in needles)
        if not hit and name_match and s.get("name", "").strip().lower() == name_match.lower():
            hit = True
        if not hit:
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
    print(f"PATCH|{stem}|{flag}|{n}")


def main():
    for stem, needles in CO_ONLY.items():
        patch(stem, needles, FLAG_CO, NOTE_CO)
    for stem, needles in SCHEME_ONLY.items():
        patch(stem, needles, FLAG_SCHEME, NOTE_SCHEME,
              name_match="Open Elective-I")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
