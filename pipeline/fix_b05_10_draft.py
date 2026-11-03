#!/usr/bin/env python3
"""CRON-20261027-B05 draft fix — stem 10 (btech_carpet-textile_y4_syllabus_2025-26).

The carpet y4 doc prints the SAME code BCT752 on TWO scheme rows (Sl.5 'Mini Project
or Internship Assessment*' and Sl.6 'Project - I') — a print quirk. The drafter kept
BCT752 in the Project-I row's codes_print as EVIDENCE (primary_code left empty), with
a note predicting that a second ACTIVE binding of BCT752 would violate G2.

At commit, the live re-ladder used that evidence code for Tier-0 identity and
redirected Project-I's UPDATE->project-i into the mini-project row — merging two
DISTINCT subjects (siblings 2026-27 docs print a distinct Project-I code on this slot:
BEC753 in ACT, BMN753 in mining). Fix per the drafter's own design: remove BCT752 from
the Project-I row's codes_print (evidence already verbatim in notes; add brain_fix).
Zero-guess intact: nothing invented, only the duplicate active binding removed.
"""
import json

DRAFT = "/home/z/my-project/work/pipeline_v2/drafts/10_btech_carpet-textile_y4_syllabus_2025-26.draft.json"

d = json.load(open(DRAFT, encoding="utf-8"))
fixed = 0
for s in d.get("subjects", []):
    if (s.get("name_slug") or "") == "project-i" and "BCT752" in (s.get("codes_print") or []):
        s["codes_print"] = [c for c in s["codes_print"] if c != "BCT752"]
        bf = s.setdefault("brain_fixes", [])
        bf.append({
            "field": "codes_print",
            "print": "BCT752 (duplicate print on Project-I row, same code as Sl.5 Mini Project or Internship Assessment*)",
            "corrected": "removed from active codes; kept verbatim in notes with scheme-cell page evidence",
            "reason": "duplicate code print on two distinct scheme rows; sibling 2026-27 Y4 docs print a "
                      "DISTINCT Project-I code on this slot (BEC753 ACT, BMN753 mining); second active "
                      "BCT752 binding would (a) violate G2 code-uniqueness, (b) let the commit live "
                      "re-ladder Tier-0-merge Project-I into the mini-project row (observed in commit v1)"
        })
        note = s.setdefault("notes", [])
        note.append("[B05 orchestrator brain_fix] codes_print evidence-code BCT752 removed from this row "
                    "pre-merge (duplicate active-binding risk; print preserved in notes + brain_fixes).")
        fixed += 1

json.dump(d, open(DRAFT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"fixed {fixed} subject row(s); codes_print for project-i now:",
      [s.get("codes_print") for s in d["subjects"] if s.get("name_slug") == "project-i"])
