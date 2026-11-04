#!/usr/bin/env python3
"""CRON-20261104-B30 adjudications — evidence-recorded RESOLVE_APPEND entries.

Evidence passes (probe class of probe_b29_flags.py: full-vocab Jaccard +
best per-unit Jaccard on unitN_text columns + ownership probes):

1. CODE-REASSIGNED-ACROSS-SESSIONS autos — 2 stand, 1 corrected:
   - 02::09 applied-thermodynamics STANDS: EME403 transfers to
     applied-thermodynamics per the recorded B3/B02 class (newest print
     wins: the 2017-18 detail page prints EME403 on Applied Thermodynamics;
     the 2009-10 owner measurement-and-metrology content J=0.06 vs draft
     proves a different subject; draft vs applied-thermodynamics full
     J=0.66, U5 gas-turbine J=0.97 verbatim = same subject, era-reorganized
     units). RME403 (unowned 2017-18 scheme print) joins the row.
   - 04::02 cad-cam-lab CORRECTED via RETARGET_KEEP_PUBLISHED_CODE_OWNER:
     the auto's transfer would strip RME751 from computer-aided-design-
     manufacturing-lab, contradicting B29's recorded same-session ruling
     (B29 04::02: RME751 stays with computer-aided-design-manufacturing-lab,
     established by the 2019-20 ME-Ind print; newest-print-wins cannot break
     a same-session tie). The 2019-20 ME print lands on cad-cam-lab (name
     identity, 2009-10 accumulator row) as an era update; RME751 recorded
     as narrative on cad-cam-lab.
   - 04::11 automation-and-robotics CORRECTED: Tier-1 name identity hits
     the 2023-24 BOE302 open-elective row but content J=0.15 (units diverge:
     manufacturing automation/robot classification/robot drives/robot
     simulation vs industrial-automation-architecture/CIM/applications) and
     the auto's transfer would strip RME078 from robotics-and-automation
     against B29's recorded ruling (owner 2024-25 newer; older draft never
     steals a code). The 2019-20 ME DE print is a DIFFERENT-CONTENT same-name
     subject (B28 04::04 same-core-different-tail / B29 07::47 class):
     FORCE_APPEND as its own row; RME078 stripped draft-side (keeps with its
     published owner) and recorded as narrative; KMT053 (2020-21, unowned)
     joins via the 08::11 RETARGET.
2. FORCE_APPEND x2 — wrong-subject name-collision fuzzy hits:
   - 07::11 Simulation-and-Modeling EMT-011 (2010-11 Mfg-Tech DE: physical
     modeling, Monte Carlo, probability concepts, system-dynamics causal
     loops, V&V) vs modelling-and-simulation NIT062 fuzzy 98 but content
     J=0.04 (row units bioinformatics/IT); vs introduction-to-modeling-
     simulation ECH608 J=0.08 (ChemE process models); vs B29's own
     simulation-modelling-analysis RME604 row J=0.17 — same recorded class
     as B29 03::12 (name-family collision, different subject). Appends as
     its own row with cross-reference notes.
   - 07::21 Advanced-Manufacturing-Systems EMT-801 (2010-11 core:
     automation strategies, AGV/automated storage, GT, materials
     management, FMS/CIMS) vs advance-manufacturing-processes BME051 fuzzy
     85 but content J=0.05 (machining/casting/welding/forming/additive);
     no FMS/CIMS-domain row exists (probe: zero candidates >= 0.25 J).
     Appends as its own row.
3. TIER2 ALLOWs x4 stood (recorded):
   - 07::01 Work-Study-&-Ergonomics EMT-502 -> work-study-and-ergonomics
     (RMI601, 2018-19): same subject era-reworded (work study -> method
     study -> work measurement -> sampling/PMTS/wages -> ergonomics;
     fuzzy 91, 39 shared distinctive terms; low word-J is print rewording).
   - 08::07 Advance-Manufacturing-Science KPI051 -> advanced-manufacturing-
     science (RME055, 2018-19): same subject (fuzzy 98 singular/plural;
     shared advanced-machining vocabulary: EDM/ECM/wire-cut/HERF class,
     35 shared distinctive terms, era-reorganized units).
   - 08::23 Product-Design-And-Development KMT063 -> product-development-
     and-design (EME-013, 2009-10 4-branch): near-verbatim same subject
     (per-unit J 0.84-0.97, full 0.96, 111 shared terms; Introduction to
     PDD/Morphology/Transformations/Reliability/Product Appraisal).
   - 08::26 Facility-Planning-and-Design KPI072 -> facility-planning-design
     (BPI052;RMI062, 2024-25/2018-19 ME-Ind): same subject era print
     (per-unit J 0.67-0.91, full 0.84, 84 shared terms; factory planning/
     plant layout/GT/line balancing/materials handling).
4. TIE resolution: 08::11 Automation-&-Robotics KMT053 (2020-21 Mfg-Tech DE)
   TIE fuzzy 90/automation-and-robotics; 90/robotics-and-automation — both
   candidates are same-name different-content rows (J=0.17 / J=0.06; the
   robotics-and-automation row's units are the AI-DS ML-network-security
   print). The 2020-21 print shares the 2019-20 ME DE units of 04::11
   near-verbatim -> RETARGET to the row appended by 04::11
   (automation-and-robotics-btech); KMT053 (unowned) joins it; 2020-21 is
   the newer session and fieldwise-wins; both era prints accumulate in
   source_history. Never guess: the content evidence is conclusive.
5. DOC_SCOPE pre-commit for all 10 printed covers (B28R post-commit repair
   lesson) — branch_names verbatim from each cover; per-subject
   program_year already set from printed semesters (verified 0 missing).
6. Draft hygiene (B28 marker-hygiene class, doc-wide layout attested on
   p.6/p.20 page images): standalone per-unit lecture-hour digit lines
   stripped from 5 doc-07 subjects' unit texts (EMT-501 already patched at
   verify time), digits + page citation recorded per subject quirk;
   04::11 RME078 stripped to codes with keep-published quirk.
"""
import json, re, glob

