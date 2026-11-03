#!/usr/bin/env python3
"""patch_b16_tie_alt_pair.py — evidence flag for the B16 TIE on
01::01::mathematics-iii (EAS 301/EAS 401 dual print).

Print evidence (2009-10 doc p.2 scheme table, verbatim):
  Sem-III: '2 EAS301/ EOE031-EOE038 | Mathematics III/Science Based Open Elective**'
  Sem-IV : '2 EOE041-EOE048/ EAS401 | Science Based Open Elective/ Mathematics III'
  Detail heading: 'EAS 301/EAS 401: MATHEMATICS –III'

The doc prints the Mathematics-III / Science-Based-Open-Elective ALTERNATIVE
PAIR as one dual-code subject (B01 recorded ALTERNATIVE-PAIR-SLOT class: a
slot is program structure, not a subject). Both printed codes are already
owned by the registry's slot rows (EAS401 = primary of
science-based-open-elective-mathematics-iii; EAS-301 in all_codes of
mathematics-iii-science-based-open-elective) — the draft adds NO new code.
The 'alternative_pair' flag routes the ladder TIE to the recorded
ALTERNATIVE-PAIR-SLOT SKIP (RESOLVE_APPEND), preserving zero-guess and G2
one-owner. The scheme rows stay in the draft's non_subject_rows.
Idempotent.
"""
import json

P = "/home/z/my-project/work/pipeline_v2/drafts/01_btech_che_y2-4_syllabus_2009-10.draft.json"
FLAG = "alternative_pair_row_dual_code_slot_print"
Q = ("patch-b16 evidence: scheme table (p.2) prints this subject as the "
     "Mathematics-III / Science-Based-Open-Elective ALTERNATIVE PAIR "
     "('EAS301/ EOE031-EOE038 | Mathematics III/Science Based Open Elective' "
     "sem-III; 'EOE041-EOE048/ EAS401 | Science Based Open Elective/"
     "Mathematics III' sem-IV) with dual detail heading 'EAS 301/EAS 401'; "
     "both codes are already owned by the registry's slot rows "
     "(science-based-open-elective-mathematics-iii EAS401 primary; "
     "mathematics-iii-science-based-open-elective all_codes EAS-301) — a slot "
     "print is program structure, not a subject (recorded B01 class)")

d = json.load(open(P))
n = 0
for s in d["subjects"]:
    if s.get("codes") == ["EAS301", "EAS401"]:
        if FLAG not in (s.get("flags") or []):
            s.setdefault("flags", []).append(FLAG)
        if Q not in (s.get("quirks") or []):
            s.setdefault("quirks", []).append(Q)
        n += 1
with open(P, "w") as f:
    json.dump(d, f, indent=1, ensure_ascii=False)
print(f"alt_pair flagged {n}")
