#!/usr/bin/env python3
"""adjudicate_b49.py — inject the B49 adjudications into merge_draft.py
(marker: adjudicate_b49), idempotent. Evidence probed from the live CSV +
parsed fulltexts before writing (see worklog B49 section):
  * 4 TIER2 same-subject ALLOWs (CHE/EE/EN era accumulators)
  * 6 RETARGET_KEEP_PUBLISHED_CODE_OWNER GP entries (B25/B26 GP class)
  * 1 TIE RETARGET (B41 corroborating-copy convergence class, KAS402 kept)
"""
import json, re

M = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
MARK = "    # --- B49 commit-run adjudications (adjudicate_b49 marker) ---\n"
s = open(M).read()
if "adjudicate_b49 marker" in s:
    print("already injected; no-op")
    raise SystemExit(0)

def ALLOW(key, reason):
    return f'    "{key}": {{\n        "action": "ALLOW",\n        "reason": "{reason}"}},\n'

def RTK(key, target, keep, reason):
    return (f'    "{key}": {{\n        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER",\n'
            f'        "target": "{target}",\n'
            f'        "keep_published_codes": {json.dumps(dict(keep))},\n'
            f'        "reason": "{reason}"}},\n')

def RT(key, target, reason):
    return (f'    "{key}": {{\n        "action": "RETARGET",\n'
            f'        "target": "{target}",\n'
            f'        "reason": "{reason}"}},\n')

GP_R = ("B49 RETARGET_KEEP_PUBLISHED_CODE_OWNER (recorded B25/B26 GP class + B19 newest-print-wins): "
        "draft 'GP' (no-session N-era y4 scheme print, {code}) vs the BTech general-proficiency "
        "accumulator which ALREADY OWNS NGP-701;NGP-801;GP701;GP801 in all_codes (sess 2026-27). "
        "The name-identity 'gp' row (sess 2016-17) owns the NGP301-601 range, NOT the y4 codes. "
        "The published code owner wins; the y4 GP scheme print corroborates on the general-proficiency "
        "row; the intra-family 'gp'/'general-proficiency' (name,course) variance pair is recorded for "
        "owner reconciliation (B48 legacy-pair class). The B3 auto's premise (code slot re-used across "
        "DIFFERENT subjects) does not apply - GP is the same subject in both rows.")

block = MARK
block += ALLOW("01_btech_che_y4_syllabus::19::advance-separation-technology",
    "B49 TIER2 same-subject ALLOW (fuzzy 98, overlap 36): draft 'Advance Separation Technology' "
    "(NCH-033, BTech CHE y4 2016-17 DE-III, 5 verbatim units) vs the BTech advanced-separation-technology "
    "accumulator (ECH-051, sess 2009-10, unit1 empty) - the same Chemical-Engineering departmental-elective "
    "across eras (printed spelling variance Advance/ADVANCED; unit-I shared distinctive terms 'separation "
    "processes, equilibrium and rate governed multistage processes' class). Same course BTech per §1b "
    "(cross-course guard clean); tier-2 qualified per RULES §2. Update-first: 2016-17 print is newer -> "
    "fieldwise units backfill the empty row per §3; NCH-033 is unowned, accumulates into code_history.")
block += ALLOW("04_btech_ee_y4_syllabus::09::utilization-of-electrical-energy-and-traction",
    "B49 TIER2 same-subject ALLOW (fuzzy 88, overlap 68): draft 'UTILIZATION OF ELECTRICAL ENERGY AND "
    "TRACTION' (NEE-802, BTech EE y4 2016-17) vs the BTech utilization-of-electrical-energy-electric-traction "
    "accumulator (BEE-075;EEE-801;REE-071;KEE-079, sess 2025-26, unit1 empty) - the target's all_codes "
    "already own EEE-801, the E-era print of exactly this subject (code-family evidence, B28 ITC class); "
    "'&'/'AND' print variance. Same course BTech per §1b; tier-2 qualified per RULES §2. Draft is OLDER "
    "(2016-17 < 2025-26) -> backfill of empty unit fields only per §3; NEE-802 unowned, accumulates into "
    "code_history.")
