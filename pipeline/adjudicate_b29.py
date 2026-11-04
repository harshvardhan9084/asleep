#!/usr/bin/env python3
"""CRON-20261104-B29 adjudications — evidence-recorded RESOLVE_APPEND entries.

Three evidence passes (probe_b29_flags.py + per-unit Jaccard probes):
1. FORCE_APPEND ×3 — wrong-subject fuzzy hits (B28 01::15 class):
   - 03::12 Simulation-Modelling-&-Analysis (RME604, ME-Ind) vs IT modelling-and-simulation J=0.18/best 0.22
   - 07::47 Optimisation-Techniques-in-Engineering (EME-023, ME) vs ChemE optimization-techniques-in-chemical-engineering J=0.18/best 0.26
   - 07::72 Fundamentals-of-Biomedical-Engineering (EME-066, ME) vs fundamentals-of-electrical-engineering J=0.03/best 0.06
2. RETARGET ×3 — verbatim-identity joins (B23 REE070 / B28 NEC408 class):
   - 02::07 I-C-Engine-Fuel-&-Lubrication BME052 -> i-c-engine-fuels-lubrication (best-unit J=1.00)
   - 02::10 Mechatronic-Systems BME054 -> mechatronics-systems (best-unit J=0.98, singular/plural print variant)
   - 06::04 Total-Quality-Management BPI062 -> total-quality-management-tqm (best-unit J=1.00; TIE resolved)
3. RETARGET_KEEP_PUBLISHED_CODE_OWNER ×9 — same-session (B27 RCS653 class) or
   older-print (B21/B28R class) code-slot collisions:
   - 02::11 CFD BME055 stays with turbo-machines (same-session 2024-25)
   - 02::21 Turbo-Machines BME062 stays with computational-fluid-dynamics (owner 2025-26 newer)
   - 04::02 CAD/CAM-Lab RME751 stays with computer-aided-design-manufacturing-lab (same-session 2019-20)
   - 04::13 Automation-and-Robotics RME078 stays with robotics-and-automation (owner 2024-25 newer)
   - 07::61/62/63/67/68 EME051/052/053/061/062 stay with their 2009-10 published owners (same-session)
STAND (recorded, no override): 02::03 heat-transfer-lab BME551 newest-print name-identity
transfer (draft 2024-25 > owner 2020-21); 04::00 CAD/CAM RME701 append+transfer (draft 2019-20
> establishing 2009-10, B10 class); 10 TIER2 same-subject era updates (RAC ×4, THM, welding,
UMP, MV, MIS, ASM).

Also: DOC_SCOPE entries for the 10 printed covers (B28R post-commit repair lesson)
and per-subject program_year derivation (semester -> year, zero-guess structure).
"""
import json, re, io

MD = '/home/z/my-project/scripts/pipeline_v2/merge_draft.py'
DRAFTS = '/home/z/my-project/work/pipeline_v2/drafts/B29/'

