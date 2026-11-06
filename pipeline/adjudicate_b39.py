#!/usr/bin/env python3
"""adjudicate_b39.py — inject the B39 TIER2_OVERRIDES adjudications into
merge_draft.py (marker: adjudicate_b39). Every entry is evidence-recorded;
the TIE entries resolve the 8 unresolved TIEs, the TIER2 ALLOWs record the
name-variant classes. Verified against the registry before writing."""

MARK = "    # --- B39 commit-run adjudications (adjudicate_b39 marker) ---\n"
BLOCK = MARK + '''    "01_btech_y1_syllabus_2008-09::04::electrical-engineering": {
        "action": "RETARGET", "target": "basic-electrical-engineering",
        "reason": "B39 TIE resolution (fuzzy TIE electronics-engineering vs basic-electrical-engineering) on unit-vocabulary identity + the recorded B38 name-class: draft 'ELECTRICAL ENGINEERING' (EEE-101/EEE-201, 2008-09 y1 print, 5 verbatim units: DC circuit analysis & network theorems / steady-state single-phase AC / three-phase AC circuits / power system layout / electrical machines) — the basic-electrical-engineering row owns KEE101/KEE201/KEE-101T/KEE-201T (the same course's K-era ladder; the identical shortened header print 'ELECTRICAL ENGINEERING' was recorded in B38 on KEE101TH as the shortened form of 'Basic Electrical Engineering'); the DC-circuits-to-machines unit vocabulary is the BEE syllabus while the electronics-engineering row's semiconductors/OP-AMP content is a DIFFERENT subject sharing the generic skeleton. RETARGET pins the update on the KEE101-owner row; 2008-09 older print: backfill-empty only; EEE101/EEE201 are unowned so they accumulate cleanly."},
    "03_btech_y2_common-subjects-syllabus-rev_2014-15::03::laser-systems-and-applications": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "laser-systems-and-applications",
        "keep_published_codes": {"NOE033": "mathematics-iii-science-based-open-elective", "NOE043": "science-based-open-elective-mathematics-iii"},
        "reason": "B39 TIE resolution (code identity across rows on the dual-slot print NOE-033/NOE-043): the name-identity laser-systems-and-applications row (EOE-033/EOE-043, 2009-10 establishing print, EMPTY units) gains the 2014-15 verbatim units/COs/books (newer-session fieldwise); the N-era slot codes stay owned by the two Science-Based-OE slot rows exactly as the recorded B31/B35 STAND kept them for the E/K-era prints (introduction-to-soft-computing precedent: name-identity rows gain units, NOT slot codes; the pool rows keep their expanded range prints); the keep_owner executor records the N-era print as narrative on the target row."},
    "03_btech_y2_common-subjects-syllabus-rev_2014-15::04::polymer-science-technology": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "polymer-science-technology",
        "keep_published_codes": {"NOE035": "mathematics-iii-science-based-open-elective", "NOE045": "science-based-open-elective-mathematics-iii"},
        "reason": "B39 TIE resolution (same dual-slot class as 03::03): the name-identity polymer-science-technology row (ROE035/ROE045 2017-18 R-era ladder, EMPTY units) gains the 2014-15 verbatim units; NOE-035/NOE-045 stay owned by the two Science-Based-OE slot rows (B31/B35 STAND); narrative records the N-era print."},
    "03_btech_y2_common-subjects-syllabus-rev_2014-15::07::discrete-mathematics": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "discrete-mathematics-btech",
        "keep_published_codes": {"NOE038": "mathematics-iii-science-based-open-elective", "NOE048": "science-based-open-elective-mathematics-iii"},
        "reason": "B39 TIE resolution (same dual-slot class as 03::03): the BTech name-identity discrete-mathematics-btech row (ROE038/ROE048 ladder; 2009-10 units printed) gains the 2014-15 verbatim units (newer-session fieldwise wins); NOE-038/NOE-048 stay owned by the two Science-Based-OE slot rows (B31/B35 STAND); RULES §1b: the BCA discrete-mathematics row is a DIFFERENT subject and is never touched."},
    "03_btech_y2_common-subjects-syllabus-rev_2014-15::08::nuclear-science": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "nuclear-science",
        "keep_published_codes": {"NOE036": "mathematics-iii-science-based-open-elective", "NOE046": "science-based-open-elective-mathematics-iii"},
        "reason": "B39 TIE resolution (same dual-slot class as 03::03): the name-identity nuclear-science row (EOE-046/ROE036/ROE046 ladder, units printed) gains the 2014-15 verbatim units (newer-session fieldwise); NOE-036/NOE-046 stay owned by the two Science-Based-OE slot rows (B31/B35 STAND)."},
    "04_btech_y2_engg-science-course_2019-20::04::basics-data-structure-and-algorithms": {
        "action": "RETARGET", "target": "basics-data-structure-algorithms",
        "reason": "B39 TIE resolution (fuzzy 94/basics-data-structure-algorithms vs 89/data-structure-and-algorithms): the target row owns KOE035;KOE045 as exact tokens (the 2023-24 BOE/K-era accumulator; u1 'Introduction: Basic Terminology, Elementary Data Organization, Built in Data Types in C...' matches the 2019-20 AICTE-model-curriculum print) — the draft 'Basics Data Structure & Algorithms' (KOE-035/KOE-045 dual print, 2019-20 ES-course doc) is the SAME course; the 89 fuzzy candidate data-structure-and-algorithms (ECS-508, 2009-10 CSE DE) is a DIFFERENT subject sharing the generic skeleton. RETARGET pins the update on the exact-name row; the dual print atomizes to both codes at apply time."},
    "05_btech_y2_engg-science-course_2021-22::04::basics-data-structure-and-algorithms": {
        "action": "RETARGET", "target": "basics-data-structure-algorithms",
        "reason": "B39 TIE resolution (same row as 04::04; the 2021-22 ES-course doc prints the identical KOE-035/KOE-045 course with identical unit content) — converges onto the basics-data-structure-algorithms accumulator; 2021-22 vs 2023-24 row session: backfill-empty only."},
    "09_btech_y3-4_syllabus_2010-11::23::data-mining-data-warehousing": {
        "action": "RETARGET", "target": "data-warehousing-and-data-mining",
        "reason": "B39 TIE resolution (fuzzy 92/data-warehousing-and-data-mining vs 91/data-warehouse-and-data-mining): word-order print variants of the same course family; the target owns the K/AI-era accumulator codes (KAI075;BCS058;NCS066;BCS058H;BCS-058H) and its u1 'Data Warehousing: Overview, Definition, Data Warehousing Components...' is the DW&DM canon also printed in the competing row; the 2010-11 ECS-075 'Data Mining & Data Warehousing' is the E-era print of the same university course (5 verbatim units; ECS-075 unowned so it accumulates cleanly). RETARGET pins the update on the higher-fuzzy code-bearing accumulator; the 91 candidate row corroborates as a same-family print."},
    "04_btech_y2_engg-science-course_2019-20::02::sensor-and-instrumentation": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (fuzzy 92, overlap 104): 'Sensor and Instrumentation' vs the sensor-instrumentation row's 'Sensor & Instrumentation' — the recorded 'and'/'&' print-variance class (B29/B33); the row owns KOE034;KOE044 (this 2019-20 print's own codes) and its u1 'Sensors & Transducer: Definition, Classification & selection of sensors...' verbatim-matches the draft; the dual code print 'KOE034/044' atomizes at apply time."},
    "04_btech_y2_engg-science-course_2019-20::03::energy-science-and-engineering": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (fuzzy 93, overlap 137): 'Energy Science and Engineering' vs 'Energy Science & Engineering' — the 'and'/'&' print-variance class; the energy-science-engineering row owns KOE033;KOE043 and its u1 'Energy and its Usage: Units and scales of energy use, Mechanical energy and transport...' verbatim-matches the draft's unit-I."},
    "05_btech_y2_engg-science-course_2021-22::02::energy-science-and-engineering": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (same row + class as 04::03; the 2021-22 doc prints the identical KOE-033/KOE-043 course with identical unit-I vocabulary)."},
    "09_btech_y3-4_syllabus_2010-11::02::design-and-analysis-of-algorithms": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (fuzzy 98, overlap 84): plural/singular print variance ('Design and Analysis of Algorithms' vs the design-and-analysis-of-algorithm row) — the recorded B29/B33 singular/plural class; the row owns BCS503;KCS503;NCS501 (the accumulator) and the 2010-11 ECS-502 print is the E-era of the same course; ECS-502 is unowned so it accumulates cleanly."},
    "09_btech_y3-4_syllabus_2010-11::07::computer-network": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (fuzzy 97, overlap 49): singular/plural print variance ('Computer Network' vs 'Computer Networks') — recorded class; the computer-networks row owns BCS603;KCS603;NCS601;RCS-601 (the accumulator); the 2010-11 ECS-601 print is the E-era of the same course (unowned code, accumulates)."},
    "09_btech_y3-4_syllabus_2010-11::12::distributed-systems": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (fuzzy 97, overlap 80): plural print variance ('DISTRIBUTED SYSTEMS' vs 'Distributed System') — recorded class; the row owns KDS052;KCS077;NCS-701;RCS701; the 2010-11 ECS-701 print is the E-era of the same course (unowned code, accumulates)."},
    "09_btech_y3-4_syllabus_2010-11::40::multimedia-systems": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (fuzzy 97, overlap 96): plural print variance ('Multimedia Systems' vs 'Multimedia System', 2009-10 establishing row); the 2010-11 EIT-081 print is the same course's E-era (unowned code, accumulates)."},
    "10_btech_y3_syllabus_2024-25::14::instrumentation-measurement-lab": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (fuzzy 100 normalized-identical): word-order print variance — the 2024-25 ICE print 'INSTRUMENTATION & MEASUREMENT LAB' (BIC-551) vs the measurement-instrumentation-lab row 'Measurement & Instrumentation Lab' (KEC-653A;KIC-553;KIC-551 K-era ICE labs, empty unit text) — the same university lab across the K->B era rename; BIC-551 accumulates."},
    "10_btech_y3_syllabus_2024-25::20::microcontrollers-and-sensors-for-iot-devices": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (fuzzy 86, overlap 134 shared distinctive terms): the 2024-25 ICE DE print 'MICROCONTROLLERS AND SENSORS FOR IOT DEVICES' (BIC-063) vs the microcontrollers-and-sensors-for-iot-applications row (BEC-064, 2025-26) — unit-I is verbatim-identical on both prints ('Fundamentals of IOT: Introduction to IoT, IoT Design Methodology, Design Principles for Connected Devices...') and the unit vocabulary (MSP430, sensor interfacing, IoT security) is the same course; DEVICES/APPLICATIONS is the era print variance; the row's 2025-26 session is newer so the 2024-25 draft BACKFILLS only and BIC-063 accumulates to code_history."},
'''

src_path = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
src = open(src_path).read()
if "adjudicate_b39 marker" in src:
    print("already injected")
else:
    anchor = "    # --- B37 commit-run TIE adjudications (adjudicate_b37b marker) ---"
    assert anchor in src, "anchor missing"
    src = src.replace(anchor, BLOCK + anchor, 1)
    open(src_path, "w").write(src)
    print("injected B39 adjudications")
