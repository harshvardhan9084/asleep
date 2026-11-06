#!/usr/bin/env python3
"""adjudicate_b38.py — B38 merge adjudications (marker-guarded, idempotent).

7 live TIE resolutions (roman-numeral/code-lineage classes, all registry-
verified) + 2 wrong-subject FORCE_APPENDs (recorded B30 class) + 1 draft-side
junk-row drop (doc 01 KOE041 instruction-string row, sibling of the doc-03/doc-04
junk rows already patched at verify).
"""
import json

DRAFT = "/home/z/my-project/work/pipeline_v2/drafts_b38_run/01_btech_textile-tech_y2_model-curriculum_2019-20.draft.json"
MERGE = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"

d = json.load(open(DRAFT, encoding="utf-8"))
before = len(d["subjects"])
d["subjects"] = [s for s in d["subjects"]
                 if not (s.get("codes") == ["KOE041"] and not s.get("name") and str(s.get("sessional_ct")) == "..")]
print("doc01 junk rows dropped:", before - len(d["subjects"]))
json.dump(d, open(DRAFT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

src = open(MERGE).read()
if "adjudicate_b38 marker" in src:
    print("already injected")
    raise SystemExit(0)

BLOCK = '''
    # --- B38 adjudications (adjudicate_b38 marker) ---
    "01_btech_textile-tech_y2_model-curriculum_2019-20::01::fabric-manufacturing-ii": {
        "action": "RETARGET", "target": "fabric-manufacture-ii",
        "reason": "B38 TIE resolution (fuzzy 88/-i, 91/-ii, 89/-iii, 86/woven-fabric) on roman-numeral identity + code lineage: draft 'Fabric Manufacturing-II' (KTT402, 2019-20 y2 model-curriculum sem-4 print, 5 verbatim units) — the fabric-manufacture-ii row owns ECT402/ETE402 (the same university course's E-era ladder; KTT402 is its K-era code, cf. the B33 KTT/BPE ladder classes); -i and -iii are different-semester courses; woven-fabric-manufacture is the Handloom-Tech branch course (BHT-551/601). RETARGET pins the update on the numeral-matching -ii row."},
    "02_btech_textile-tech_y2_scheme-syllabus_2017-18::00::environment-ecology": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "environment-ecology",
        "keep_published_codes": {"RVE401": "universal-human-values-professional-ethics"},
        "reason": "B38 TIE resolution (code identity across rows on RAS402/RVE401 — the paired-cell print): draft 'Environment & Ecology' (RAS402/RVE401, 2017-18 y2 scheme print) — the environment-ecology row owns RAS402 (EAS-105/RAS302 ladder) and universal-human-values-professional-ethics owns RVE401; a paired-cell slot print is NOT a subject (recorded SKIP_SLOT_PRINT class) and one row must not absorb both members' codes. RETARGET pins the update on the name-identity environment-ecology row; RVE401 stays with its published owner (B37 NAS-202 same-session class); the paired print is recorded in the slot row environment-ecology-universal-human-values-p."},
    "03_btech_textile-tech_y3_model-curriculum_2020-21::10::advance-weaving-technology": {
        "action": "RETARGET", "target": "advanced-weaving-technology",
        "reason": "B38 TIE resolution (fuzzy 91/advanced-welding-technology vs 98/advanced-weaving-technology): draft 'Advance Weaving Technology' (KTT603, 2020-21 y3 model-curriculum print, 5 verbatim units) — the advanced-weaving-technology row owns RTT603 (the same course's R-era code); the welding row (NME-055/EME-022/RME506) is a DIFFERENT subject sharing only the generic skeleton. RETARGET pins the update on the weaving row (fuzzy 98 + code family RTT603=KTT603 lineage)."},
    "04_btech_textile-tech_y3_syllabus_2024-25::00::yarn-manufacturing-iii": {
        "action": "RETARGET", "target": "yarn-manufacture-iii",
        "reason": "B38 TIE resolution (fuzzy 85/-i, 88/-ii, 90/-iii) on roman-numeral identity + code lineage: draft 'Yarn Manufacturing –III' (BTT502, 2024-25 NEP y3 sem-5 print, 5 verbatim units) — the yarn-manufacture-iii row owns ETE502/RTT502 (the same course's E/R-era ladder; BTT502 is its B-era code). -i/-ii are different-semester courses. RETARGET pins the update on the numeral-matching -iii row."},
    "04_btech_textile-tech_y3_syllabus_2024-25::08::advance-weaving-technology": {
        "action": "RETARGET", "target": "advanced-weaving-technology",
        "reason": "B38 TIE resolution (fuzzy 91/advanced-welding-technology vs 98/advanced-weaving-technology): draft 'Advance Weaving Technology' (BTT603, 2024-25 NEP print, 5 verbatim units) — converges onto the same advanced-weaving-technology row as 03::10 (BTT603 = the B-era code of KTT603/RTT603); the welding row is a different subject."},
    "05_btech_textile-tech_y4_syllabus-cbcs_2019-20::09::process-control-in-spinning-weaving": {
        "action": "FORCE_APPEND",
        "reason": "B38 wrong-family FORCE_APPEND (recorded B30 EMT-011 class + RULES §11): draft 'Process Control in Spinning & Weaving' (RTT085, 2019-20 y4 CBCS DE-5 print, detailed units) — the TIE candidates process-control-in-spinning (ETEF-041) and process-control-in-weaving (ETEF042) are the 2009-10 four-branch-textile DE pool's TWO SEPARATE subjects (spinning-only / weaving-only); the 2019-20 print is a COMBINED course covering both domains in one syllabus. fuzzy 87/85 (both below the identity line) confirms neither candidate is a name variant. Appends as its own row with cross-reference notes to both pool rows; doc 06 (2021-22) prints the same RTT085 course and converges by Tier-1 name identity at commit."},
    "10_btech_y1_syllabus-hindi_2021-22::03::electrical-engineering": {
        "action": "RETARGET", "target": "basic-electrical-engineering",
        "reason": "B38 TIE resolution (fuzzy 89/electronics-engineering vs 88/basic-electrical-engineering) on code lineage: draft 'ELECTRICAL ENGINEERING' (KEE101TH/KEE201TH, 2021-22 y1 print, 5 verbatim units) — the basic-electrical-engineering row owns KEE101/KEE201/KEE-101T/KEE-201T (the same course; 'TH' is this document's theory-suffix print convention and 'ELECTRICAL ENGINEERING' its shortened header form of 'Basic Electrical Engineering'); electronics-engineering is a DIFFERENT subject sharing the generic skeleton. RETARGET pins the update on the KEE101-owner row (equal-session print: fieldwise per §3, source corroboration recorded)."},
    "05_btech_textile-tech_y4_syllabus-cbcs_2019-20::07::textile-marketing-and-merchandising": {
        "action": "FORCE_APPEND",
        "reason": "B38 wrong-subject FORCE_APPEND (recorded B30 class): draft 'Textile Marketing and Merchandising' (RTT071, 2019-20 y4 CBCS DE print, detailed units) — the Tier-2 hit marketing-merchandising-of-carpet-textiles (EACT704, 2009-10 Carpet-Tech DE row, fuzzy 86, overlap 8) is a carpet-specific DIFFERENT subject. Appends as its own row with a cross-reference note; RTT071 unclaimed → the new row owns it."},
    "08_btech_vlsi_y3_syllabus-rev_2025-26::11::analog-integrated-circuit-design": {
        "action": "FORCE_APPEND",
        "reason": "B38 wrong-subject FORCE_APPEND (recorded B30 class): draft 'ANALOG INTEGRATED CIRCUIT DESIGN' (BVL-053, 2025-26 VLSI y3 rev DE print, lecture-plan table units) — the Tier-2 hit integrated-circuits-design (fuzzy 86, overlap 13) is a name-skeleton match on the shared 'integrated circuits design' tokens; the VLSI-branch analog IC design course (op-amp stages, CMOS analog blocks per its printed units) is a DIFFERENT subject from the generic IC-design row. Appends as its own row owning the unclaimed BVL053 with cross-reference notes."},
'''
anchor = "TIER2_OVERRIDES = {"
i = src.find(anchor)
assert i > 0
j = i + len(anchor)
src = src[:j] + BLOCK + src[j:]
open(MERGE, "w").write(src)
print("injected 9 B38 TIER2_OVERRIDES entries")
