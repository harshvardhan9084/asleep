#!/usr/bin/env python3
"""patch_b17_merge_adjudications.py — B17 per-key merge adjudications, all with
recorded print/vocabulary evidence (B16 precedent: TIER2_OVERRIDES + DOC_SCOPE
+ in-place dict edits; the publish step ships this exact toolchain per §1c).

1. TIER2_OVERRIDES +4:
   - 03::05 renewable-energy-resources (T2 fuzzy 96/overlap 61 → ALLOW):
     the target renewable-energy-sources row (KAG-057;BAG057;NAG-081, 2020-21)
     carries a unit1 VERBATIM-IDENTICAL to the draft's unit1 ('Introduction:
     Various non-conventional energy resources- ... Solar Cells: Theory of
     solar cells...') — the same university-wide elective content; KOE074
     (2021-22 OE-II print) joins as the newest era code; 2021-22 fieldwise
     wins (RULES §3).
   - 06::24 / 07::14 / 09::14 mini-project-or-internship-assessment (RETARGET
     internship-assessment-mini-project): recorded B16 rejection class (the
     B16 override for the same transfer) — the ladder's Tier-0 code-reassigned
     name-transfer would move CSE-family codes (BCS554; KCS354/KCS554/KCS752)
     OUT of the CSE&E code-owner row internship-assessment-mini-project
     (all_codes BCC351;KCS354;KEC354;KCS554;BCS554;BCE554;KCS752) into the
     AG/AE-named cross-branch slot row (primary BAE553, EMPTY branch_names) —
     cross-branch pollution, RULES §1b spirit. UPDATE the CSE&E code-owner row;
     the RETARGET also re-points the registered reassignment so the executor
     strips these codes from any OTHER row claiming them (G2 single-owner).

2. SLOT_CODE_TRANSFERS +2 (new recorded class, HSMC slot-code transfer):
   03::00 rural-development (KHU701/KHU801) and 03::01 project-management-
   entrepreneurship (KHU702/KHU802): the 2021-22 HSMC doc prints REAL subjects
   (5 verbatim units each; RD also prints COs) under dual slot-code headings
   'KHU701/KHU801' (HSMC-1 Sem-VII / HSMC-2 Sem-VIII offering per the printed
   p.2 scheme list 'HSMC1/HSMC2 || KHU701/KHU801 RUR...'). The only code owners
   today are the generic slot rows hsmc-1-hsmc-2 ('HSMC -1 #/ HSMC-2 #',
   KHU701;KHU702) and hsmc-2-hsmc-1 ('HSMC- 2#/HSMC-1#', KHU801;KHU802) —
   program-structure prints, not subjects. Newest detailed print wins
   (CODE-REASSIGNED principle): the subject APPENDs with its printed codes and
   ownership transfers off the slot rows via the recorded reassignment executor
   (B08 remedy: a slot row losing every code becomes a codeless identity row,
   narrative history retained, G3 skips empty primary). Zero-GAP holds: the
   subjects' full verbatim content lands in subject rows; the slot prints stay
   in the draft's non_subject_rows and the slot rows' names/code_history.

3. RESOLVE_APPEND['SLOT-CODE-TRANSFER'] — the recorded adjudication kind.

4. DOC_SCOPE +5 (branch/program_year verbatim from each appending doc's cover):
   9f353dd680d7c524 (HSMC+OE-II list 2021-22, no branch list printed → blank,
   year 4); 3791c12eb1101e50 (B.Tech FIRST YEAR course structure 2026-27 AICTE
   model, common — stream-variant codes recorded in non_subject_rows → blank,
   year 1); 1f7976d962297c2e (CSBS 4th year NEP2020 2025-26); 829a3843b2605d88
   (CSD 3rd year NEP2020 2024-25); 6db264fcd825bdae (CSD 4th year AICTE
   2024-25).

Idempotent: every insertion is guarded by a marker check.
"""
import re, sys

P = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
src = open(P).read()
n = 0

# ---------- 1a. TIER2_OVERRIDES entries (insert right after dict open) ----------
T2_ANCHOR = 'TIER2_OVERRIDES = {\n'
if "B17 renewable-energy-resources ALLOW" not in src:
    add = '''TIER2_OVERRIDES = {
    "03_btech_common_y4_hsmc-courses_2021-22::05::renewable-energy-resources": {
        "action": "ALLOW",
        "reason": "B17 renewable-energy-resources ALLOW (era-family/same-elective class): the T2 target renewable-energy-sources row (KAG-057;BAG057;NAG-081, 2020-21 AG print) carries a unit1 VERBATIM-IDENTICAL to the draft's unit1 ('Introduction: Various non-conventional energy resources- Introduction, availability, classification, relative merits and demerits. Solar Cells: Theory of solar cells. Solar cell materials, solar cell array, solar cell power plant, limitations.') — the same university-wide renewable-energy elective content reprinted as KOE074 in the 2021-22 OE-II list; KOE074 joins as the newest era code and 2021-22 fieldwise wins (RULES §3 newest-session policy)."},
'''
    src = src.replace(T2_ANCHOR, add, 1); n += 1