# ---------------------------------------------------------------- 1. overrides
B29_OVERRIDES = '''    # ---- B29 (CRON-20261104-B29) per-key adjudications, evidence-recorded ----
    "03_btech_me-ind_y3_syllabus_2018-19::12::simulation-modelling-analysis": {
        "action": "FORCE_APPEND",
        "reason": "B29 wrong-subject FORCE_APPEND (recorded B28 01::15 Modelling-and-Simulation class): draft 'Simulation Modelling & Analysis' (RME604, 2018-19 ME-Ind y3 elective, 5 verbatim units: system modelling concepts, random variates, queuing, DES languages, Petri-nets) fuzzy 87/26-hits modelling-and-simulation (NIT062, 2015-16 Information-Technology row: IT systems-simulation). probe: full-vocab J=0.18, best per-unit J=0.22, zero shared model vocabulary (IT GPSS/Java-simulation vs ME manufacturing/queuing) — different programs print different courses under a similar name. Appends as its own row with a cross-reference note to the IT row; zero-GAP holds."},
    "07_btech_me-pe_syllabus_2009-10::47::optimisation-techniques-in-engineering": {
        "action": "FORCE_APPEND",
        "reason": "B29 wrong-subject FORCE_APPEND (recorded B28 01::15 class): draft 'OPTIMISATION TECHNIQUES IN ENGINEERING' (EME-023, 2009-10 ME elective, 5 verbatim units: LP simplex, transportation, assignment, sequencing, network CPM/PERT) fuzzy 87/23-hits optimization-techniques-in-chemical-engineering (ECH021, 2009-10 CHEMICAL Engineering row: chem-flow-sheet optimization). probe: J=0.18, best per-unit 0.26, different program scope (ME generic-OR vs ChemE process) — same recorded wrong-subject class as the ChemE process-modelling vs IT systems-simulation pair. Appends as its own row with a cross-reference note; zero-GAP holds."},
    "07_btech_me-pe_syllabus_2009-10::72::fundamentals-of-biomedical-engineering": {
        "action": "FORCE_APPEND",
        "reason": "B29 wrong-subject FORCE_APPEND (recorded B28 01::15/B27 08::03 class): draft 'FUNDAMENTALS OF BIOMEDICAL ENGINEERING' (EME-066, 2009-10 ME elective, 5 verbatim units: human physiology, bioelectric phenomena, biomaterials, medical instrumentation, rehabilitation) fuzzy 87/6-hits fundamentals-of-electrical-engineering (AEE101B/BEE101 2026-27 first-year row: circuits, machines). probe: J=0.03, best per-unit 0.06 — token 'fundamentals-of-X-engineering' name collision only, content is a DIFFERENT subject. Appends as its own row with a cross-reference note; zero-GAP holds."},
    "02_btech_me-ind_y3_evaluation-scheme_2024-25::07::i-c-engine-fuel-lubrication": {
        "action": "RETARGET", "target": "i-c-engine-fuels-lubrication",
        "reason": "B29 verbatim-identity RETARGET (recorded B23 REE070 / B28 NEC408 class): draft 'I C Engine Fuel & Lubrication' (BME052, 2024-25 ME-Ind y3 print, 5 verbatim units). probe: i-c-engine-fuels-lubrication (KME054;BME054, 2020-21 establishing print) best per-unit J=1.00 VERBATIM — the 2024-25 print is the SAME subject with a punctuation/plural print variant; appending a second I.C.-Engine row would duplicate the subject (RULES §11). BME052 transfers from mechatronics-systems (its 2020-21-era published owner, older than this print) to the canon row; units fieldwise-win (2024-25 newer)."},
    "02_btech_me-ind_y3_evaluation-scheme_2024-25::10::mechatronic-systems": {
        "action": "RETARGET", "target": "mechatronics-systems",
        "reason": "B29 verbatim-identity RETARGET (B28 NEC408 class + recorded singular/plural name-variant ALLOW): draft 'Mechatronic Systems' (BME054, 2024-25 ME-Ind y3 print, 5 verbatim units: sensors/actuators, modeling, controllers, DAQ, case studies). probe: mechatronics-systems (KME052;BME052, 2020-21) best per-unit J=0.98, full J=0.88 — SAME subject, singular print variant; no name-exact row exists because norm_name keeps the plural 's'. BME054 transfers from i-c-engine-fuels-lubrication (older published owner) to the canon row; units fieldwise-win."},
    "06_btech_me-ind_y4_syllabus_2025-26::04::total-quality-management": {
        "action": "RETARGET", "target": "total-quality-management-tqm",
        "reason": "B29 TIE resolution, verbatim-identity RETARGET (B23 REE070 / B28 NEC408 class): draft 'Total Quality Management' (BPI062, 2025-26 ME-Ind y4 DE print, 5 verbatim units). TIE candidates: total-quality-management-tqm (NME-041, 2016-17 ME-Ind-family row — best per-unit J=1.00 VERBATIM, same branch scope) vs quality-management (NOE072;EOE-072, 2016-17 Civil open-elective row — best per-unit 0.92 on generic quality vocabulary, different program, different name). The verbatim-identical same-family row is the subject's canon; BPI062 joins it as the 2025-26 era code; the Civil quality-management row is untouched (different subject, cross-reference note only)."},
    "02_btech_me-ind_y3_evaluation-scheme_2024-25::11::computational-fluid-dynamics": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "computational-fluid-dynamics",
        "keep_published_codes": {"BME055": "turbo-machines"},
        "reason": "B29 same-session code-slot collision keep (recorded B27 RCS653 / B28R 06::18 NGP-301 class): draft 'Computational Fluid Dynamics' (BME055, 2024-25 ME-Ind y3 print, 5 verbatim units). BME055's published owner is turbo-machines (session 2024-25 — SAME session, established by another 2024-25 y3 scheme that prints BME055 = Turbo Machines): newest-print-wins cannot break a same-session tie, so the published owner keeps the code. The update lands on the name-exact computational-fluid-dynamics row (2024-25 print backfills against its 2025-26 content); BME055 dropped to narrative; the AKTU same-session slot split recorded for owner reconciliation."},
    "02_btech_me-ind_y3_evaluation-scheme_2024-25::21::turbo-machines": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "turbo-machines",
        "keep_published_codes": {"BME062": "computational-fluid-dynamics"},
        "reason": "B29 keep-published-owner (recorded B21 older-print guard / B28R 02::04 NOE-075 class): draft 'Turbo Machines' (BME062, 2024-25 ME-Ind y3 print, 5 verbatim units). BME062's published owner is computational-fluid-dynamics (session 2025-26 — NEWER than the draft; a 2025-26 scheme prints BME062 = CFD): an equal-or-older print never takes a code from its newer-session published owner. The update lands on the name-exact turbo-machines row (same-session 2024-25 corroboration of its 2024-25 units); BME062 dropped to narrative; the across-session slot split recorded for owner reconciliation."},
    "04_btech_me-ind_y4_syllabus-cbcs_2019-20::02::cad-cam-lab": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "cad-cam-lab",
        "keep_published_codes": {"RME751": "computer-aided-design-manufacturing-lab"},
        "reason": "B29 same-session code-slot collision keep (B27 RCS653 class): draft 'CAD/CAM Lab' (RME751, 2019-20 ME-Ind y4 CBCS print, experiment list). RME751's published owner is computer-aided-design-manufacturing-lab (session 2019-20 — SAME session, 'COMPUTER AIDED DESIGN & MANUFACTURING LAB' from the 2019-20 AU-family CBCS print): same-session tie keeps the published owner. The update lands on the name-exact cad-cam-lab row; RME751 dropped to narrative; the same-session same-code cross-branch print pair recorded for owner reconciliation."},
    "04_btech_me-ind_y4_syllabus-cbcs_2019-20::13::automation-and-robotics": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "automation-and-robotics",
        "keep_published_codes": {"RME078": "robotics-and-automation"},
        "reason": "B29 keep-published-owner (recorded B21 older-print guard / B28R NOE-075 class): draft 'Automation and Robotics' (RME078, 2019-20 ME-Ind y4 DE print, 5 verbatim units). RME078's published owner is robotics-and-automation (KAD073;EAU013;RME078, session 2024-25 — NEWER): an equal-or-older print never takes a code from its newer-session published owner. The update lands on the name-exact automation-and-robotics row (2019-20 print backfills/corroborates); RME078 dropped to narrative; the Robotics-and-Automation vs Automation-and-Robotics name pair and the AKTU slot re-use recorded for owner reconciliation."},
    "07_btech_me-pe_syllabus_2009-10::61::operations-research": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "operations-research",
        "keep_published_codes": {"EME051": "computer-aided-vehicle-design"},
        "reason": "B29 same-session code-slot collision keep (B27 RCS653 class): draft 'OPERATIONS RESEARCH' (EME-051, 2009-10 ME elective-VIII print, 5 verbatim units). EME051's published owner is computer-aided-vehicle-design (EAU051;EME051, session 2009-10 — SAME session, established by the 2009-10 AU print): same-session tie keeps the published owner. The update lands on the name-exact operations-research row; EME051 dropped to narrative; the 2009-10 EME-051 cross-branch double print (AU CAVD vs ME Operations-Research) recorded for owner reconciliation."},
    "07_btech_me-pe_syllabus_2009-10::62::maintenance-engineering-management": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "maintenance-engineering-management",
        "keep_published_codes": {"EME052": "alternative-energy-sources-for-automobiles"},
        "reason": "B29 same-session code-slot collision keep (B27 RCS653 class; same evidence pattern as 07::61): draft 'MAINTENANCE ENGINEERING & MANAGEMENT' (EME-052, 2009-10 ME elective print, 5 verbatim units). EME052's published owner is alternative-energy-sources-for-automobiles (EAU052;EME052;RAU082;NAU-052, session 2009-10 — SAME session): the published owner keeps the code; the update lands on the name-exact maintenance-engineering-management row; collision recorded for owner reconciliation."},
    "07_btech_me-pe_syllabus_2009-10::63::design-of-thermal-systems": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "design-of-thermal-systems",
        "keep_published_codes": {"EME053": "vehicle-dynamics"},
        "reason": "B29 same-session code-slot collision keep (B27 RCS653 class; same evidence pattern as 07::61): draft 'DESIGN OF THERMAL SYSTEMS' (EME-053, 2009-10 ME elective print, 5 verbatim units). EME053's published owner is vehicle-dynamics (EAU053;EME053;RAU061;NAU-053, session 2009-10 — SAME session): the published owner keeps the code; the update lands on the name-exact design-of-thermal-systems row; collision recorded for owner reconciliation."},
    "07_btech_me-pe_syllabus_2009-10::67::finite-element-method": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "finite-element-method",
        "keep_published_codes": {"EME061": "computer-simulation-of-ic-engines-process"},
        "reason": "B29 same-session code-slot collision keep (B27 RCS653 class; same evidence pattern as 07::61): draft 'FINITE ELEMENT METHOD' (EME-061, 2009-10 ME elective print, 5 verbatim units). EME061's published owner is computer-simulation-of-ic-engines-process (EAU061;EME061;EME062;NAU-061, session 2009-10 — SAME session): the published owner keeps the code; the update lands on the name-exact finite-element-method row (the 6-branch FEM accumulator); collision recorded for owner reconciliation."},
    "07_btech_me-pe_syllabus_2009-10::68::non-destructive-testing": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "non-destructive-testing",
        "keep_published_codes": {"EME062": "computer-simulation-of-ic-engines-process"},
        "reason": "B29 same-session code-slot collision keep (B27 RCS653 class; same evidence pattern as 07::61): draft 'NON-DESTRUCTIVE TESTING' (EME-062, 2009-10 ME elective print, 5 verbatim units). EME062's published owner is computer-simulation-of-ic-engines-process (session 2009-10 — SAME session): the published owner keeps the code; the update lands on the name-exact non-destructive-testing row; collision recorded for owner reconciliation."},
'''

