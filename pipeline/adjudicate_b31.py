#!/usr/bin/env python3
"""adjudicate_b31.py — B31 per-key adjudications (evidence-recorded, RESOLVE_APPEND class).

1. Patch drafts 01::01 / 01::15 (slash-separated scheme slot prints) with the
   recorded alternative_pair_row flag + scheme-row-citing quirk (B28 doc-03/06
   class) so the ALTERNATIVE-PAIR-SLOT executor skips them (both member rows
   own the printed codes: RAS502/RAS602 -> sociology-cyber-security,
   RUC501/RUC601 -> cyber-security).
2. Insert TIER2_OVERRIDES.update({...}) + DOC_SCOPE.update({...}) B31 blocks
   before the __main__ guard of merge_draft.py.
"""
import json

D = '/home/z/my-project/work/pipeline_v2/drafts/'
M = '/home/z/my-project/scripts/pipeline_v2/merge_draft.py'

# ---- 1. alt-pair draft patches ---------------------------------------------
for idx, name in ((1, 'SOCIOLOGY / CYBER SECURITY'), (15, 'CYBER SECURITY/ SOCIOLOGY')):
    p = D + '01_btech_mfg-tech_y3_syllabus_2018-19.draft.json'
    d = json.load(open(p))
    s = d['subjects'][idx]
    assert s['name'] == name, (idx, s['name'])
    fl = s.setdefault('flags', [])
    tag = 'alternative_pair_row'
    if tag not in fl:
        fl.append(tag)
    s.setdefault('quirks', []).append(
        'slash-separated scheme slot print (2018-19 Mfg-Tech y3 scheme table): the slot row names '
        'TWO subjects whose registry rows already own the printed codes — '
        'RAS502/RAS602 are owned by sociology-cyber-security (primary RAS502), '
        'RUC501/RUC601 are owned by cyber-security (all_codes BCC301;BCC401;KNC301;BCC301H;BCC401H;RUC501;RUC601;AUC-002); '
        'no syllabus units/COs printed for the slot in this document (scheme-row-only) — '
        'program-structure slot print, not a subject (recorded B28 alternative-pair class)')
    json.dump(d, open(p, 'w'), indent=1, ensure_ascii=False)
    print(f'patched 01::{idx:02d} {name!r} with alternative_pair_row')

