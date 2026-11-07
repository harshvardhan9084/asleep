#!/usr/bin/env python3
"""adjudicate_b49b.py — second-wave B49 adjudications after the aborted first
commit surfaced the intra-batch cascade TIEs (recorded B44 class: dry-run plans
are computed against the pre-commit CSV; commit-mode-only TIEs surface when doc
04's dual-print updates add the second code to a row). Idempotent (marker:
adjudicate_b49b).

KEEP rulings (B19: an older print never steals a code from a newer-session
published owner) — the batch print era is 2016-17:
  NEN-031 (soil-and-water-conservation-engineering 2025-26), NEN-032
  (engineering-geology 2024-25), NEN-043 (river-engineering 2024-25),
  NEN-751 (seminar 2019-20), NEC-802 (optical-networks 2021-22), NOE-083
  (product-development 2016-17, same-era published owner; the doc-05 NOE-085
  print lands on the DBMS row instead) — all KEPT with their published owners.
Transfers ALLOWED (owners OLDER than the 2016-17 print, newest-print-wins):
  NEN-701 (health-safety-and-environment 2009-10), NEN-702 (estimation-and-
  project-management 2009-10), NEN-753 (project-btech pre-existing wrong
  ownership; name-identity row industrial-training is the recorded B3 fix).
RETARGET pins for the 8 commit-mode TIEs (name-identity rows).
"""
import json

M = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
s = open(M).read()
if "adjudicate_b49b marker" in s:
    print("already injected; no-op")
    raise SystemExit(0)

def RTK(key, target, keep, reason):
    return (f'    "{key}": {{\n        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER",\n'
            f'        "target": "{target}",\n'
            f'        "keep_published_codes": {json.dumps(keep)},\n'
            f'        "reason": "{reason}"}},\n')

def RT(key, target, reason):
    return (f'    "{key}": {{\n        "action": "RETARGET",\n'
            f'        "target": "{target}",\n'
            f'        "reason": "{reason}"}},\n')

KEEP = ("B49 KEEP (B19 ruling: an older print never steals a code from a newer-session published "
        "owner): draft {codes} ({what}, no-session N-era 2016-17 print) vs {code} currently owned by "
        "{owner} (sess {osess}, NEWER than this print). The {code} scheme print is recorded as "
        "narrative on the updated row; ownership stays with the published owner; G2 single-ownership "
        "preserved. The unowned sibling codes of the draft land normally.")

TIE_R = ("B49 commit-mode TIE resolution (B44 intra-batch cascade class - the dry-run laddered against "
         "the pre-commit CSV where the second code was unowned/differently owned; doc 04's earlier "
         "update in THIS commit created the second candidate): RETARGET pins the name-identity row "
         "{target} (the exact-name accumulator; same course BTech per §1b). Update-first per the "
         "owner rule; fieldwise per §3.")

block = "    # --- B49b commit-run adjudications (adjudicate_b49b marker) ---\n"
block += RTK("04_btech_ee_y4_syllabus::03::advanced-microprocessors-and-microcontrollers",
             "advanced-microprocessors-and-microcontrollers",
             {"NEN-032": "engineering-geology"},
             KEEP.format(codes="NEE-032/NEN-032", what="BTech EE y4 2016-17 DE print",
                         code="NEN-032", owner="engineering-geology", osess="2024-25"))
block += RTK("04_btech_ee_y4_syllabus::15::power-system-operation-and-control",
             "power-system-operation-and-control",
             {"NEN-031": "soil-and-water-conservation-engineering"},
             KEEP.format(codes="NEE-031/NEN-031", what="BTech EE y4 2016-17 DE print",
                         code="NEN-031", owner="soil-and-water-conservation-engineering", osess="2025-26"))
block += RTK("04_btech_ee_y4_syllabus::05::embedded-systems",
             "embedded-systems",
             {"NEC-802": "optical-networks"},
             KEEP.format(codes="NEE-043/NEC-802", what="BTech EE y4 2016-17 DE print",
                         code="NEC-802", owner="optical-networks", osess="2021-22"))
