#!/usr/bin/env python3
"""adjudicate_b37.py — inject the 3 B37 TIE resolutions into merge_draft.py's
TIER2_OVERRIDES (recorded classes: code-lineage RETARGET B29-TQM class; era
accumulator RETARGET B36-KAS404 class; same-session corroborating print
backfill-only + needs_review B27-RCS653 class). Idempotent."""
import re

P = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
src = open(P).read()
if "adjudicate_b37 marker" in src:
    print("already injected")
    raise SystemExit(0)

BLOCK = '''
    # --- B37 adjudications (adjudicate_b37 marker) ---
    "02_btech_syllabus_2009-10::39::transducers-and-sensors": {
        "action": "RETARGET", "target": "transducer-and-sensors",
        "reason": "B37 TIE resolution (fuzzy 98 transducer-and-sensors vs 100 sensors-and-transducers) on code-lineage identity: draft 'Transducers and Sensors' (EIC-401, 2009-10 Instrumentation-family 3rd/4th-yr syllabus, 5 verbatim units) — the transducer-and-sensors row owns NIC-502 (2016-17 N-era print of the SAME instrumentation branch family EIC->NIC, establishing source btech_applied-electronics-ece-ei_syllabus); the competing sensors-and-transducers row (KEE052/BEE052, 2020-21 EE-branch open-elective accumulator) is a DIFFERENT branch's elective with its own code family (recorded B29-TQM / B23 code-owner class: lineage beats generic-vocabulary ratio). 2009-10 is the older print: backfill-empty only; NIC-502 ownership unchanged."},
    "03_btech_syllabus_2013-14::24::engineering-chemistry": {
        "action": "RETARGET", "target": "engineering-chemistry",
        "reason": "B37 TIE resolution (code identity across rows on NAS-102/NAS-202) on name identity + era-ladder lineage: draft 'ENGINEERING CHEMISTRY' (NAS-102/NAS-202 paired 2013-14 y1/y2 print, 5 verbatim units) — the engineering-chemistry accumulator row already owns the whole era ladder of this university-wide course (RAG202; KAS-102T/KAS-202T; BAS102/BAS202; RAS102/RAS202 from the AG 2016-17 establishing print); NAS-102/NAS-202 are the 2013-14-era codes of the SAME course (EAS->NAS->KAS/BAS/RAS ladder). The competing engineering-physics-ii row carries NAS-202 only as a 2013-14 dual-print artifact in its code history (its own subject is Physics-II, NAS-201-era) — recorded B36 KAS304/KAS404 dual-slot class: converge onto the name-identity accumulator row; the physics row is untouched and its NAS-202 history token is recorded for owner reconciliation. 2013-14 older than 2016-17: backfill-empty only."},
    "09_btech_textile-tech_course-structure_2026-27::19::applied-physics-lab-applied-chemistry-for-fibres-polymers-an": {
        "action": "RETARGET", "target": "applied-physics-lab", "backfill_only": True,
        "reason": "B37 TIE resolution (code identity across rows on the AAS151/ASS251 paired lab cell) — same-session corroborating print (recorded B27 RCS-653 class): the TX-stream 2026-27 first-year doc prints 'AAS151/ ASS251 Applied Physics Lab/ Applied Chemistry ... Lab' as a PAIRED scheme cell; the applied-physics-lab row is the 2026-27 establishing print (btech_ag_course-structure_2026-27, owns AAS151/AAS251/ASS251). Equal-session prints never take codes from their published owner (B29 RETARGET class): the TX doc is recorded as a corroborating source with backfill-empty-only, and the paired-cell lab-content split (physics vs chemistry experiments in one cell) is flagged needs_review for owner reconciliation per RULES §4 — the draft's merged experiment list is NOT written fieldwise."},
'''

anchor = "TIER2_OVERRIDES = {"
i = src.find(anchor)
assert i > 0, "TIER2_OVERRIDES dict not found"
j = i + len(anchor)
src = src[:j] + BLOCK + src[j:]
open(P, "w").write(src)
print("injected 3 B37 TIER2_OVERRIDES entries")