MD = '/home/z/my-project/scripts/pipeline_v2/merge_draft.py'
DRAFTS = '/home/z/my-project/work/repo_asleep/pipeline/drafts_B30/'

# ---------------------------------------------------------------- 1. overrides
B30_OVERRIDES = '''
# ---- B30 (CRON-20261104-B30) per-key adjudications, evidence-recorded ----
TIER2_OVERRIDES.update({
    "02_btech_me_y2_scheme-syllabus_2017-18::09::applied-thermodynamics": {
        "action": "ALLOW",
        "reason": "B30 STAND (recorded B3/B02 code-reassigned class): Tier-1 name identity Applied Thermodynamics; draft 2017-18 carries EME403 (detail-page print) + RME403 (scheme print). EME403's published owner measurement-and-metrology (2009-10) content J=0.06 vs draft = different subject; draft vs applied-thermodynamics full J=0.66, U5 gas-turbine J=0.97 verbatim = same subject, era-reorganized units. The recorded auto transfers EME403 to the name-identity row (newest print wins; measurement-and-metrology keeps narrative history, primary follows the newest-era print status=latest model); RME403 (unowned) joins the row."},
    "04_btech_me_y4_syllabus-cbcs_2019-20::02::cad-cam-lab": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "cad-cam-lab",
        "keep_published_codes": {"RME751": "computer-aided-design-manufacturing-lab"},
        "reason": "B30 same-session code-slot keep (recorded B29 04::02 ruling): the 2019-20 ME y4 CBCS print's CAD/CAM Lab RME751 must NOT strip the code from computer-aided-design-manufacturing-lab — B29 established that the 2019-20 ME-Ind print of the SAME session owns RME751 (newest-print-wins cannot break a same-session tie). The update lands on the name-exact cad-cam-lab accumulator row (2009-10 EAU751;NAU-751;NME-751;BME652;EME-751) as a 2019-20 era backfill; RME751 recorded as narrative on cad-cam-lab; the ME-vs-ME-Ind dual print of the same session recorded for owner reconciliation."},
    "04_btech_me_y4_syllabus-cbcs_2019-20::11::automation-and-robotics": {
        "action": "FORCE_APPEND",
        "reason": "B30 wrong-subject FORCE_APPEND (recorded B28 04::04 same-core-different-tail / B29 07::47 class): Tier-1 name identity hits the 2023-24 BOE302 open-elective row automation-and-robotics but content J=0.15 — the 2019-20 ME DE-3 print's units (automation definition/laws, manufacturing automation & transfer machines, robot geometric/control classification, robot drives & power transmission, robot simulation/off-line programming) diverge from the open-elective print (industrial automation architecture, sensors, CIM, industrial applications). The auto's code transfer would also strip RME078 from robotics-and-automation against B29's recorded ruling (owner 2024-25 newer; older draft never steals a code). Appends as its own row; RME078 stripped draft-side (stays with its published owner, narrative quirk records the print); the open-elective row untouched (same name, different subject — cross-reference note)."},
    "07_btech_mfg-tech_syllabus_2010-11::01::work-study-ergonomics": {
        "action": "ALLOW",
        "reason": "B30 TIER2 same-subject era update STAND (recorded B29 RAC-class): draft Work Study & Ergonomics (EMT-502, 2010-11 E-era) vs work-study-and-ergonomics (RMI601, 2018-19 R-era ME-Ind). fuzzy 91 with 39 shared distinctive terms; the unit SEQUENCE is identical (productivity intro -> method study/charts -> work measurement/time study -> work sampling/PMTS/wages-incentives -> ergonomics) — the low word-Jaccard is E-era vs R-era print rewording, not a different subject. 2010-11 print backfills (older session, RULES §3)."},
    "07_btech_mfg-tech_syllabus_2010-11::11::simulation-and-modeling": {
        "action": "FORCE_APPEND",
        "reason": "B30 wrong-subject FORCE_APPEND (recorded B29 03::12 class, same name family): draft Simulation and Modeling (EMT-011, 2010-11 Mfg-Tech DE: physical modeling, computer-based system simulation/Monte Carlo, probability concepts in simulation, system-dynamics causal-loop/flow-diagram modeling, verification & validation). fuzzy 98 vs modelling-and-simulation (NIT062;RME076) but content J=0.04 (that row's current units are the IT/bioinformatics print); vs introduction-to-modeling-simulation (ECH608 ChemE) J=0.08; vs B29's own simulation-modelling-analysis (RME604) J=0.17 — name-family collision only, no shared model vocabulary. Appends as its own row with cross-reference notes; EMT-011 (unowned) joins it."},
    "07_btech_mfg-tech_syllabus_2010-11::21::advanced-manufacturing-systems": {
        "action": "FORCE_APPEND",
        "reason": "B30 wrong-subject FORCE_APPEND (recorded B29 07::47 class): draft Advanced Manufacturing Systems (EMT-801, 2010-11 Mfg-Tech core: automation strategies, automated storage/AGV materials handling, group technology, production economics & materials management/MPRM, FMS & CIMS). fuzzy 85 vs advance-manufacturing-processes (BME051) but content J=0.05 — that row is the machining/casting/welding/forming/additive subject. Probe found NO existing row in the FMS/CIMS domain (zero candidates >= 0.25 J across BTech). Appends as its own row; EMT-801 (unowned) joins it."},
    "08_btech_mfg-tech_syllabus_2020-21::07::advance-manufacturing-science": {
        "action": "ALLOW",
        "reason": "B30 TIER2 same-subject era update STAND (recorded B29 class): draft Advance Manufacturing Science (KPI051, 2020-21 Mfg-Tech DE) vs advanced-manufacturing-science (RME055, 2018-19). fuzzy 98 (Advance/Advanced singular-plural print variant); shared advanced-manufacturing-process vocabulary (classification, EDM/ECM-type thermal and electro-chemical removal, hybrid processes, high-energy forming) with era-reorganized unit splits — same subject, 2020-21 newer print fieldwise-wins; KPI051 (unowned) joins the row."},
    "08_btech_mfg-tech_syllabus_2020-21::11::automation-robotics": {
        "action": "RETARGET", "target": "automation-and-robotics-btech",
        "reason": "B30 TIE resolution via content evidence (never-guess satisfied: both fuzzy-90 candidates are same-name different-content rows — automation-and-robotics BOE302 J=0.17, robotics-and-automation J=0.06 whose units are the AI-DS ML-network-security print). The 2020-21 Mfg-Tech print 'Automation & Robotics' (KMT053) carries NEAR-VERBATIM the same units as the 2019-20 ME DE print appended by 04::11 (automation definition, manufacturing automation, robot classification, robot drives, robot simulation) -> RETARGET to the just-appended automation-and-robotics-btech row (same-commit visibility, recorded B22/B23 class); KMT053 (unowned) joins; 2020-21 newer session fieldwise-wins; both era prints accumulate in source_history."},
    "08_btech_mfg-tech_syllabus_2020-21::23::product-design-and-development": {
        "action": "ALLOW",
        "reason": "B30 TIER2 same-subject era update STAND: draft Product Design And Development (KMT063, 2020-21 Mfg-Tech DE) vs product-development-and-design (EME-013, 2009-10 ME/PE/IPE/ME&I 4-branch row). fuzzy 100; near-verbatim units (per-unit J 0.84-0.97, full 0.96, 111 shared distinctive terms: Introduction to PDD/Morphology of Design/Transformations/Reliability bath-tub/Product Appraisal) — same subject, 2020-21 newer print fieldwise-wins; KMT063 (unowned) joins the row."},
    "08_btech_mfg-tech_syllabus_2020-21::26::facility-planning-and-design": {
        "action": "ALLOW",
        "reason": "B30 TIER2 same-subject era update STAND: draft Facility Planning and Design (KPI072, 2020-21 Mfg-Tech DE) vs facility-planning-design (BPI052;RMI062, 2024-25 + 2018-19 ME-Ind establishing prints). fuzzy 92 with 84 shared distinctive terms; per-unit J 0.67-0.91 (factory planning/plant location, plant layout, group technology, line balancing, materials handling) — same subject, 2020-21 print backfills against the 2024-25 newer row (RULES §3 older-doc corroboration); KPI072 (unowned) joins the row."},
})
'''