block += RTK("04_btech_ee_y4_syllabus::26::database-management-system-and-data-mining-and-warehousing",
             "database-management-system-and-data-mining-and-warehousing",
             {"NOE-083": "product-development"},
             KEEP.format(codes="NOE-083", what="BTech EE y4 2016-17 OE print",
                         code="NOE-083", owner="product-development", osess="2016-17")
             + " The doc-05 print of the same subject is NOE-085 (the recorded 04/05 083-vs-085 scheme "
               "discrepancy): NOE-085 is unowned and lands on the DBMS row via this update; the 04 print "
               "stays with its published same-era owner.")
block += RTK("05_btech_en_y4_syllabus::08::advanced-microprocessors-and-microcontrollers",
             "advanced-microprocessors-and-microcontrollers",
             {"NEN-032": "engineering-geology"},
             KEEP.format(codes="NEE-032/NEN-032", what="BTech EN y4 2016-17 DE print",
                         code="NEN-032", owner="engineering-geology", osess="2024-25"))
block += RTK("05_btech_en_y4_syllabus::10::embedded-systems",
             "embedded-systems",
             {"NEC-802": "optical-networks"},
             KEEP.format(codes="NEE-043/NEC-802", what="BTech EN y4 2016-17 DE print",
                         code="NEC-802", owner="optical-networks", osess="2021-22"))
block += RTK("05_btech_en_y4_syllabus::15::power-system-operation-and-control",
             "power-system-operation-and-control",
             {"NEN-031": "soil-and-water-conservation-engineering"},
             KEEP.format(codes="NEE-031/NEN-031", what="BTech EN y4 2016-17 DE print",
                         code="NEN-031", owner="soil-and-water-conservation-engineering", osess="2025-26"))
block += RTK("05_btech_en_y4_syllabus::17::image-processing",
             "image-processing",
             {"NEN-043": "river-engineering"},
             KEEP.format(codes="NEN-043", what="BTech EN y4 2016-17 DE-IV print",
                         code="NEN-043", owner="river-engineering", osess="2024-25"))
block += RTK("05_btech_en_y4_syllabus::19::power-system-lab",
             "power-system-lab",
             {"NEN-751": "seminar"},
             KEEP.format(codes="NEN-751", what="BTech EN y4 2016-17 practical print",
                         code="NEN-751", owner="seminar", osess="2019-20"))
block += RT("05_btech_en_y4_syllabus::01::project", "project-btech",
            TIE_R.format(target="project-btech"))
block += RT("05_btech_en_y4_syllabus::03::project", "project-btech",
            TIE_R.format(target="project-btech"))
block += RT("05_btech_en_y4_syllabus::11::flexible-ac-transmission-systems",
            "flexible-ac-transmission-systems",
            TIE_R.format(target="flexible-ac-transmission-systems")
            + " The target row is the FATS row appended EARLIER IN THIS COMMIT by doc 04 (NEE-033 "
              "establishing print); this update unites the EN print (B48 commit-cascade class).")
block += RT("05_btech_en_y4_syllabus::12::electric-drives", "electric-drives",
            TIE_R.format(target="electric-drives")
            + " NEN-701 transfers here per the recorded B3 newest-print-wins model (the published owner "
              "health-safety-and-environment is the OLDER 2009-10 print; narrative history retained).")
block += RT("05_btech_en_y4_syllabus::13::power-station-practice", "power-station-practice",
            TIE_R.format(target="power-station-practice")
            + " NEN-702 transfers here per the recorded B3 newest-print-wins model (owner "
              "estimation-and-project-management is the OLDER 2009-10 print; narrative retained).")

anchor = "TIER2_OVERRIDES = {\n"
assert anchor in s
s = s.replace(anchor, anchor + block, 1)
open(M, "w").write(s)
print("injected B49b adjudications: 9 RTK + 5 RT")
