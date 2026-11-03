#!/usr/bin/env python3
"""patch_b15_code_adjudications.py — B15 draft-code adjudication with recorded
evidence (RULES §4 brain clause: determine-then-fix, keep proof).

Evidence: 06_btech_che_course-structure_2026-27 subject 00 'Physics of Process
Engineering Materials' prints BOTH AAS101F/AAS201F (detail pages) and
AAS101G/AAS201G (CH-stream scheme table). The published CSV row
'physics-of-materials-and-biomaterials' (BT stream 2026-27 doc
btech_bt_course-structure_2026-27.pdf#49a930c63f3156b9) already owns
AAS101F;AAS201F and carries a DIFFERENT unit canon (u1 'Fundamentals of
Quantum Mechanics... de-Broglie... Davisson and Germer' vs the CHE draft's
u1 'Structure and properties of materials... crystal structures (BCC, FCC,
HCP)...') and different COs — TWO DIFFERENT subjects printed under shared
template F-codes (RULES §11: never merge two different subjects). The CH
scheme's G-codes are the CHE subject's ownership codes; the F-code detail
print is retained verbatim in the draft quirk as evidence and NOT claimed
(G2: one code owner per course).
"""
import json

P = "/home/z/my-project/work/pipeline_v2/drafts/06_btech_che_course-structure_2026-27.draft.json"
d = json.load(open(P))
s = d["subjects"][0]
assert s["name"] == "Physics of Process Engineering Materials", s["name"]
s["codes"] = ["AAS101G", "AAS201G"]
q = ("patch-b15 code adjudication: the CH detail pages print AAS101F/AAS201F "
     "(shared template print) while the CH-stream scheme table prints "
     "AAS101G/AAS201G for this subject; AAS101F;AAS201F are PUBLISHED as owned "
     "by 'Physics of Materials and Biomaterials' (BT stream 2026-27, "
     "btech_bt_course-structure_2026-27.pdf#49a930c63f3156b9) whose unit canon "
     "(u1 Quantum Mechanics: de-Broglie, Davisson-Germer, wave packets) differs "
     "from this subject's canon (u1 Structure and properties of materials: "
     "bonding, crystal structures BCC/FCC/HCP, stress/strain) — different "
     "subjects under a shared template print (RULES §11), so the F-codes stay "
     "with their published owner and are NOT claimed here (G2); ownership "
     "codes: AAS101G;AAS201G.")
if q not in (s.get("quirks") or []):
    s.setdefault("quirks", []).append(q)
with open(P, "w") as f:
    json.dump(d, f, indent=1, ensure_ascii=False)
print("PATCHED|06::00|codes->AAS101G,AAS201G|F-codes recorded as quirk evidence")
