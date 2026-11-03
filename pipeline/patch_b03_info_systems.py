#!/usr/bin/env python3
"""patch_b03_info_systems.py — B03 P7 (brain clause, conclusive print evidence).

Draft 03 (BCA Y1 2025-26) 'Information Systems' prints a heading code conflict:
the Sem-I SCHEME TABLE prints slot BBC106 for Information Systems (2025-26
revision replacing the 2024-25 BBC102 Mathematical-Foundation slot), while the
subject HEADING misprints 'BBC102' (the 2024-25 slot number; the fragment
subagent flagged heading_code_differs_from_scheme_code). The sibling 2024-25
doc (draft 02) already yields a BCA 'Information Systems' row (BBC205, sem-II)
— same subject name + course, so the registry holds ONE row (subject-first
define-once) and draft 03's data UPDATEs it (newer session wins fieldwise).

Patch: codes = ['BBC106'] (the scheme-table slot identity, primary); the
heading misprint 'BBC102' is recorded in the misprint narrative (code_note →
code_history_all on append/update) — never as an ownership claim, because
BBC102 is owned by the 2024-25 Mathematical-Foundation row (G2).
"""
import json

P = "/home/z/my-project/work/pipeline_v2/drafts/03_bca_y1_syllabus_2025-26.draft.json"
d = json.load(open(P))
n = 0
for s in d["subjects"]:
    if s.get("name") == "Information Systems":
        s["codes"] = ["BBC106"]
        q = ("[patch-P7] primary code set to the Sem-I scheme-table slot print BBC106 "
             "(2025-26 scheme page; the heading misprints 'BBC102' — the 2024-25 "
             "Mathematical-Foundation slot number; flagged heading_code_differs_from_scheme_code "
             "by the fragment subagent). BBC102 stays an ownership claim of the 2024-25 "
             "Mathematical-Foundation row (G2); recorded here as a misprint narrative. "
             "Same-named BCA subject already appended from the 2024-25 doc (BBC205) — "
             "this draft UPDATEs that row per subject-first define-once.")
        if q not in (s.get("quirks") or []):
            s.setdefault("quirks", []).append(q)
        if not s.get("code_note"):
            s["code_note"] = ("heading misprint BBC102; scheme slot BBC106 (2025-26); "
                              "sibling 2024-25 print: BBC205 Information Systems")
        n += 1
json.dump(d, open(P, "w"), ensure_ascii=False, indent=1)
print(f"PATCH|03-info-systems|changed={n}")