# ---------------------------------------------------------------- 2. DOC_SCOPE
B30_DOC_SCOPE = '''
# ---- B30 (CRON-20261104-B30) doc-level scope from the PRINTED COVERS ----
DOC_SCOPE.update({
    "7d699e03eb1f40d3": {
        "branch_names": "Mechanical Engineering",
        "program_year": "2",
        "reason": "B30 doc01: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH 2nd YEAR MECHANICAL ENGINEERING On AICTE Model Curriculum (EFFECTIVE FROM THE SESSION: 2019-20)' — single-branch ME 2nd-year AICTE model-curriculum print; per-subject program_year set from printed semesters (3/4 -> 2)"},
    "15ccfbe9a0ef83e4": {
        "branch_names": "Mechanical Engineering;Production Engineering;Industrial & Production Engineering;Mechanical & Industrial Engineering;Manufacturing Technology;Automobile Engineering;Aeronautical Engineering",
        "program_year": "2",
        "reason": "B30 doc02: cover prints 'Study & Evaluation Scheme with Syllabus For B.Tech. Second Year (Mechanical Engineering/ Production Engineering, Industrial & Production Engineering, Mechanical & Industrial Engineering, Manufacturing Technology, Automobile Engineering, Aeronautical Engineering)' — the 7-branch ME-family y2 print; scheme rows carry the shared RME codes"},
    "6c00370d9f7d0ba5": {
        "branch_names": "Mechanical Engineering",
        "program_year": "3",
        "reason": "B30 doc03: cover prints 'EVALUATION SCHEME FOR B.TECH. 3rd YEAR MECHANICAL ENGINEERING [Effective from Session: 2024-25]' (V & VI semester B-era NEP print); per-subject program_year from printed semesters (5/6 -> 3)"},
    "56ed2e4469bcb780": {
        "branch_names": "Mechanical Engineering",
        "program_year": "4",
        "reason": "B30 doc04: cover prints 'STUDY & EVALUATION SCHEME WITH SYLLABUS FOR B. TECH 4th YEAR MECHANICAL ENGINEERING ON CHOICE BASED CREDIT SYSTEM (EFFECTIVE FROM THE SESSION: 2019-20)' (R-era CBCS Sem VII/VIII)"},
    "3cf7784768f67986": {
        "branch_names": "Mechanical Engineering",
        "program_year": "4",
        "reason": "B30 doc05: cover prints 'STUDY & EVALUATION SCHEME WITH SYLLABUS FOR B. TECH. 4th YEAR MECHANICAL ENGINEERING [Effective from Session: 2021-22]' (K-era Sem VII DE-IV/V print)"},
    "99d084e82fa37354": {
        "branch_names": "Mechanical Engineering",
        "program_year": "4",
        "reason": "B30 doc06: cover prints 'COURSE STRUCTURE/EVALUATION SCHEME FOR B.TECH. 4th YEAR MECHANICAL ENGINEERING [Effective from Session: 2025-26]' (B-era Sem VII/VIII print)"},
    "5f4df8f382ad0b54": {
        "branch_names": "Manufacturing Technology",
        "program_year": "3",
        "reason": "B30 doc07: cover prints 'Syllabus [Subjects related to Manufacturing Technology] 3rd & 4th Year [Effective from session 2010-11] B. TECH. MANUFACTURING TECHNOLOGY'; p.2 prints the note 'The Syllabus of Subjects with EME code are common to B.Tech. Mechanical Engg. course' (recorded in the draft quirks); combined 3rd-4th-year doc — per-subject program_year set from printed semesters (5/6 -> 3, 7/8 -> 4) so the single-scope fallback never mislabels (B29 me-pe class)"},
    "e441e28ab6b822d4": {
        "branch_names": "Manufacturing Technology",
        "program_year": "3",
        "reason": "B30 doc08: cover prints 'STUDY & EVALUATION SCHEME WITH SYLLABUS FOR B. TECH. 3rd YEAR Manufacturing Technology [Effective from Session: 2020-21]' (K-era KMT/KPI codes); p.47 carries a 4th-yr scheme headed 'B. Tech Manufacturing Engineering / Session 2021-22 (Yet to Finalize)' — recorded in the draft quirks as a note row, not scope"},
    "c3070c76d0529139": {
        "branch_names": "Manufacturing Technology",
        "program_year": "2",
        "reason": "B30 doc09: cover prints 'STUDY & EVALUATION SCHEME & SYLLABUS FOR B. TECH 2nd YEAR MECHANICAL ENGINEERING (Manufacturing Technology) On AICTE Model Curriculum (EFFECTIVE FROM THE SESSION: 2019-20)' — the Mfg-Tech stream of the ME 2nd-year AICTE model-curriculum print (bracketed branch); detail pages print no codes (codes from the printed scheme table, B29 doc-01 class)"},
    "60cad5443dd11e27": {
        "branch_names": "Manufacturing Technology",
        "program_year": "3",
        "reason": "B30 doc10: cover prints 'EVALUATION SCHEME FOR B.TECH. 3rd YEAR Manufacturing Technology [Effective from Session: 2024-25]' (V & VI semester B-era NEP print); BNC common codes + BME554 are scheme-row-only (B29 doc-02 class)"},
})
'''

