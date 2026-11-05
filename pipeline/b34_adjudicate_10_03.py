#!/usr/bin/env python3
"""b34_adjudicate_10_03.py — CRON-20261105-B34 adjudication for
10_btech_mfg-tech_y3_evaluation-scheme_2024-25::03::heat-transfer-lab.

Situation at replay commit: draft 'Heat Transfer Lab' (BME 551, 2024-25
Mfg-Tech y3 eval-scheme print). Tier-0 code identity now hits TWO rows:
  - heat-and-mass-transfer-lab (KME551;BME551;NBT-452;NEN554, latest 2020-21)
  - heat-transfer-lab (ECH-656;RCH355;RCH455, the CHEM-family accumulator)
In B30's ORIGINAL run the auto CODE-REASSIGNED name-transfer moved BME551 to
heat-transfer-lab — but that transfer predates the recorded B29-2nd ruling
(already injected in merge_draft.py TIER2_OVERRIDES for the ME-Ind print of
the SAME 2024-25 session): 'Heat Transfer Lab' (BME551, 2024-25) is a
same-session name-variant corroboration of the ME-family lab, RETARGET to
heat-and-mass-transfer-lab per the recorded B27 RCS653 class; BME551's
published owner keeps the code; the CHEM-family heat-transfer-lab row keeps
its own ECH-656/RCH355/RCH455 identity untouched.

The newer recorded ruling supersedes the B30-era auto (recorded
newest-ruling-wins; same evidence base, same session, same code, same
name-variant class). Zero-GAP holds: the Mfg-Tech print lands on the
ME-family lab row as a fieldwise 2024-25 update.
"""
import re

MD = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
MARK = "B34 (CRON-20261105-B34) 10::03 heat-transfer-lab RETARGET"

src = open(MD).read()
if MARK in src:
    print("  (already injected)")
else:
    block = '''
# ---- B34 (CRON-20261105-B34) 10::03 heat-transfer-lab RETARGET ----
TIER2_OVERRIDES.update({
    "10_btech_mfg-tech_y3_evaluation-scheme_2024-25::03::heat-transfer-lab": {
        "action": "RETARGET", "target": "heat-and-mass-transfer-lab",
        "reason": "B34 replay adjudication (newest recorded ruling supersedes the B30-era auto; recorded B29-2nd ruling for the SAME 2024-25 BME551 print, B27 RCS653 same-session name-variant class): draft 'Heat Transfer Lab' (BME 551, 2024-25 Mfg-Tech y3 eval-scheme print, detailed experiment list) — Tier-0 code identity now hits TWO rows because B29-2nd's recorded merge gave heat-and-mass-transfer-lab the BME551 ownership (KME551 2020-21 continuity -> BME551 2024-25) while the B30-era auto (executed before that ruling existed) had transferred BME551 to the CHEM-family heat-transfer-lab row. The recorded B29 ruling governs: BME551's owner is heat-and-mass-transfer-lab; this Mfg-Tech print is a same-session name-variant corroboration of the SAME ME-family lab (thermal-conductivity/heat-exchanger experiment list) -> RETARGET pins the fieldwise 2024-25 update on the published owner; the CHEM-family heat-transfer-lab row (ECH-656;RCH355;RCH455) is a different subject and stays untouched; the 'Heat Transfer Lab' print variant recorded in the change note."},
})
'''
    # insert right after the last TIER2_OVERRIDES.update({...}) block
    lines = src.split("\n")
    starts = [i for i, l in enumerate(lines) if l.startswith("TIER2_OVERRIDES.update({")]
    assert starts, "no TIER2_OVERRIDES.update block found"
    s = starts[-1]
    depth = 0
    e = None
    for i in range(s, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if depth == 0 and i > s:
            e = i
            break
    assert e is not None
    lines.insert(e + 1, block)
    open(MD, "w").write("\n".join(lines))
    print("  injected after TIER2_OVERRIDES block ending line", e + 1)
