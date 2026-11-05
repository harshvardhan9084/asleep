#!/usr/bin/env python3
"""b34_adjudicate_acc_pair.py — CRON-20261105-B34 corrective adjudications for the
automation-and-robotics accumulator pair (04::11 + 08::11), matching the RECORDED
B30 FINAL state (commit 747874e: 'G3-taught accumulator RETARGET pair
(automation-and-robotics 3-print reconciliation)'; row state durable in the B32
published CSV: automation-and-robotics all_codes BOE302;BOE402;BOE302H;BOE402H;
NOE084;EOE-084;NME-044;KMT053;RPI701, NO separate '-btech' row, RME078 stays with
robotics-and-automation).

The local adjudicate_b30.py copy carries STALE pre-G3 entries (04::11
FORCE_APPEND, 08::11 RETARGET to a to-be-appended 'automation-and-robotics-btech'
row) — those were superseded during B30's own run when G3 taught the
(name,course) collision: both prints land on the EXISTING open-elective
accumulator row automation-and-robotics as era corroborations:
  - 04::11 (2019-20 ME DE-3 print, RME078 stripped draft-side per the recorded
    B29 keep-published ruling -> codeless draft): older session (2019-20 <
    2023-24) -> backfill-empty-only + provenance/source_history extension;
    the no-code evidence quirk stays on the draft subject.
  - 08::11 (2020-21 Mfg-Tech DE print 'Automation & Robotics', KMT053 unowned):
    older session (2020-21 < 2023-24) -> backfill-empty-only; KMT053 joins the
    row's codes exactly as the recorded final all_codes shows; both fuzzy-90
    name-family rows (open-elective BOE302 row = same accumulator; the
    robotics-and-automation AI-DS print row) are distinguished by the recorded
    content evidence (J=0.15 / J=0.06 vs near-verbatim ME-print units).
"""
import re

MD = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
MARK = "B34 (CRON-20261105-B34) accumulator-pair corrective (G3-taught, recorded B30 final)"

src = open(MD).read()
if MARK in src:
    print("  (already injected)")
else:
    block = '''
# ---- B34 (CRON-20261105-B34) accumulator-pair corrective (G3-taught, recorded B30 final) ----
TIER2_OVERRIDES.update({
    "04_btech_me_y4_syllabus-cbcs_2019-20::11::automation-and-robotics": {
        "action": "RETARGET", "target": "automation-and-robotics",
        "reason": "B34 corrective to the recorded B30 FINAL state (747874e 'G3-taught accumulator RETARGET pair (automation-and-robotics 3-print reconciliation)'; B32 published CSV row state = NO separate '-btech' row). The stale pre-G3 FORCE_APPEND entry (local adjudicate_b30.py copy) is superseded: appending a second BTech 'Automation and Robotics' row violates G3 (name,course) uniqueness — B30's own run learned this and pinned the 2019-20 ME DE-3 print onto the existing open-elective accumulator row as an era corroboration. 2019-20 < 2023-24 (row's latest print): backfill-empty-only + source_history extension (RULES §3); RME078 stays stripped draft-side (keep-published with robotics-and-automation per the recorded B29 04::13 ruling; the accumulator's recorded all_codes deliberately excludes RME078); the no-code evidence quirk stays on the draft subject."},
    "08_btech_mfg-tech_syllabus_2020-21::11::automation-robotics": {
        "action": "RETARGET", "target": "automation-and-robotics",
        "reason": "B34 corrective to the recorded B30 FINAL state (747874e 'G3-taught accumulator RETARGET pair'): the 2020-21 Mfg-Tech DE print 'Automation & Robotics' (KMT053, unowned) lands on the automation-and-robotics accumulator row (G3-unique (name,course)); both fuzzy-90 candidates are same-name different-content rows per the recorded evidence (BOE302 open-elective units J=0.17 vs the ME-print units the accumulator now carries; robotics-and-automation J=0.06 = the AI-DS ML print) — the near-verbatim match is the ME-print lineage already reconciled into the accumulator. 2020-21 < 2023-24 (row's latest print): backfill-empty-only; KMT053 joins the row's codes exactly as the recorded B32 all_codes shows (BOE302;...;NME-044;KMT053;RPI701); both era prints accumulate in source_history."},
})
'''
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