if "B17 mini-project CSE&E code-owner RETARGET class" not in src:
    add = '''    "06_btech_csd_y3_syllabus_2024-25::24::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B17 mini-project CSE&E code-owner RETARGET class (recorded B16 rejection of this exact transfer): the ladder's Tier-0 code-reassigned name-transfer would move CSE-family BCS554 OUT of the CSE&E code-owner row internship-assessment-mini-project (all_codes BCC351;KCS354;KEC354;KCS554;BCS554;BCE554;KCS752, branch Computer Science & Engineering) into the AG/AE-named cross-branch slot row (primary BAE553, EMPTY branch_names) — cross-branch pollution, RULES §1b spirit. UPDATE the CSE&E code-owner row; the RETARGET re-points the registered reassignment so any OTHER row claiming these codes is stripped to single ownership (G2). The draft subject is the 2024-25 CSD scheme-row print (PS=100, Total=100; no detailed syllabus printed — flagged no_detailed_syllabus_printed)."},
    "07_btech_csd_y4_syllabus_2024-25::14::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B17 mini-project CSE&E code-owner RETARGET class (recorded B16 override: 'UPDATE the CSE&E row; KCS752 (sem-VII slot print) joins it as a slot code'): the draft (2024-25 CSD y4; heading prints '(KCS 354 , KCS 554 , KCS 752)' — three earlier-year assessment codes of the same slot) carries KCS354/KCS554/KCS752, ALL already owned by the CSE&E code-owner row internship-assessment-mini-project; the name-transfer toward the AG/AE-named row (BAE553 primary, empty branch) would pollute cross-branch (RULES §1b spirit, B08 recorded rejection). UPDATE the CSE&E code-owner row; 2024-25 print corroborates/extends."},
    "09_btech_cse-ai_y3_syllabus_2024-25::14::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B17 mini-project CSE&E code-owner RETARGET class (same recorded B16 rejection): draft BCS554 (2024-25 CSE-AI y3 scheme-row print, PS=100/Total=100, marks columns word-coordinate verified) — BCS554 is ALREADY owned by the CSE&E code-owner row internship-assessment-mini-project; the name-transfer toward the AG/AE-named cross-branch row (BAE553 primary, empty branch) is rejected per RULES §1b spirit. UPDATE the CSE&E code-owner row."},
'''
    src = src.replace(T2_ANCHOR, add, 1); n += 1

# ---------- 1b. SLOT_CODE_TRANSFERS dict (before DOC_SCOPE comment) ----------
DS_ANCHOR = "# B2: doc-level scope from the PRINTED COVER of each ingested document"
if "SLOT_CODE_TRANSFERS = {" not in src:
    add = '''# ---------------- SLOT_CODE_TRANSFERS (B17 recorded class) -----------------
# A dual slot-code print (e.g. 'KHU701/KHU801' = HSMC-1 Sem-VII / HSMC-2
# Sem-VIII offering) naming a REAL subject (verbatim units printed) whose
# printed codes are currently owned by generic slot rows (program-structure
# prints, not subjects). Newest detailed print wins (CODE-REASSIGNED
# principle): the subject APPENDs with its printed codes; code ownership
# transfers off the slot rows via the recorded reassignment executor (B08
# remedy: a slot row losing every code becomes a codeless identity row with
# its narrative history retained; G3 skips empty primary). Zero-GAP holds.
SLOT_CODE_TRANSFERS = {
    "03_btech_common_y4_hsmc-courses_2021-22::00::rural-development-administration-and-planning": {
        "codes": ["KHU701", "KHU801"],
        "reason": "B17 HSMC slot-code transfer: the 2021-22 HSMC doc prints 'KHU701/KHU801 RURAL DEVELOPMENT: ADMINISTRATION AND PLANNING' as a REAL subject (5 verbatim units + COs; p.2 scheme list 'HSMC1/HSMC2 || KHU701/KHU801 ...' = HSMC-1 Sem-VII / HSMC-2 Sem-VIII offering) — the only current owners of KHU701/KHU801 are the generic slot rows hsmc-1-hsmc-2 / hsmc-2-hsmc-1 ('HSMC-1#/HSMC-2#' program-structure prints). The subject appends with its printed codes; the slot rows keep their prints in names/code_history (codeless identity rows, recorded B08 remedy)."},
    "03_btech_common_y4_hsmc-courses_2021-22::01::project-management-entrepreneurship": {
        "codes": ["KHU702", "KHU802"],
        "reason": "B17 HSMC slot-code transfer: the 2021-22 HSMC doc prints 'KHU702/KHU802 PROJECT MANAGEMENT & ENTREPRENEURSHIP' as a REAL subject (5 verbatim units; same HSMC-1/HSMC-2 dual-slot model) — KHU702/KHU802 currently sit on the generic slot rows hsmc-1-hsmc-2 / hsmc-2-hsmc-1. The subject appends with its printed codes; slot rows keep their prints (codeless identity rows, recorded B08 remedy)."},
}

'''
    src = src.replace(DS_ANCHOR, add + DS_ANCHOR, 1); n += 1