block += ALLOW("04_btech_ee_y4_syllabus::16::ehv-ac-dc-transmission",
    "B49 TIER2 same-subject ALLOW (fuzzy 86, overlap 93): draft 'EHV AC & DC TRANSMISSION' (NEE-041, BTech "
    "EE y4 2016-17) vs the BTech hvdc-ac-transmission accumulator ('HVDC & AC Transmission', "
    "BEE-072;EEE-041;REE-085;KEE-072, sess 2025-26, unit1 empty) - the target's all_codes already own "
    "EEE-041, the E-era print of this subject (code-family evidence); the EHV->HVDC title drift is era "
    "rewording of the same course (recorded B28 ITC era-rewriting class), overlap 93 shared unit terms. "
    "Same course BTech per §1b; tier-2 qualified per RULES §2. Draft OLDER -> backfill empty units only; "
    "NEE-041 unowned, accumulates into code_history.")
block += ALLOW("05_btech_en_y4_syllabus::16::ehv-ac-dc-transmission",
    "B49 TIER2 same-subject ALLOW (fuzzy 86, overlap 95): draft 'EHV AC & DC TRANSMISSION' (NEE-041, BTech "
    "EN y4 2016-17 print, the EE/EN shared y4 wave) vs the BTech hvdc-ac-transmission accumulator (sess "
    "2025-26) - identical evidence class to 04_btech_ee_y4_syllabus::16 (EEE-041 owned by the target; "
    "EHV->HVDC era rewording; backfill-only update per §3); the commit-mode cascade unites the two "
    "same-name prints (B48 recorded class).")
block += RTK("01_btech_che_y4_syllabus::05::gp", "general-proficiency", ["NGP-701"], GP_R.format(code="NGP-701"))
block += RTK("01_btech_che_y4_syllabus::13::gp", "general-proficiency", ["NGP-801"], GP_R.format(code="NGP-801"))
block += RTK("04_btech_ee_y4_syllabus::18::gp", "general-proficiency", ["NGP-701"], GP_R.format(code="NGP-701"))
block += RTK("04_btech_ee_y4_syllabus::19::gp", "general-proficiency", ["NGP-801"], GP_R.format(code="NGP-801"))
block += RTK("05_btech_en_y4_syllabus::02::gp", "general-proficiency", ["NGP-701"], GP_R.format(code="NGP-701"))
block += RTK("05_btech_en_y4_syllabus::04::gp", "general-proficiency", ["NGP-801"], GP_R.format(code="NGP-801"))
block += RT("09_btech_s3-4_kas302-402h-maths-iv-pde-probability-statistics::00::mathematics-iv",
    "engg-science-course-maths-iv",
    "B49 TIE resolution (B41 corroborating-copy convergence class): draft 'MATHEMATICS-IV' "
    "(KAS302/KAS402/KAS302H/KAS402H, Basic Science Course, 5 verbatim units - the detailed PDE/Probability "
    "print) hits a Tier-0 TIE across the flipped-name 2019-20 model-curriculum scheme rows "
    "engg-science-course-maths-iv (KAS302;KOE031 owner) and maths-iv-engg-science-course (KAS402 owner). "
    "RETARGET pins the update on the KAS302 published owner (first-printed draft code, same 2019-20 era): "
    "the 5 verbatim units backfill its empty unit fields (GAP closure per §3 same-era corroboration); "
    "KAS302H/KAS402H (unowned H-variant prints) accumulate into all_codes. keep_published_codes=[KAS402] "
    "keeps KAS402 with its published owner maths-iv-engg-science-course (G2 single ownership). The "
    "flipped-name pair + the bare maths-iv row (no codes) are recorded for owner reconciliation (B48 "
    "legacy (name,course)-variance class) - never silently merged.")

anchor = 'TIER2_OVERRIDES = {\n'
assert anchor in s
s = s.replace(anchor, anchor + block, 1)
open(M, "w").write(s)
print("injected B49 adjudications: 4 ALLOW + 6 RETARGET_KEEP_PUBLISHED_CODE_OWNER + 1 RETARGET")