# ---------------------------------------------------------------- 3. apply
def inject_after_last_update(src, call_name, block, marker):
    if marker in src:
        print('  (already injected)', call_name); return src
    lines = src.split('\n')
    starts = [i for i, l in enumerate(lines) if l.startswith(call_name + '.update({')]
    assert starts, call_name
    s = starts[-1]
    depth = 0
    e = None
    for i in range(s, len(lines)):
        depth += lines[i].count('{') - lines[i].count('}')
        if depth == 0 and i > s:
            e = i
            break
    assert e is not None
    lines.insert(e + 1, block)
    print('  injected after', call_name, 'block ending line', e + 1)
    return '\n'.join(lines)

src = open(MD).read()
src = inject_after_last_update(src, 'TIER2_OVERRIDES', B30_OVERRIDES, 'B30 (CRON-20261104-B30) per-key adjudications')
src = inject_after_last_update(src, 'DOC_SCOPE', B30_DOC_SCOPE, 'B30 (CRON-20261104-B30) doc-level scope')
open(MD, 'w').write(src)

# ---------------------------------------------------------------- 4. draft patches
def py_from_sem(sem):
    try:
        s = int(sem)
    except (TypeError, ValueError):
        return None
    return {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4}.get(s)

npy = nc = nq = nd = 0
for f in sorted(glob.glob(DRAFTS + '*.draft.json')):
    d = json.load(open(f))
    stem = d['stem']
    for idx, s in enumerate(d['subjects']):
        py = py_from_sem(s.get('semester'))
        if py and not s.get('program_year'):
            s['program_year'] = py; npy += 1
        # 04::11: strip RME078 (keep-published; B29 ruling) + quirk
        if stem.startswith('04_btech_me_y4_syllabus-cbcs') and idx == 11:
            codes = s.get('codes') or []
            if any(norm == 'RME078' for norm in [re.sub(r'[^A-Z0-9]', '', c.upper()) for c in codes]):
                s['codes'] = [c for c in codes if re.sub(r'[^A-Z0-9]', '', c.upper()) != 'RME078']
                s.setdefault('quirks', []).append(
                    "patch-b30: the printed code RME078 (2019-20 ME DE-3 scheme, p.8 pool print) is NOT "
                    "claimed by this row — it stays owned by robotics-and-automation per the recorded B29 "
                    "04::13 keep-published-owner ruling (owner 2024-25 newer; older draft never steals a "
                    "code); the print is preserved in this quirk and in the row notes as a narrative "
                    "history mention; the 2023-24 BOE302 open-elective row of the same name is a different "
                    "subject (content J=0.15) and is left untouched (cross-reference).")
                nc += 1
        # doc-07: strip standalone per-unit lecture-hour digit lines (5 subjects)
        if stem.startswith('07_btech_mfg-tech_syllabus') and idx in (6, 11, 15, 16, 23):
            moved = {}
            for uk, ut in list((s.get('units') or {}).items()):
                lines = ut.split('\n')
                digs = [l.strip() for l in lines if re.fullmatch(r'\s*\d{1,3}\s*', l)]
                if digs:
                    moved[uk] = digs
                    s['units'][uk] = '\n'.join(l for l in lines if re.fullmatch(r'\s*\d{1,3}\s*', l) is None).strip()
            if moved:
                s.setdefault('quirks', []).append(
                    "patch-b30: the per-unit lecture-hour digits (" +
                    ", ".join(f"U{uk}: {'/'.join(v)}" for uk, v in sorted(moved.items())) +
                    ") print as separate column values between unit headings and bodies in this E-era "
                    "print (doc-wide layout; p.6/p.20 page-image attested, visible print authoritative "
                    "RULES §6) — moved to this quirk, unit texts kept verbatim-only (B28 doc-04 "
                    "marker-hygiene class).")
                nd += 1
    json.dump(d, open(f, 'w'), indent=1, ensure_ascii=False)
print(f'draft patches: program_year {npy}, RME078 strip {nc}, doc-07 digit strips {nd}')
print('DONE')