# ---- 2. merge_draft.py blocks ----------------------------------------------
BLOCK = '''

# ---- B31 (CRON-20261104-B31) per-key adjudications, evidence-recorded ----
TIER2_OVERRIDES.update({
    "01_btech_mfg-tech_y3_syllabus_2018-19::03::manufacturing-science-and-technology-ii": {
        "action": "RETARGET", "target": "manufacturing-science-technology-ii",
        "reason": "B31 TIE resolution on name-family + content evidence: draft 'Manufacturing Science and Technology II' (RME505, 2018-19 Mfg-Tech y3, 5 verbatim units) TIEs fuzzy 93/manufacturing-science-technology-i (NME402;RME402) vs 95/manufacturing-science-technology-ii (RME503, sess 2018-19). The II token is the subject's own print — merging II into I would violate the recorded distinct-row design (MST-I/MST-II are separate courses, cf. electro-mechanical-energy-conversion-i/ii); the probe: draft vs MST-II fullJ=0.38 (U1 0.63, U5 0.51 — era-reorganized same course) vs MST-I fullJ=0.10. RETARGET pins MST-II; RME505 (unowned) joins as the 2018-19 Mfg-Tech era code; the SAME-SESSION dual-print (ME-Ind RME503 establishing print vs Mfg-Tech RME505 print, units fieldwise per the >= rule) is recorded here for owner reconciliation (B27 RCS653 same-session class narrative)."},
    "01_btech_mfg-tech_y3_syllabus_2018-19::04::advance-welding-technology": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND: draft 'Advance Welding Technology' (RME506, 2018-19 Mfg-Tech y3, 4 units — no Unit-V printed) vs advanced-welding-technology row: probe sim 0.98, fullJ=0.99 (unitJ 0.97-1.0) — VERBATIM same subject ('Advance'/'Advanced' print variant, recorded B10 0.982 class). RME506 (unowned) joins; 2018-19 row session fieldwise."},
    "01_btech_mfg-tech_y3_syllabus_2018-19::09::advance-casting-process": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND: draft 'Advance Casting Process' (RMT051, 2018-19 Mfg-Tech y3, 5 verbatim units) vs advanced-casting-processes (EMT-012, 2010-11 establishing print): probe fullJ=1.0, per-unit all 1.0 — VERBATIM; 2018-19 newer so units fieldwise-win (B10 'ADVANCE/ADVANCED' 0.982 print-variant class). RMT051 (unowned) joins."},
    "01_btech_mfg-tech_y3_syllabus_2018-19::10::plastic-material-and-manufacturing": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND: draft 'Plastic Material and Manufacturing' (RMT052, 2018-19 Mfg-Tech y3, 5 verbatim units) vs plastic-materials-manufacturing (KMT051, 2020-21 establishing): probe fullJ=0.99 (per-unit 0.94-1.0) — verbatim modulo singular/plural + '&'/'and' print variance (recorded name-variant class); draft 2018-19 OLDER so backfill-empty only (RULES §3). RMT052 (unowned) joins."},
    "01_btech_mfg-tech_y3_syllabus_2018-19::16::pneumatics-and-hydraulics": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND: draft 'Pneumatics and Hydraulics' (RMT601, 2018-19 Mfg-Tech y3, 5 verbatim units) vs pneumatics-hydraulics (EMT-601, 2010-11 establishing): probe fullJ=0.99 (per-unit 0.95-1.0) — verbatim era print; 2018-19 newer so units fieldwise-win. The competing pneumatics-hydraulics-lab hit (J=0.0) is the recorded distinct-lab-row design (labs are separate rows, RULES §3) and stays untouched. RMT601 (unowned) joins."},
    "01_btech_mfg-tech_y3_syllabus_2018-19::18::production-planning-and-control": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND: draft 'Production Planning and Control' (RMT602, 2018-19 Mfg-Tech y3, 4 units — no Unit-V printed) vs production-planning-control (EPI-501, 2009-10 establishing): probe unit1 J=0.81 with the SAME opening sentence ('Introduction: Types and characteristics of production systems Objective and functions of Production, Planning & Control'); 6 shared distinctive terms (capacity, forecasting, inventory, layout, MRP, scheduling) — the 2018-19 print is the era-reorganized same PPC course (B30 facility-planning class); 2018-19 newer so units fieldwise-win. RMT602 (unowned) joins."},
    "01_btech_mfg-tech_y3_syllabus_2018-19::24::product-design-and-development": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND (recorded B30 08::23 ruling on this exact pair): draft 'Product Design and Development' (RMT061, 2018-19 Mfg-Tech y3, 5 verbatim units) vs product-development-and-design (EME-013, 2009-10 establishing; KMT063 2020-21 joined in B30 with per-unit J 0.84-0.97 evidence). fuzzy 100/111 shared distinctive terms — the 2018-19 Mfg-Tech print is the same PDD course; draft OLDER than the row's 2020-21 session so backfill-empty only (RULES §3). RMT061 (unowned) joins."},
    "01_btech_mfg-tech_y3_syllabus_2018-19::26::operation-research": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND: draft 'Operation Research' (RMT063, 2018-19 Mfg-Tech y3, 5 verbatim units) vs operations-research (NOE073, 2016-17): fuzzy 97 singular/plural name variant (recorded class); probe 7 shared distinctive OR terms (assignment, CPM, inventory, PERT, queuing, sequencing, transportation) — the canonical OR course across eras; 2018-19 newer so units fieldwise-win. RMT063 (unowned) joins."},
    "01_btech_mfg-tech_y3_syllabus_2018-19::27::machine-vision-and-image-processing": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND: draft 'Machine Vision and Image Processing' (RME066, 2018-19 Mfg-Tech y3, 5 verbatim units) vs machine-vision-image-processing (KMT061, 2020-21 establishing): probe fullJ=0.99 (per-unit 0.95-1.0) — verbatim era print; draft 2018-19 OLDER so backfill-empty only. RME066 (unowned) joins."},
    "02_btech_mfg-tech_y4_syllabus-cbcs_2019-20::01::automation-robotics": {
        "action": "RETARGET", "target": "automation-and-robotics",
        "reason": "B31 TIE resolution via the recorded accumulator model (B30 08::11 KMT053 ruling): draft 'Automation & Robotics' (RPI701, 2019-20 Mfg-Tech y4 CBCS, 5 verbatim units) TIEs fuzzy 90/automation-and-robotics vs 90/robotics-and-automation; probe vs the 2019-20 ME DE print (B30 durable draft 04::11, RME078): per-unit J 0.81-0.95 (U1 verbatim 'Automation: Definition, Advantages, goals, types, need, laws and principles of Automation...') — the SAME 2019-20 print family; a third same-name row is G3-forbidden. The name-exact accumulator automation-and-robotics takes the 2019-20 Mfg-Tech era print (draft OLDER than the 2023-24 establishing session: backfill-empty only, units untouched); RPI701 (unowned) joins; the print divergence vs the accumulator's 2023-24 units recorded in notes for owner reconciliation (B30 open-item-4 class)."},
    "02_btech_mfg-tech_y4_syllabus-cbcs_2019-20::05::advanced-material-technology": {
        "action": "FORCE_APPEND",
        "reason": "B31 wrong-subject FORCE_APPEND (recorded B28 01::15 Modelling-and-Simulation class): draft 'Advanced Material Technology' (RPI070, 2019-20 Mfg-Tech y4 CBCS, 5 verbatim units: intelligent/smart materials, functional/polyfunctional/structural/bio-compatible materials) fuzzy 98-hits advanced-materials-technology (2009-10 ADVANCED MATERIALS TECHNOLOGY row: ferrous materials, plain-carbon steels, alloying elements) — probe fullJ=0.09 (unitJ 0.10-0.12), only 2 generic shared terms (ceramics, polymers): the 2009-10 row is the classical ferrous/alloy metallurgy course, the 2019-20 print is the smart/functional-materials course. Different subjects sharing a name family; appends as its own row with a cross-reference note to the 2009-10 row."},
    "02_btech_mfg-tech_y4_syllabus-cbcs_2019-20::08::reverse-engineering": {
        "action": "FORCE_APPEND",
        "reason": "B31 wrong-fuzzy FORCE_APPEND (recorded B23 sensors class): draft 'Reverse Engineering' (RPI075, 2019-20 Mfg-Tech y4 CBCS, 5 verbatim units incl. the printed Course Outcomes paragraph p.17) fuzzy 89-hits river-engineering (BCE062, 2024-25 CE row) on the generic 'engineering' token only — probe fullJ=0.09. NO reverse-engineering row exists in BTech; the subject (3D scanning, digitization, point-cloud/CAD reconstruction, B30's RME073-adjacent Mfg-Tech DE print) appends as its own row; zero-GAP holds."},
    "06_btech_mining_y3_syllabus_2025-26::00::mine-environmental-engineering": {
        "action": "FORCE_APPEND",
        "reason": "B31 wrong-subject FORCE_APPEND (recorded B28 01::15 class): draft 'Mine Environmental Engineering' (BMN-501, 2025-26 Mining y3 core, 5 verbatim units) TIEs 5 name-family candidates (environmental-engineering BCE603 J=0.10; environmental-engineering-i ECE503 J=0.06; -ii ECE602 J=0.10; geoenvironmental-engineering RCE053 J=0.07; environmental-engineering-process NEN-302 J=0.08) — ALL are the Civil/Environmental generic pollution-control courses; the mining print covers mine-specific content (mine gases/dust/climate, subsidence and strata control, mine fires/spontaneous heating, mine water environmental impact). Same-name different-program class: appends as its own Mining-scope row with a cross-reference note to the Civil environmental-engineering rows."},
    "06_btech_mining_y3_syllabus_2025-26::09::mine-environmental-engineering-lab": {
        "action": "FORCE_APPEND",
        "reason": "B31 wrong-subject FORCE_APPEND (same evidence as 06::00, lab row per the recorded labs-are-distinct-rows rule): draft 'Mine Environmental Engineering Lab' (BMN-551, 2025-26 Mining y3 lab) fuzzy 92-hits environmental-engineering-lab (BCE653, 2024-25 Civil) — probe J=0.0 (no shared unit vocabulary; the mining lab's printed experiment list is mine-specific). Appends as its own row with a cross-reference note."},
    "06_btech_mining_y3_syllabus_2025-26::16::geo-informatics": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND: draft 'Geo-Informatics' (BMN-062, 2025-26 Mining y3 DE, 5 verbatim units) vs geoinformatics (ECE402, 2009-10 establishing): sim 1.0 name identity; probe shared distinctive core = the discipline's own vocabulary (GIS, GPS, photogrammetry, remote sensing, sensors) with era-reorganized unit splits (the 2009-10 print leads with aerial-photography/photogrammetry, the 2025-26 print leads with GIS fundamentals — recorded era-reorganization class, B30 facility-planning/B31 01::18 evidence standard). 2025-26 newer so units fieldwise-win; the 2009-10 photogrammetry-led text stays in source_history/git (RULES §1c). BMN-062 (unowned) joins."},
    "10_btech_open-electives-science_2009-10::00::introduction-to-soft-computing-neural-networks-fuzzy-logic-a": {
        "action": "ALLOW",
        "reason": "B31 STAND of the pre-adjudicated CODE-REASSIGNED-ACROSS-SESSIONS auto (RESOLVE_APPEND B3/B02 class): the unique Tier-0 code owner of EOE-031/EOE-041 is the k_era range print on the Mathematics-III/Science-Based-OE slot rows ('EOE 031-038'/'EOE 041-048' program-structure prints); the draft (2009-10 science-OE doc, the ORIGINAL establishing print) names Introduction-to-Soft-Computing, and exactly one name-identity row exists (sess 2009-10, empty units) — the slot-code-to-subject convergence (recorded B17 SLOT-CODE-TRANSFER class): the name-identity row gains the exact codes + the verbatim units; the pool slot rows keep their range prints (G2-exempt)."},
    "10_btech_open-electives-science_2009-10::01::nano-sciences": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "nano-sciences",
        "keep_published_codes": {"EOE-042": "power-station-practice"},
        "reason": "B31 equal-session code-slot keep (recorded B19/RCS653 class): draft 'Nano Sciences' (2009-10 science-OE doc, 5 verbatim units) prints the paired slot 'EOE-032/EOE-042'; Tier-0 TIEs across nano-sciences (owns EOE-032) and power-station-practice (EEE-042;EOE-042, its own 2009-10 establishing print). Equal-session establishing prints never steal each other's codes: the update lands on the name-exact nano-sciences row (units backfill — the row prints none), EOE-042 STAYS with power-station-practice (G2 single ownership), and the science-OE pairing print is recorded as narrative on the nano-sciences row."},
    "10_btech_open-electives-science_2009-10::04::polymer-science-and-technology": {
        "action": "ALLOW",
        "reason": "B31 STAND of the pre-adjudicated CODE-REASSIGNED-ACROSS-SESSIONS auto (B3 BBC102 class): the unique Tier-0 code owner EOE-035/EOE-045 is polymer-science-technology ('Polymer Science & Technology', 2009-10, units empty, ROE035;ROE045 also owned); the draft name 'Polymer Science and Technology' name-matches exactly one same-course row (polymer-science-and-technology, BOE311;BOE411, 2023-24, 5 units — the NEP open-elective print of the SAME science elective; '&'/'and' print variance across eras, distinctive probe: polymerization/composites/polymers). The auto transfers EOE-035/EOE-045 to the name-identity accumulator row (the &-form row keeps ROE codes + narrative; recorded variant-name-rows-pending-reconciliation owner open item); draft 2009-10 OLDER so backfill-empty only."},
})

# ---- B31 (CRON-20261104-B31) doc-level scope from the PRINTED COVERS ----
DOC_SCOPE.update({
    "0ade72fa693fbd9c": {
        "branch_names": "Manufacturing Technology",
        "program_year": "3",
        "reason": "B31 doc01: cover prints 'EVALUATION SCHEME & SYLLABUS For B. Tech. 3rd Year Manufacturing Technology ON CBCS [Effective from session 2018-19]' — single-branch Mfg-Tech 3rd-year CBCS print; per-subject program_year from printed semesters (V/VI -> 3)"},
    "ae8c8559100c3cbf": {
        "branch_names": "Manufacturing Technology",
        "program_year": "4",
        "reason": "B31 doc02: cover prints 'STUDY & EVALUATION SCHEME WITH SYLLABUS FOR B. TECH 4th YEAR MANUFACTURING TECHNOLOGY ON CHOICE BASED CREDIT SYSTEM (EFFECTIVE FROM THE SESSION: 2019-20)' (R-era CBCS Sem VII/VIII)"},
    "16b336aad90afc2b": {
        "branch_names": "Manufacturing Technology",
        "program_year": "4",
        "reason": "B31 doc03: cover prints 'STUDY & EVALUATION SCHEME — B.Tech.ManufacturingTechnology [EffectivefromSession2016-17] — YEAR IV, SEMESTER-VII' (kerning-fused print; N-era NME/NMT codes)"},
    "b3c1767fa66cb1cb": {
        "branch_names": "Manufacturing Technology",
        "program_year": "4",
        "reason": "B31 doc04: cover prints 'STUDY & EVALUATION SCHEME WITH SYLLABUS | FOR | B. TECH. 4th YEAR | MANUFACTURING TECHNOLOGY | [Effective from Session: 2021-22]' (K-era KMT/KPI codes)"},
    "2e50304ddbcc9f22": {
        "branch_names": "Manufacturing Technology",
        "program_year": "4",
        "reason": "B31 doc05: cover prints 'COURSE STRUCTURE/EVALUATION SCHEME FOR B.TECH. 4th YEAR MANUFACTURING TECHNOLOGY [Effective from Session: 2025-26]' (B-era NEP BME/BPI codes)"},
    "d97d9fe331d271c1": {
        "branch_names": "Mining Engineering",
        "program_year": "3",
        "reason": "B31 doc06: cover (p.1) prints 'Evaluation Scheme & Syllabus For B.Tech. 3rd Year MINING ENGINEERING [Effective from the Session: 2025-26}' (B-era BMN codes; the closing brace is a printed cover typo, kept verbatim); per-subject program_year from printed semesters (V/VI -> 3)"},
    "1b93096db8304b23": {
        "branch_names": "Mining Engineering",
        "program_year": "4",
        "reason": "B31 doc07: cover prints 'Evaluation Scheme & Syllabus For B.Tech. 4th Year MINING ENGINEERING [Effective from the Session: 2026-27}' (B-era BMN codes; printed bracket typo '2026-27}' kept verbatim)"},
    "db1f836f585af9c4": {
        "branch_names": "",
        "program_year": "",
        "reason": "B31 doc10: cover prints 'U.P. TECHNICAL UNIVERSITY LUCKNOW Syllabus 1. Science based Open Electives 2. Open Electives-I 3. Open Electives-II [Effective from the session : 2009-10] B.TECH. COURSES' — no branch list printed (science-based OE / OE-I / OE-II are common university slots, B16 BNC zero-guess class); branch_names stays BLANK; all 16 subjects resolve as UPDATES on existing rows so no append scope is consumed"},
})

'''

src = open(M).read()
guard = 'if __name__ == "__main__":'
assert guard in src, 'main guard not found'
assert 'B31 (CRON-20261104-B31) per-key adjudications' not in src, 'B31 block already present'
src = src.replace(guard, BLOCK + '\n' + guard, 1)
open(M, 'w').write(src)
print('B31 adjudication blocks inserted before __main__ guard')
