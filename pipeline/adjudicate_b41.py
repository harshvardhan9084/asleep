#!/usr/bin/env python3
"""adjudicate_b41.py — inject the B41 TIER2_OVERRIDES adjudications into
merge_draft.py (marker: adjudicate_b41). Evidence: registry rows + parsed
fulltext verified before writing. 4 same-subject ALLOWs (u1 verbatim) + 2 TIE
RETARGETs on the recorded B39 word-order precedent."""
import json

MARK = "    # --- B41 commit-run adjudications (adjudicate_b41 marker) ---\n"
ENTRIES = '''    "01_btech_y4s8_open-elective-3-4-list_2021-22::03::biomedical-signal-processing": {
        "action": "ALLOW",
        "reason": "B41 TIER2 same-subject ALLOW (fuzzy 98, overlap 88): draft 'BIOMEDICAL SIGNAL PROCESSING' (KOE-082, 2021-22 OE-III print) vs the bio-medical-signal-processing accumulator (EBM-603;RBM602;BEC-056;RIC080;EIC-032;BIC-062;NIC041) — hyphen/space print variance (recorded class; identical class to B40's 06::20 NIC041 ALLOW); unit-I VERBATIM ('Introduction to Bio-Medical Signals: Classification, Acquisition and Difficulties during Acquisition...'). KOE082 unowned in BTech, accumulates cleanly."},
    "02_btech_y4s8_open-elective-3-4-list_2025-26::02::biomedical-signal-processing": {
        "action": "ALLOW",
        "reason": "B41 TIER2 same-subject ALLOW (fuzzy 98, overlap 88): same row + class as 01::03 — the 2025-26 OE-III doc prints the identical course as BOE-083 with identical unit-I (corroborating print). BOE083 unowned, accumulates."},
    "01_btech_y4s8_open-elective-3-4-list_2021-22::11::computerized-process-control": {
        "action": "ALLOW",
        "reason": "B41 TIER2 same-subject ALLOW (fuzzy 96, overlap 70): draft 'COMPUTERIZED PROCESS CONTROL' (KOE-092, 2021-22 OE-IV print) vs the computerised-process-control accumulator (REC078;KIC077;EIC-031;ROE-076) — z/s spelling variance (recorded class, same as B40's 05::03 ALLOW); unit-I VERBATIM ('Basics of Computer-Aided Process Control: Role of computers in process control...'). KOE092 unowned, accumulates cleanly."},
    "02_btech_y4s8_open-elective-3-4-list_2025-26::12::computerized-process-control": {
        "action": "ALLOW",
        "reason": "B41 TIER2 same-subject ALLOW (fuzzy 96, overlap 70): same row + class as 01::11 — the 2025-26 OE-IV doc prints the identical course as BOE-094 with identical unit-I (corroborating print). BOE094 unowned, accumulates."},
    "01_btech_y4s8_open-elective-3-4-list_2021-22::12::data-warehousing-data-mining": {
        "action": "RETARGET", "target": "data-warehousing-and-data-mining",
        "reason": "B41 TIE resolution (fuzzy 91/data-warehouse-and-data-mining vs 92/data-warehousing-and-data-mining) on the recorded B39 word-order precedent: both candidate rows carry the IDENTICAL canonical unit-I ('Data Warehousing: Overview, Definition, Data Warehousing Components...') — word-order print variants of the same university course family; the higher-fuzzy code-bearing accumulator data-warehousing-and-data-mining (KAI075;BCS058;NCS066;ECS-075...) takes the OE print; the 91 candidate corroborates as a same-family print. Draft KOE-093 (2021-22 OE-IV) is unowned, accumulates."},
    "02_btech_y4s8_open-elective-3-4-list_2025-26::13::data-warehousing-data-mining": {
        "action": "RETARGET", "target": "data-warehousing-and-data-mining",
        "reason": "B41 TIE resolution (same row + class as 01::12): the 2025-26 OE-IV doc prints the identical course as BOE-093 (corroborating print); converges on data-warehousing-and-data-mining per the B39 word-order precedent. BOE093 unowned, accumulates."},
'''

src = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
text = open(src).read()
if "adjudicate_b41 marker" in text:
    print("already injected")
else:
    anchor = "    # --- B40 commit-run adjudications (adjudicate_b40 marker) ---\n"
    assert anchor in text
    text = text.replace(anchor, ENTRIES + anchor, 1)
    open(src, "w").write(text)
    print("injected 6 B41 TIER2_OVERRIDES entries")
