#!/usr/bin/env python3
"""patch_b18_tie_strips.py — B18 TIE remediation (recorded B09 patch_b09_merge_fixes.py
precedent + RULES §6 page-image evidence).

Resolves the 4 dry-run TIE flags by removing the SECOND printed code from the
draft subject where the print itself is conflicted/joint, keeping the code whose
ownership is corroborated by the detailed-syllabus print:

1. docs 05/07/10 (2025-26 y4, Cyber-Security/CSE-DS/CSE-IoT) subject 'Project'
   prints 'BCS753/ BCS851 Project' — ONE shared CO table, TWO scheme rows
   (different semesters/credits). BCS753 is owned by project-1 (sem-VII slot)
   and BCS851 by project-ii (sem-VIII slot). Recorded B09 remedy: strip BCS851
   from the joint draft subject (project-ii already owns it); BCS753 then
   Tier-0-resolves UNIQUELY onto project-1. Print evidence preserved verbatim
   in the draft quirks + non_subject_rows.

2. doc 06 (2024-25 CSE-DS y3) subject 'Software Engineering Lab' carries
   BCS651+BCS652 (intra-doc print conflict). Page-image evidence (RULES §6,
   visible print authoritative):
     - p.41 detail heading prints 'BCS651 | SOFTWARE ENGINEERING LAB'
     - p.42 prints 'Software Engineering Lab (BCS651): Mapping with Virtual Lab'
     - p.3 scheme table row 6 prints 'BCS652 | Software Engineering Lab'
   The DETAILED-syllabus print (twice) + the sibling 2024-25 AIML print
   (published row software-engineering-lab owns BCS651) establish BCS651.
   BCS652 stays owned by compiler-design-lab (btech_ce-cst-cse_y3_syllabus_
   2024-25.pdf#3a7ea7b8a35eecac). Strip BCS652 from this draft subject; the
   scheme-table print is recorded as an intra-doc code-conflict quirk.

Idempotent: strips only when both codes are present.
"""
import json, os

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"

PROJECT_DOCS = [
    "05_btech_cse-cyber-security_y4_syllabus_2025-26",
    "07_btech_cse-ds_y4_syllabus_2025-26",
    "10_btech_cse-iot_y4_syllabus_2025-26",
]
NOTE_PROJECT = (
    "B18 TIE remedy (recorded B09 patch_b09_merge_fixes.py class): the document "
    "prints 'BCS753/ BCS851 Project' as ONE shared CO table over TWO scheme rows "
    "(BCS753 sem-VII slot, BCS851 sem-VIII slot). BCS851 stripped from this draft "
    "subject's codes because project-ii already owns BCS851 (published all_codes "
    "BCS851;BME851;RBT852;KBT851;BBT851;BCE851;BCH851;BCBS851) — keeping it would "
    "TIE the Tier-0 match across two rows and double-own the code (G2). BCS753 "
    "resolves uniquely onto project-1. Joint-print evidence preserved in the draft "
    "quirks/non_subject_rows; project-ii is corroborated by its own published 2025-26 "
    "sister-branch prints (B08).")


def norm(c):
    return str(c).upper().replace("-", "").replace(" ", "")


def strip(stem, subject_idx, keep, drop, note):
    path = os.path.join(DRAFTS, f"{stem}.draft.json")
    d = json.load(open(path))
    s = d["subjects"][subject_idx]
    codes = [norm(c) for c in (s.get("codes") or [])]
    if norm(drop) in codes and norm(keep) in codes:
        s["codes"] = [c for c in s["codes"] if norm(c) != norm(drop)]
        q = s.get("quirks") or []
        if note not in q:
            q.append(note)
        s["quirks"] = q
        with open(path, "w") as f:
            json.dump(d, f, indent=1, ensure_ascii=False)
        print(f"STRIP|{stem}::{subject_idx}|removed {drop}, kept {keep}|codes now {s['codes']}")
    else:
        print(f"SKIP|{stem}::{subject_idx}|codes {s.get('codes')}")


def main():
    for stem in PROJECT_DOCS:
        d = json.load(open(os.path.join(DRAFTS, f"{stem}.draft.json")))
        idx = next(i for i, s in enumerate(d["subjects"]) if s.get("name") == "Project")
        strip(stem, idx, "BCS753", "BCS851", NOTE_PROJECT)
    strip("06_btech_cse-ds_y3_syllabus_2024-25", 22, "BCS651", "BCS652",
          "B18 evidence (RULES §6 page-image, visible print authoritative): intra-doc "
          "code conflict — p.41 detail heading prints 'BCS651 | SOFTWARE ENGINEERING "
          "LAB' and p.42 prints 'Software Engineering Lab (BCS651): Mapping with "
          "Virtual Lab', while the p.3 scheme table row 6 prints 'BCS652 | Software "
          "Engineering Lab'. The detailed-syllabus print (x2) + the sibling 2024-25 "
          "AIML print (published software-engineering-lab row owns BCS651) establish "
          "BCS651; BCS652 stripped from this draft subject because compiler-design-lab "
          "owns BCS652 (btech_ce-cst-cse_y3_syllabus_2024-25.pdf#3a7ea7b8a35eecac) — "
          "keeping it would TIE the Tier-0 match and double-own the code (G2). The "
          "scheme-table print is preserved verbatim in non_subject_rows.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