src = open(MD).read()
if 'B29 (CRON-20261104-B29) per-key adjudications' in src:
    print('overrides already present — skip')
else:
    lines = src.split('\n')
    # insert before the closing '}' of TIER2_OVERRIDES (line 1764, 1-based)
    assert lines[1763] == '}', f"unexpected line 1764: {lines[1763]!r}"
    lines.insert(1763, B29_OVERRIDES.rstrip('\n'))
    open(MD, 'w').write('\n'.join(lines))
    print('overrides inserted before line 1764')

# ---------------------------------------------------------------- 2. DOC_SCOPE
B29_SCOPE = '''
# ---- B29 DOC_SCOPE (CRON-20261104-B29; branch scope from each ingested document's
# PRINTED COVER, zero-guess; added pre-commit per the recorded B28R post-commit repair
# lesson: merges without DOC_SCOPE leave appended rows with empty branch_names) ----
DOC_SCOPE.update({
    "5e14dc3f12ac04a3": {
        "branch_names": "Mechanical Engineering (Mechanical and Industrial Engineering)",
        "program_year": "2",
        "reason": "B29 ME-Ind y2 model-curriculum 2019-20: cover prints 'STUDY & EVALUATION SCHEME & SYLLABUS FOR B. TECH 2nd YEAR MECHANICAL ENGINEERING (Mechanical and Industrial Engineering) On AICTE Model Curriculum (Effective from the session 2019-20)'"},
    "9c81bf6940829c7d": {
        "branch_names": "Mechanical and Industrial Engineering",
        "program_year": "3",
        "reason": "B29 ME-Ind y3 evaluation-scheme 2024-25: cover prints 'EVALUATION SCHEME FOR B.TECH. 3rd YEAR MECHANICAL AND INDUSTRIAL ENGINEERING [Effective from Session: 2024-25]'"},
    "df5b69780b912bb8": {
        "branch_names": "Mechanical and Industrial Engineering",
        "program_year": "3",
        "reason": "B29 ME-Ind y3 syllabus 2018-19: cover prints 'EVALUATION SCHEME & SYLLABUS For B. Tech. 3rd Year MECHANICAL AND INDUSTRIAL ENGINEERING ON CHOICE BASED CREDIT SYSTEM (CBCS) [Effective from session 2018-19]'"},
    "818c56493dfa2d0f": {
        "branch_names": "Mechanical & Industrial Engineering",
        "program_year": "4",
        "reason": "B29 ME-Ind y4 CBCS 2019-20: cover prints 'STUDY & EVALUATION SCHEME WITH SYLLABUS FOR B. TECH 4th YEAR MECHANICAL & INDUSTRIAL ENGINEERING ON CHOICE BASED CREDIT SYSTEM (EFFECTIVE FROM THE SESSION: 2019-20)'"},
    "a664da8df2b68ed7": {
        "branch_names": "Mechanical & Industrial Engineering",
        "program_year": "4",
        "reason": "B29 ME-Ind y4 2021-22: cover prints 'STUDY & EVALUATION SCHEME WITH SYLLABUS FOR B. TECH. 4th YEAR MECHANICAL & INDUSTRIAL ENGINEERING [Effective from Session: 2021-22]'"},
    "72ffdc4ec8f31053": {
        "branch_names": "Mechanical and Industrial Engineering",
        "program_year": "4",
        "reason": "B29 ME-Ind y4 2025-26: cover prints 'COURSE STRUCTURE/EVALUATION SCHEME FOR B.TECH. 4th YEAR MECHANICAL AND INDUSTRIAL ENGINEERING [Effective from Session: 2025-26]'"},
    "c46b141f3ee05115": {
        "branch_names": "Mechanical Engineering;Production Engineering;Industrial & Production Engineering;Mechanical & Industrial Engineering",
        "program_year": "2",
        "reason": "B29 ME-PE 2009-10 (2nd-4th year combined): cover prints 'Syllabus 2nd, 3rd and 4th Year [Effective from session 2009-10] — 1. B. Tech. Mechanical Engineering 2. B. Tech. Production Engineering 3. B. Tech. Industrial & Production Engineering 4. B. Tech. Mechanical & Industrial Engineering'; per-subject program_year set from the printed semester (2/3/4) so the single-scope fallback never mislabels"},
    "4514084f982fc59e": {
        "branch_names": "Mechanical Engineering;Automobile Engineering;Aeronautical Engineering;Industrial Production Engineering;Manufacturing Technology;Mining Engineering",
        "program_year": "1",
        "reason": "B29 ME course-structure 2026-27: cover prints 'EVALUATION SCHEME & SYLLABUS of B. TECH. First Year ME STREAM (Mechanical Engineering, Automobile Engineering, Aeronautical Engineering, Industrial Production Engineering, Manufacturing Technology, Mining Engineering)'"},
    "b4463c0a5bda685f": {
        "branch_names": "Mechanical Engineering",
        "program_year": "3",
        "reason": "B29 ME y3 2018-19: cover prints 'B. Tech. Syllabus for Mechanical Engineering Third Year (Effective from the Session: 2018-19)'"},
    "be2a8d8948a6c2d6": {
        "branch_names": "Mechanical Engineering",
        "program_year": "3",
        "reason": "B29 ME y3 2020-21: cover prints 'STUDY & EVALUATION SCHEME WITH SYLLABUS FOR B. TECH. 3rd YEAR MECHANICAL ENGINEERING [Effective from Session: 2020-21]' (garbled text layer; visible-print reconstruction recorded in the draft quirks)"},
})
'''
src = open(MD).read()
if 'B29 DOC_SCOPE' in src:
    print('DOC_SCOPE already present — skip')
