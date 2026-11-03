#!/usr/bin/env python3
"""patch_b13_verify_fixes.py — B13 verify-FAIL remedies (B08/B12 precedent).

verify_draft.py hard-failed 6 subjects across 2 drafts. Root-cause class in
every case: the document prints NO unit-structured syllabus for these rows
(they are project/internship-assessment or NPTEL/MOOCS-outline rows) —
zero-guess forbids inventing units (RULES §6/§7); the verifier-visible
evidence flags were missing. Remedies (same classes as B08 v11 + B12):

- doc10 BCS752 'Mini Project or Internship Assessment', BCS753 'Project-I',
  BCS851 'Project-II': each prints a real CO table (5 COs each, containment-
  checked by the subagent) and NO units anywhere → flag
  `co_only_no_units_printed` (B08 v11 evidence class: printed design of
  project/assessment courses).
- doc07 RCT753 'INDUSTRIAL TRAINNING': prints a training description
  paragraph (p.13) but no unit-structured syllabus, no COs → flag
  `detailed_syllabus_not_printed` (verifier-recognized class).
- doc07 RCT080 'TEXTURED YARN TECHNOLOGY (NPTEL/MOOCS)', RCT085 'ADVANCE
  TEXTILE PRINTING TECHNOLOGY (NPTEL/MOOCS)': the doc prints an NPTEL topic
  bullet list (preserved verbatim in draft `topics_print`), no Unit-I..V
  structure, no COs → flag `detailed_syllabus_not_printed` + quirk recording
  that the printed topic list is preserved in the draft for row-notes at merge.

Idempotent: flags only added when absent. Evidence string recorded per patch.
"""
import json, sys
from datetime import datetime, timezone

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

PATCHES = {
    "10_btech_ce-cse_y4_syllabus_2025-26": {
        "codes": ["BCS752", "BCS753", "BCS851"],
        "flag": "co_only_no_units_printed",
        "evidence": ("B13 patch: subject prints a CO table (5 COs, verbatim, containment-"
                     "checked) and NO unit theory anywhere in the doc — printed design of "
                     "project/assessment courses (B08 v11 evidence class); zero-guess "
                     "forbids inventing units (RULES §6)."),
    },
    "07_btech_carpet-textile_y4_syllabus-cbcs_2019-20": {
        "codes": ["RCT753", "RCT080", "RCT085"],
        "flag": "detailed_syllabus_not_printed",
        "evidence": ("B13 patch: doc prints no unit-structured detailed syllabus for this "
                     "row (RCT753: training description paragraph p.13 only; RCT080/RCT085: "
                     "NPTEL/MOOCS topic bullet list preserved verbatim in draft "
                     "topics_print); zero-guess forbids inventing units (RULES §6)."),
    },
}


def main():
    total = 0
    for stem, spec in PATCHES.items():
        path = f"{DRAFTS}/{stem}.draft.json"
        d = json.load(open(path))
        n = 0
        for s in d["subjects"]:
            codes = [str(c).replace(" ", "").replace("-", "").upper()
                     for c in (s.get("codes") or [])]
            if not any(c.replace("-", "") in [x.replace("-", "") for x in spec["codes"]] or c in spec["codes"] for c in codes):
                continue
            if spec["flag"] in (s.get("flags") or []):
                continue
            s.setdefault("flags", []).append(spec["flag"])
            s.setdefault("quirks", []).append(f"{NOW} {spec['evidence']}")
            n += 1
        with open(path, "w") as f:
            json.dump(d, f, indent=1, ensure_ascii=False)
        print(f"PATCH|{stem}|{spec['flag']}|{n} subjects")
        total += n
    print(f"TOTAL|{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