# ---------- 2. RESOLVE_APPEND entry ----------
RA_ANCHOR = '    "TIER2-OVERRIDE": {\n'
if '"SLOT-CODE-TRANSFER"' not in src:
    add = '''    "SLOT-CODE-TRANSFER": {
        "action": "APPEND_REAL_SUBJECT_WITH_CODE_TRANSFER",
        "reason": "A dual slot-code heading ('KHU701/KHU801' = HSMC-1/HSMC-2 offering) names a REAL subject (verbatim units printed) whose codes currently sit on generic slot rows ('HSMC-1#/HSMC-2#' program-structure prints). The newest detailed print wins (recorded CODE-REASSIGNED principle): the subject appends with its printed codes; ownership transfers off the slot rows via the recorded reassignment executor, which leaves a slot row that loses every code as a codeless identity row (B08 remedy; narrative history retained in code_history_all; G3 skips empty primary). Zero-GAP: the subject's content lands in a subject row; the slot prints remain in the draft's non_subject_rows and the slot rows' names."},
'''
    src = src.replace(RA_ANCHOR, add, 1); n += 1

# ---------- 3. DOC_SCOPE entries ----------
if "B17 HSMC+OE-II list 2021-22" not in src:
    add = '''    "9f353dd680d7c524": {
        "branch_names": "",
        "program_year": "4",
        "reason": "B17 HSMC+OE-II list 2021-22: cover prints 'EVALUATION SCHEME & SYLLABUS FOR HUMANITIES, SCOCIAL SCIENCE AND MANAGEMENT COURSE (HSMC COURSE) & OPEN ELECTIVES II LIST AS PER AICTE MODEL CURRICULUM [Effective from the Session:2021-22]' and the list page header prints 'B.Tech. VII Semester (2021-22)' — no branch list printed (HSMC/OE are common slots), so branch_names stays BLANK (zero-guess, B16 BNC class); program_year 4 from the printed VII-semester span"},
    "3791c12eb1101e50": {
        "branch_names": "",
        "program_year": "1",
        "reason": "B17: cover prints 'COURSE STURCTURE & EVALUATION SCHEME of Bachelor of Technology (B.Tech.) First Year (Along with the SOPs for General Proficiency, Innovation & Design Thinking Lab, and AICTE Activity Points) AS PER AICTE MODEL CURRICULUM' (typo STURCTURE kept verbatim) — common first-year structure, no branch list printed; per-stream variant codes are recorded in the draft's non_subject_rows; branch_names BLANK (zero-guess), program_year 1"},
    "1f7976d962297c2e": {
        "branch_names": "Computer Science and Business Systems",
        "program_year": "4",
        "reason": "B17: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. 4TH YEAR — Computer Science and Business Systems — Based On NEP2020 — (Effective from the Session: 2025-26)'"},
    "829a3843b2605d88": {
        "branch_names": "Computer Science and Design",
        "program_year": "3",
        "reason": "B17: cover prints 'Evaluation Scheme & Syllabus For B.Tech. 3rd Year (Computer Science and Design) Based On NEP2020 Effective from the Session: 2024-25)'"},
    "6db264fcd825bdae": {
        "branch_names": "Computer Science and Design",
        "program_year": "4",
        "reason": "B17: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. FOURTH (IV) YEAR (COMPUTER SCIENCE AND DESIGN) AS PER AICTE MODEL CURRICULUM [Effective from the Session: 2024-25]'"},
'''
    src = src.replace('DOC_SCOPE = {\n', 'DOC_SCOPE = {\n' + add, 1); n += 1

# ---------- 4. run() wiring: TIE -> APPEND + reassignment for transfer keys ----------
WIRE_ANCHOR = '''            if op[0] == "UPDATE":
                tgt = op[1]["subject_id"]'''
if "SLOT-CODE-TRANSFER override APPEND" not in src:
    add = '''            # B17: HSMC slot-code transfer (recorded class) — a dual slot-code
            # print naming a REAL subject whose codes sit on generic slot rows.
            # Newest detailed print wins: APPEND the subject with its printed
            # codes and register the ownership transfer (executor strips the
            # codes from the slot rows, B08 remedy for stranded slot rows).
            if op[0] == "TIE" and SLOT_CODE_TRANSFERS.get(key):
                ov = SLOT_CODE_TRANSFERS[key]
                info = info + " | SLOT-CODE-TRANSFER override APPEND: " + ov["reason"][:200]
                flags.append((key, "SLOT-CODE-TRANSFER", ov["reason"]))
                flags = [f for f in flags if not (f[0] == key and str(f[1]).startswith("TIE"))]
                reassignments.append({"codes": list(ov["codes"]),
                                      "to_row": slug(dsub.get("name", "")),
                                      "detail": info, "draft_session": dmeta["session"]})
                tier = 3
                op = ("APPEND", (None, ("", "")))
'''
    src = src.replace(WIRE_ANCHOR, add + WIRE_ANCHOR, 1); n += 1

open(P, "w").write(src)
print(f"PATCHED|merge_draft.py|{n} edit(s)")
if n < 5:
    print("WARNING: expected 5 edits, got", n)
    sys.exit(1)
