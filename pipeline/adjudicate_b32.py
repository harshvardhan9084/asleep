#!/usr/bin/env python3
"""adjudicate_b32.py — B32 per-key adjudications (evidence-recorded, RESOLVE_APPEND class).

1. TIER2_OVERRIDES.update({...}) + DOC_SCOPE.update({...}) B32 blocks inserted
   before the __main__ guard of merge_draft.py (recorded adjudicate_b31.py
   mechanism). All 5 dry-run flags adjudicated with probe_b32_flags.py
   evidence; DOC_SCOPE zero-guess cover entries for the 7 append-bearing docs.
"""
M = '/home/z/my-project/scripts/pipeline_v2/merge_draft.py'

BLOCK = '''

# ---- B32 (CRON-20261105-B32) per-key adjudications, evidence-recorded ----
TIER2_OVERRIDES.update({
    "01_btech_open-electives_2019-20::05::renewable-energy-resources": {
        "action": "ALLOW",
        "reason": "B32 TIER2 same-subject era update STAND (recorded name-variant class): draft 'Renewable Energy Resources' (ROE086, 2019-20 Open-Electives-II print, 5 verbatim units) vs renewable-energy-sources (KAG-057;BAG057;NAG-081;KOE074, 2020-21 AG establishing): probe fullJ=0.94, per-unit 0.84-0.96, unit1 VERBATIM opening ('Introduction: Various non-conventional energy resources- Introduction, availability, classification, relative merits and demerits. Solar Cells: Theory of...') — the same renewables canon (solar, wind, biomass, geothermal, fuel cells); 'Resources'/'Sources' is the recorded singular/plural-adjacent print-variant class (B10 0.982 / B31 operation-research singular/plural). Draft 2019-20 OLDER than the row's 2020-21 session so backfill-empty only (RULES §3); ROE086 (unowned) joins as the 2019-20 OE-era code."},
    "02_btech_pe-ipe_syllabus_2020-21::26::project-management": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "project-management",
        "keep_published_codes": {"KPI072": "facility-planning-design"},
        "reason": "B32 older-draft-never-steals-a-code adjudication (recorded B19/B20 older-print guard + B29 1841 turbo-machines class): draft 'Project Management' (2020-21 PE/I-PE print, 5 verbatim units) carries an INTRA-DOC code clash — detail p.53 prints 'KPI 072' but the doc's own contents/pool print KPI 073 (clash quirk recorded by the draft). KPI072's published owner is facility-planning-design (all_codes BPI052;RMI062;KPI072): the 2021-22 PE/I-PE y4 print (this same commit's doc-07 draft: KPI072=Facility Planning and Design, KPI073=Project Management) and the 2024-25 ME-Ind scheme (B29) BOTH corroborate KPI072=Facility Planning; the 2020-21 print is OLDER than both. Ruling: UPDATE project-management by name identity (fullJ 0.46 vs the row's RAU072 2019-20 canon, u3-u5 0.51-0.64 — the era-reorganized same PM course; draft session 2020-21 newer than the row's 2019-20 so units fieldwise-win per RULES §3); KPI073 (the contents/pool print, corroborated by the 2021-22 print) joins project-management; KPI072 STAYS with facility-planning-design and the 2020-21 p.53 'KPI 072' print is recorded as a narrative history mention (dual-use slot across sessions, B19/B20 class)."},
    "04_btech_pe-ipe_y3_evaluation-scheme_2024-25::07::ergonomics-workplace-design": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "ergonomics-workplace-design",
        "keep_published_codes": {"BPI052": "facility-planning-design"},
        "reason": "B32 same-session code-slot collision keep (recorded B27 RCS653 / B29 1835 computational-fluid-dynamics class): draft 'Ergonomics & Workplace Design' (BPI052, 2024-25 PE/I-PE y3 evaluation-scheme print, 5 verbatim units). BPI052's published owner is facility-planning-design (primary BPI052, session 2024-25 — SAME session, established by the 2024-25 ME-Ind y3 evaluation-scheme print, B29): newest-print-wins cannot break a same-session tie, so the published owner keeps the code. The update lands on the name-exact ergonomics-workplace-design row (owns BPI051 — the 2024-25 ME-Ind scheme's Ergonomics code; probe fullJ=1.00, all 5 units VERBATIM-identical between the PE/I-PE and ME-Ind 2024-25 prints — the same NEP-era course printed in both branch docs); BPI052 dropped to narrative; the 2024-25 BPI052 cross-branch double print (ME-Ind Facility Planning vs PE/I-PE Ergonomics) recorded for owner reconciliation."},
    "05_btech_pe-ipe_y3_syllabus_2018-19::18::instrumentation-and-control": {
        "action": "FORCE_APPEND",
        "reason": "B32 wrong-subject FORCE_APPEND (recorded B23 sensors/transducers + B28 01::15 Modelling-and-Simulation class): draft 'INSTRUMENTATION AND CONTROL' (RPI061, 2018-19 PE/I-PE y3 DE-IV print, 5 verbatim units) fuzzy 87/4-hits instrumentation-and-process-control (ECH507;NCH-507, 2009-10 FT-family print): probe fullJ=0.02, per-unit <=0.03, only 3 generic shared terms (control, measurement, principle). The 2009-10 row is the process-control course (elements of measurement, indicating/recording instruments, process dynamics); the 2018-19 print is the basic-instrumentation course (accuracy/precision, error statistics, IEEE standards, transducers/signal conditioning). Different subjects sharing a name family; appends as its own row with a cross-reference note to instrumentation-and-process-control; RPI061 (unowned) joins it."},
    "06_btech_pe-ipe_y4_syllabus-cbcs_2019-20::02::cad-cam-lab": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "cad-cam-lab",
        "keep_published_codes": {"RME751": "computer-aided-design-manufacturing-lab"},
        "reason": "B32 same-session code-slot collision keep — EXACT REPLAY of the recorded B29 ruling on this same subject/code (04_btech_me-ind_y4_syllabus-cbcs_2019-20::02::cad-cam-lab): draft 'CAD/CAM Lab' (RME751, 2019-20 PE/I-PE y4 CBCS print, experiment list). RME751's published owner is computer-aided-design-manufacturing-lab (session 2019-20 — SAME session, 'COMPUTER AIDED DESIGN & MANUFACTURING LAB' from the 2019-20 AU-family CBCS print): same-session tie keeps the published owner. The update lands on the name-exact cad-cam-lab row (the multi-era EAU751;NAU-751;NME-751;BME652;EME-751 accumulator); RME751 dropped to narrative; the 2019-20 three-print same-code set (AU long-name / ME-Ind / PE-IPE CAD-CAM Lab) recorded for owner reconciliation."},
})
DOC_SCOPE.update({
    "3ad2353279d419ea": {
        "branch_names": "",
        "program_year": "4",
        "reason": "B32 Open-Electives 2019-20: cover p.1 prints 'Open Electives / For / Bachelor of Technology / (Choice Based Credit System) / 7th & 8th Semester, 2019-20' — NO branch names printed anywhere on the cover or pool lists, so branch_names stay BLANK per the recorded B16 zero-guess class (B31 doc-10 2009-10 science-OE precedent); program_year 4 from the printed '7th & 8th Semester' + 'B.Tech 4th year (CBCS)' pool headers."},
    "749493b449640e50": {
        "branch_names": "Production Engineering; Industrial Production Engineering",
        "program_year": "3",
        "reason": "B32 PE/I-PE 2020-21 y3: cover p.1 prints 'FOR B. TECH. 3rd YEAR Production Engineering/ Industrial Production Engineering [Effective from Session: 2020-21]'; running headers print 'PRODUCTION ENGINEERING/ INDUSTRIAL PRODUCTION ENGINEERING' (draft DOC_SCOPE quirk)."},
    "5a3056fc8c33bc06": {
        "branch_names": "Production Engineering; Industrial Production Engineering",
        "program_year": "3",
        "reason": "B32 PE/I-PE 2024-25 y3: cover p.1 prints 'EVALUATION SCHEME / FOR / B.TECH. 3rd YEAR / Production Engineering/ / Industrial Production Engineering / [Effective from Session: 2024-25]' (cover text verified from the parsed text layer)."},
    "819674f872d40b8d": {
        "branch_names": "Production Engineering; Industrial Production Engineering",
        "program_year": "3",
        "reason": "B32 PE/I-PE 2018-19 y3: cover p.1 prints 'B. Tech. 3rd Year / Production Engineering'; evaluation-scheme headers (pp.2, 17) print 'PRODUCTION ENGINEERING and INDUSTRIAL PRODUCTION' — the document serves both printed branches (draft DOC_SCOPE quirk)."},
    "2b3dc38be733f99e": {
        "branch_names": "Production Engineering; Industrial Production Engineering",
        "program_year": "4",
        "reason": "B32 PE/I-PE 2019-20 y4 CBCS: cover p.1 prints 'B. TECH 4th YEAR PRODUCTION ENGINEERING/INDUSTRIAL PRODUCTION ENGINEERING' (draft DOC_SCOPE quirk)."},
    "196c30b1f09eccf3": {
        "branch_names": "Petroleum Engineering",
        "program_year": "2",
        "reason": "B32 Petroleum y2 2017-18: cover p.1 prints 'B.Tech. Second Year / Petroleum Engineering' — single printed branch, no parenthetical expansion (draft DOC_SCOPE quirk; B31 Mining first-class-branch class)."},
    "5da3e4e52504a5cb": {
        "branch_names": "Petroleum Engineering",
        "program_year": "4",
        "reason": "B32 Petroleum y4 2017-18: cover p.1 prints 'B.Tech. Fourth Year / Petroleum Engineering' — single printed branch, no parenthetical expansion (draft DOC_SCOPE quirk; B31 Mining first-class-branch class)."},
})

'''
src = open(M).read()
if '---- B32 (CRON-20261105-B32) per-key adjudications' in src:
    print('B32 block already present; skipping insert')
else:
    guard = src.rfind("if __name__")
    assert guard > 0, 'no __main__ guard found'
    src = src[:guard] + BLOCK + '\n' + src[guard:]
    open(M, 'w').write(src)
    print('B32 adjudication blocks inserted into merge_draft.py')
