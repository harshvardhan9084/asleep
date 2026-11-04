#!/usr/bin/env python3
"""B29 (CRON-20261105-B29) merge adjudications — inserted into TIER2_OVERRIDES.

Every entry carries recorded evidence per the established classes:
- B27 RCS653 same-session class: two authoritative same-session prints cannot
  be split by newest-print-wins; the published owner keeps the code.
- B19 keep_published_codes: kept code dropped from the draft copy, narrative
  recorded on the target row, G2 single ownership preserved.
- B25/B26 GP class: equal/older print never takes a code from its published
  newer-print owner.
- B28 wrong-subject FORCE_APPEND class; TIER2 same-subject ALLOW class.
- Recorded prior RME078 adjudication (02_btech_au_y4_syllabus-cbcs_2019-20::09):
  RME078 = the AU-branch robotics lineage row robotics-and-automation.
"""
import re

PATH = '/home/z/my-project/scripts/pipeline_v2/merge_draft.py'
src = open(PATH, encoding='utf-8').read()

BLOCK = '''
    # ---- B29 (CRON-20261105-B29) per-key adjudications, evidence-recorded ----
    "02_btech_me-ind_y3_evaluation-scheme_2024-25::03::heat-transfer-lab": {
        "action": "RETARGET", "target": "heat-and-mass-transfer-lab",
        "reason": "B29 same-session name-variant corroboration (recorded B27 RCS653 class): draft 'Heat Transfer Lab' (BME551, 2024-25 ME-Ind eval-scheme print, detailed experiment list) — the auto CODE-REASSIGNED name-transfer would move BME551 from heat-and-mass-transfer-lab to the name-exact heat-transfer-lab row (a CHEM-family accumulator: ECH-656 2009-10 BT print + RCH355/455 2017-18). BME551's published owner heat-and-mass-transfer-lab carries the recorded continuity KME551 (2020-21 'Heat & Mass Transfer Lab') -> BME551 (2024-25, established from btech_ae_y3_syllabus_2024-25 detailed print) — this ME-Ind print is a same-session name-variant corroboration of the SAME ME-family lab (thermal-conductivity/heat-exchanger experiments), not a different subject. RETARGET pins the update on the published owner; the 'Heat Transfer Lab' print variant is recorded in the change note."},
    "02_btech_me-ind_y3_evaluation-scheme_2024-25::11::computational-fluid-dynamics": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "computational-fluid-dynamics",
        "keep_published_codes": {"BME055": "turbo-machines"},
        "reason": "B29 doc-internal code-pairing contradiction (recorded B27 RCS653 class + print-quirk rule §6): this eval-scheme doc's p.4 mapping table prints BME055=Turbo Machines / BME062=CFD while its detail-page headers print BME055 on the CFD page and BME062 on the Turbo page — the SAME 08-Hours Turbo unit text is printed under BME055 in the published same-session detailed print (btech_au_y3_syllabus_2024-25, turbo-machines row unit1 verbatim-identical to this doc's Turbo page). Three independent evidences (this doc's own mapping table + the AU detailed print + the published registry) establish BME055=Turbo Machines / BME062=CFD; the detail-header print is the outlier and is recorded as a print-quirk. The auto name-identity transfers would INVERT the published pairing — rejected. BME055 stays with turbo-machines; BME062 stays with computational-fluid-dynamics; the draft's CFD units corroborate the CFD row (2024-25 print older than the row's 2025-26 BAE074 session — backfill-empty only)."},
    "02_btech_me-ind_y3_evaluation-scheme_2024-25::21::turbo-machines": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "turbo-machines",
        "keep_published_codes": {"BME062": "computational-fluid-dynamics"},
        "reason": "B29 doc-internal code-pairing contradiction (same evidence as 02::11): BME062 stays with computational-fluid-dynamics (this doc's p.4 mapping table + the published same-session detailed prints); the detail-page header printing BME062 on the Turbo page is recorded as a print-quirk. The draft's 08-Hours Turbo units are verbatim-identical to the turbo-machines row's establishing print (btech_au_y3_syllabus_2024-25) — same-session corroboration; BME055 remains this row's 2024-25 code."},
    "04_btech_me-ind_y4_syllabus-cbcs_2019-20::00::cad-cam": {
        "action": "RETARGET", "target": "cad-cam-computer-aided-design-and-manufacturing",
        "reason": "B29 same-subject name-shortening RETARGET (recorded B23 code-owner class + B28 era-accumulator class): draft 'CAD/CAM' (RME701, 2019-20 ME-Ind CBCS print, detailed units 'Principles of Computer Graphics...') — the auto CODE-REASSIGNED path (collapsed-name 0.26 < 0.84) would APPEND a new row and transfer RME701, splitting ONE subject into two rows (RULES §11). The target row already owns RME701 from a 2019-20 print (btech_au_y4_syllabus-cbcs_2019-20, recorded in code_history) — 'CAD/CAM' is the abbreviated print of the same subject ('CAD/CAM Computer Aided Design and Manufacturing'); 0.26 is a prefix-abbreviation artifact of the full-name ratio. Same-session corroborating print: fieldwise update; EAU701/NAU-701 E-era history retained."},
    "04_btech_me-ind_y4_syllabus-cbcs_2019-20::02::cad-cam-lab": {
        "action": "RETARGET", "target": "computer-aided-design-manufacturing-lab",
        "reason": "B29 same-session code-owner RETARGET (recorded B27 RCS653 class, B23 07::20 KAS401 pattern): draft 'CAD/CAM Lab' (RME751, 2019-20 ME-Ind CBCS print, experiment list) — the auto name-identity transfer would move RME751 from its published 2019-20 owner computer-aided-design-manufacturing-lab (establishing print btech_au_y4_syllabus-cbcs_2019-20) onto the E-era cad-cam-lab row (EAU751 2009-10 / NAU-751 2016-17). RME751's owner print is the SAME session as this corroborating ME-Ind print of the SAME ME-family lab; an equal-session print never takes a code from its published owner. RETARGET pins the experiment-list corroboration on the RME751 owner row; the E-era cad-cam-lab row is untouched."},
    "04_btech_me-ind_y4_syllabus-cbcs_2019-20::13::automation-and-robotics": {
        "action": "RETARGET", "target": "robotics-and-automation",
        "reason": "B29 recorded-prior-adjudication RETARGET (recorded entry 02_btech_au_y4_syllabus-cbcs_2019-20::09::automation-robotics): draft 'Automation and Robotics' (RME078, 2019-20 ME-Ind CBCS DE-4 print, detailed units) — the SAME 2019-20 CBCS RME-078 DE-slot print already adjudicated to the robotics-and-automation row (branch+era affinity: EAU013 2011-12 AU elective + KAD073 2024-25 AI-DS cross-listing = the AU-branch robotics lineage; the competing automation-and-robotics row BOE302/402 is the 2nd-year university-wide OPEN-ELECTIVE member row, different program level). The auto name-identity transfer contradicts that recorded resolution — rejected. RME078 is already owned by the target; 2019-20 print older than the row's 2024-25 session: backfill-empty only; name-order print variance recorded."},
    "04_btech_me-ind_y4_syllabus-cbcs_2019-20::19::total-quality-management": {
        "action": "RETARGET", "target": "total-quality-management-tqm",
        "reason": "B29 TIE resolution (fuzzy 92 total-quality-management-tqm vs 86 quality-management) on print identity + code lineage: draft 'Total Quality Management' (RME085, 2019-20 ME-Ind CBCS DE-6 print, detailed units verbatim-continuing the TQM accumulator's 'Quality Concepts: Evolution of Quality control, concept change, TQM Modern concept...' text) — the TQM row is the ME-Ind establishing print (NME-041, 2016-17 ME-Ind-PE-IPE, same DE family); RME085 joins as the era code. The competing quality-management row (NOE072/EOE-072, Civil-branch open-elective accumulator, fuzzy 86 on generic quality vocabulary) is a distinct printed course with its own code family; the shared unit1 opening is generic TQM vocabulary. RULES §2: higher score + print identity wins."},
    "06_btech_me-ind_y4_syllabus_2025-26::04::total-quality-management": {
        "action": "RETARGET", "target": "total-quality-management-tqm",
        "reason": "B29 TIE resolution (same evidence as 04::19): draft 'Total Quality Management' (BPI062, 2025-26 ME-Ind print, detailed units) — converges onto the TQM accumulator (NME-041 2016-17 -> RME085 2019-20 -> BPI062 2025-26); 2025-26 is the newest session: fieldwise units win; the Civil quality-management row (fuzzy 86) stays untouched."},
    "07_btech_me-pe_syllabus_2009-10::02::general-proficiency": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "general-proficiency",
        "keep_published_codes": {"GP301": "general-proficiency-lab"},
        "reason": "B29 code-owner protection (recorded B25/B26 GP class, IDENTICAL resolution to 04_btech_it_y2_scheme-syllabus_2009-10::09::general-proficiency): draft 'General Proficiency' (GP-301, 2009-10 ME-PE scheme-row print) — the auto CODE-REASSIGNED name-transfer would move GP301 from general-proficiency-lab (its recorded owner per the B25/B26 class) to the name-exact general-proficiency row; an equal-or-older print never takes a code from its published owner (RULES §3). RETARGET pins the scheme-row corroboration on the name-exact general-proficiency row; GP301 STAYS with general-proficiency-lab (B19 keep_published_codes mechanism)."},
    "07_btech_me-pe_syllabus_2009-10::75::operations-research": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "operations-research",
        "keep_published_codes": {"EME051": "computer-aided-vehicle-design"},
        "reason": "B29 same-session cross-branch collided DE-slot print (recorded B27 RCS653 class): draft 'Operations Research' (EME-051, 2009-10 ME-PE DE print, detailed units) — EME051 is ALSO printed by the SAME-SESSION 2009-10 AU doc (btech_au_syllabus_2009-10, dual EAU051/EME051 slot print) for Computer Aided Vehicle Design, whose row owns it. Two authoritative same-session prints cannot be split by newest-print-wins; the published owner keeps EME051. The ME-PE subject content converges onto the name-exact multi-branch operations-research accumulator (already NOE073;KOE075;RCS-051;EOE-073;NME-051 — the 2016-17 ME-Ind-PE-IPE print established NME-051 for the same subject); the 2009-10 EME-051 print is recorded as narrative (B19 mechanism); G2 single ownership preserved."},
    "07_btech_me-pe_syllabus_2009-10::76::maintenance-engineering-management": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "maintenance-engineering-management",
        "keep_published_codes": {"EME052": "alternative-energy-sources-for-automobiles"},
        "reason": "B29 same-session cross-branch collided DE-slot print (recorded B27 RCS653 class, same evidence as 07::75): EME052 is printed by the 2009-10 AU doc for Alternative Energy Sources for Automobiles (dual EAU052/EME052 slot print) AND by this 2009-10 ME-PE doc for Maintenance Engineering & Management — the published owner keeps EME052. The ME-PE subject updates the name-exact maintenance-engineering-management row (2018-19 AU establishing print; 2009-10 print is OLDER: backfill-empty only; the collided print recorded as narrative)."},
    "07_btech_me-pe_syllabus_2009-10::77::design-of-thermal-systems": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "design-of-thermal-systems",
        "keep_published_codes": {"EME053": "vehicle-dynamics"},
        "reason": "B29 same-session cross-branch collided DE-slot print (recorded B27 RCS653 class, same evidence as 07::75): EME053 is printed by the 2009-10 AU doc for Vehicle Dynamics (dual EAU053/EME053 slot print) AND by this 2009-10 ME-PE doc for Design of Thermal Systems — the published owner keeps EME053. The ME-PE subject updates the name-exact design-of-thermal-systems row (NME-052, 2016-17 ME-Ind-PE-IPE establishing print; 2009-10 print older: backfill-empty only; collided print recorded as narrative)."},
    "07_btech_me-pe_syllabus_2009-10::81::finite-element-method": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "finite-element-method",
        "keep_published_codes": {"EME061": "computer-simulation-of-ic-engines-process"},
        "reason": "B29 same-session cross-branch collided DE-slot print (recorded B27 RCS653 class, same evidence as 07::75): EME061 is printed by the 2009-10 AU doc for Computer Simulation of I.C. Engines (dual EAU061/EME061 slot print) AND by this 2009-10 ME-PE doc for Finite Element Method — the published owner keeps EME061. The ME-PE FEM print converges onto the name-exact finite-element-method row (the recorded 6-branch FEM accumulator, B28 10::08 class: era reorganization not a different subject); the collided print recorded as narrative; G2 preserved."},
    "07_btech_me-pe_syllabus_2009-10::82::non-destructive-testing": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "non-destructive-testing",
        "keep_published_codes": {"EME062": "computer-simulation-of-ic-engines-process"},
        "reason": "B29 same-session cross-branch collided DE-slot print (recorded B27 RCS653 class, same evidence as 07::75): EME062 is printed by the 2009-10 AU doc (its row history records 'EME062 (2009-10)' alongside EAU061/EME061) AND by this 2009-10 ME-PE doc for Non-Destructive Testing — the published owner keeps EME062. The ME-PE NDT print updates the name-exact non-destructive-testing row (NME-065, 2016-17 ME-Ind-PE-IPE establishing print; 2009-10 print older: backfill-empty only; collided print recorded as narrative)."},
    "07_btech_me-pe_syllabus_2009-10::86::fundamentals-of-biomedical-engineering": {
        "action": "FORCE_APPEND",
        "reason": "B29 wrong-subject FORCE_APPEND (recorded B28 class, J=0.11-0.19 precedents + RULES §11 never-merge-different-subjects): draft 'Fundamentals of Biomedical Engineering' (EME-066, 2009-10 ME-PE DE print, detailed units: biomechanics, musculoskeletal statics/dynamics, bioelectric signals) — the Tier-2 hit fundamentals-of-electrical-engineering (AEE101C/BEE101 Ag-generation row, fuzzy 87 on the shared 'fundamentals-of-X-engineering' name skeleton, unit-vocabulary overlap only 6) is a DIFFERENT subject (circuits/machines vs biomechanics/bioinstrumentation). Appends as its own row with a cross-reference note to the electrical-engineering row."},
    "02_btech_me-ind_y3_evaluation-scheme_2024-25::14::refrigeration-air-conditioning": {
        "action": "ALLOW",
        "reason": "B29 same-subject name-variant ALLOW (recorded TIER2 class): 'Refrigeration & Air Conditioning' (BME653, 2024-25) -> refrigeration-and-air-conditioning accumulator (fuzzy 94, overlap 32); singular/print-order variant, same course."},
    "03_btech_me-ind_y3_syllabus_2018-19::01::thermal-and-hydraulic-machines": {
        "action": "ALLOW",
        "reason": "B29 same-subject name-variant ALLOW (recorded TIER2 class): 'Thermal and Hydraulic Machines' (RME053-family print, 2018-19) -> thermal-hydraulic-machines row (fuzzy 93, overlap 75); ampersand/conjunction print variance, same course."},
    "04_btech_me-ind_y4_syllabus-cbcs_2019-20::15::advanced-welding": {
        "action": "ALLOW",
        "reason": "B29 same-subject print-variant ALLOW (recorded TIER2 class): 'Advanced Welding' (2019-20) -> advance-welding row (fuzzy 97, overlap 76); the row's establishing print carries the 'Advance Welding' typo form retained verbatim per RULES §6."},
    "07_btech_me-pe_syllabus_2009-10::36::unconventional-manufacturing-processes": {
        "action": "ALLOW",
        "reason": "B29 same-subject singular/plural ALLOW (recorded TIER2 class): 'Unconventional Manufacturing Processes' (EME-041, 2009-10) -> unconventional-manufacturing-process row (fuzzy 97, overlap 49)."},
    "07_btech_me-pe_syllabus_2009-10::41::optimisation-techniques-in-engineering": {
        "action": "ALLOW",
        "reason": "B29 same-subject ALLOW (recorded TIER2 class + B28 era-reorganization precedent): 'Optimisation Techniques in Engineering' (EME-023, 2009-10 ME-PE DE print, detailed units) -> optimization-techniques-in-chemical-engineering row (fuzzy 87, overlap 23 distinctive terms: unconstrained/multivariable optimum conditions, quasi-Newton/least-squares/Gauss-Newton, LP simplex/transportation, dynamic programming, finite-difference). The title variance ('in Engineering' vs 'in Chemical Engineering') is branch-level print variance of the same 2009-10 generic-optimization course (B7 print-variance convergence class); the ECH-021 establishing print stays as the row's name_print/history; unit reorganization recorded in change_note."},
    "07_btech_me-pe_syllabus_2009-10::42::mechanical-vibration": {
        "action": "ALLOW",
        "reason": "B29 same-subject singular/plural ALLOW (recorded TIER2 class): 'Mechanical Vibration' (EME-0xx, 2009-10) -> mechanical-vibrations row (fuzzy 98, overlap 80)."},
    "07_btech_me-pe_syllabus_2009-10::45::refrigeration-air-conditioning": {
        "action": "ALLOW",
        "reason": "B29 same-subject name-variant ALLOW (recorded TIER2 class): 'Refrigeration & Air Conditioning' (EME-0xx, 2009-10) -> refrigeration-and-air-conditioning accumulator (fuzzy 94, overlap 24)."},
    "07_btech_me-pe_syllabus_2009-10::58::management-information-system": {
        "action": "ALLOW",
        "reason": "B29 same-subject singular/plural ALLOW (recorded TIER2 class): 'Management Information System' (EME-0xx, 2009-10) -> management-information-systems row (fuzzy 98, overlap 40)."},
    "07_btech_me-pe_syllabus_2009-10::78::advanced-synthesis-of-mechanism": {
        "action": "ALLOW",
        "reason": "B29 same-subject print-variant ALLOW (recorded TIER2 class): 'Advanced Synthesis of Mechanism' (EME-0xx, 2009-10) -> advance-synthesis-of-mechanisms row (fuzzy 97, overlap 56; the row's establishing print carries the 'Advance ... Mechanisms' typo forms retained verbatim per RULES §6)."},
    "09_btech_me_syllabus_2018-19::03::ic-engines-and-compressors": {
        "action": "ALLOW",
        "reason": "B29 same-subject name-variant ALLOW (recorded TIER2 class): 'IC Engines and Compressors' (RME-05x, 2018-19) -> i-c-engines-compressors row (fuzzy 90, overlap 94 — near-verbatim unit vocabulary)."},
    "09_btech_me_syllabus_2018-19::13::refrigeration-air-conditioning": {
        "action": "ALLOW",
        "reason": "B29 same-subject name-variant ALLOW (recorded TIER2 class): 'Refrigeration and Air Conditioning' (RME-6xx, 2018-19) -> refrigeration-and-air-conditioning accumulator (fuzzy 94, overlap 24)."},
    "10_btech_me_syllabus_2020-21::16::refrigeration-air-conditioning": {
        "action": "ALLOW",
        "reason": "B29 same-subject name-variant ALLOW (recorded TIER2 class): 'Refrigeration & Air Conditioning' (KME-6xx, 2020-21) -> refrigeration-and-air-conditioning accumulator (fuzzy 94, overlap 32)."},
'''

anchor = 'TIER2_OVERRIDES = {\n'
assert anchor in src, 'anchor not found'
src = src.replace(anchor, anchor + BLOCK, 1)
open(PATH, 'w', encoding='utf-8').write(src)
import ast, sys
try:
    ast.parse(src)
    print('PATCHED: TIER2_OVERRIDES B29 block inserted; syntax OK')
except SyntaxError as e:
    print('SYNTAX ERROR:', e); sys.exit(1)