else:
    anchor = 'def ladder(dsub, rows, course, draft_session=""):'
    assert anchor in src
    src = src.replace(anchor, B29_SCOPE + '\n' + anchor, 1)
    open(MD, 'w').write(src)
    print('DOC_SCOPE inserted before ladder()')

# ---------------------------------------------------------------- 3. draft patches
# 3a. program_year from printed semester (zero-guess AKTU structure: sem 1-2=y1,
#     3-4=y2, 5-6=y3, 7-8=y4); 3b. collision-narrative quirks for the 9 keeps.
QUIRKS = {
    ('02_btech_me-ind_y3_evaluation-scheme_2024-25', 11):
        "Code-slot collision: the 2024-25 ME-Ind scheme prints BME055 on this subject, but BME055's published owner is turbo-machines (SAME session 2024-25, established by another 2024-25 y3 scheme printing BME055 = Turbo Machines) — same-session tie keeps the published owner (B27 RCS653 class); this print's CFD content lands on the name-exact computational-fluid-dynamics row and BME055 is recorded here as narrative for owner reconciliation.",
    ('02_btech_me-ind_y3_evaluation-scheme_2024-25', 21):
        "Code-slot collision: the 2024-25 ME-Ind scheme prints BME062 on this subject, but BME062's published owner is computational-fluid-dynamics (session 2025-26, NEWER — a 2025-26 scheme prints BME062 = CFD); an equal-or-older print never takes a code from its newer-session published owner (B21/B28R class); this print's Turbo Machines content corroborates the name-exact turbo-machines row and BME062 is recorded here as narrative for owner reconciliation.",
    ('04_btech_me-ind_y4_syllabus-cbcs_2019-20', 2):
        "Code-slot collision: the 2019-20 ME-Ind y4 CBCS scheme prints RME751 on this subject, but RME751's published owner is computer-aided-design-manufacturing-lab (SAME session 2019-20, 'COMPUTER AIDED DESIGN & MANUFACTURING LAB', AU-family CBCS print) — same-session tie keeps the published owner (B27 RCS653 class); this print's lab content lands on the name-exact cad-cam-lab row and RME751 is recorded here as narrative for owner reconciliation.",
    ('04_btech_me-ind_y4_syllabus-cbcs_2019-20', 13):
        "Code-slot collision: the 2019-20 ME-Ind y4 CBCS scheme prints RME078 on this subject, but RME078's published owner is robotics-and-automation (session 2024-25, NEWER — KAD073;EAU013;RME078); an equal-or-older print never takes a code from its newer-session published owner (B21/B28R class); this print's content lands on the name-exact automation-and-robotics row and RME078 is recorded here as narrative for owner reconciliation (Robotics-and-Automation vs Automation-and-Robotics name pair noted).",
    ('07_btech_me-pe_syllabus_2009-10', 61):
        "Code-slot collision: the 2009-10 ME-PE scheme prints EME-051 on this subject, but EME051's published owner is computer-aided-vehicle-design (SAME session 2009-10, EAU051;EME051) — same-session tie keeps the published owner (B27 RCS653 class); this print's Operations Research content lands on the name-exact operations-research row and EME051 is recorded here as narrative for owner reconciliation.",
    ('07_btech_me-pe_syllabus_2009-10', 62):
        "Code-slot collision: the 2009-10 ME-PE scheme prints EME-052 on this subject, but EME052's published owner is alternative-energy-sources-for-automobiles (SAME session 2009-10, EAU052;EME052;RAU082;NAU-052) — same-session tie keeps the published owner (B27 RCS653 class); this print's Maintenance Engineering & Management content lands on the name-exact row and EME052 is recorded here as narrative for owner reconciliation.",
    ('07_btech_me-pe_syllabus_2009-10', 63):
        "Code-slot collision: the 2009-10 ME-PE scheme prints EME-053 on this subject, but EME053's published owner is vehicle-dynamics (SAME session 2009-10, EAU053;EME053;RAU061;NAU-053) — same-session tie keeps the published owner (B27 RCS653 class); this print's Design of Thermal Systems content lands on the name-exact row and EME053 is recorded here as narrative for owner reconciliation.",
    ('07_btech_me-pe_syllabus_2009-10', 67):
        "Code-slot collision: the 2009-10 ME-PE scheme prints EME-061 on this subject, but EME061's published owner is computer-simulation-of-ic-engines-process (SAME session 2009-10, EAU061;EME061;EME062;NAU-061) — same-session tie keeps the published owner (B27 RCS653 class); this print's FEM content lands on the name-exact finite-element-method row and EME061 is recorded here as narrative for owner reconciliation.",
    ('07_btech_me-pe_syllabus_2009-10', 68):
        "Code-slot collision: the 2009-10 ME-PE scheme prints EME-062 on this subject, but EME062's published owner is computer-simulation-of-ic-engines-process (SAME session 2009-10) — same-session tie keeps the published owner (B27 RCS653 class); this print's NDT content lands on the name-exact non-destructive-testing row and EME062 is recorded here as narrative for owner reconciliation.",
}
def py_from_sem(sem):
    try:
        s = int(sem)
    except (TypeError, ValueError):
        return None
    return {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4}.get(s)

import glob, os
npy = nq = 0
for f in sorted(glob.glob(DRAFTS + '*.draft.json')):
    d = json.load(open(f))
    stem = d['stem']
    for idx, s in enumerate(d['subjects']):
        py = py_from_sem(s.get('semester'))
        if py and not s.get('program_year'):
            s['program_year'] = py
            npy += 1
        q = QUIRKS.get((stem, idx))
        if q:
            ql = s.setdefault('quirks', [])
            if q not in ql:
                ql.append(q)
                nq += 1
    json.dump(d, open(f, 'w'), indent=1, ensure_ascii=False)
print(f'draft patches: program_year set on {npy} subjects, {nq} collision quirks added')
print('DONE')
