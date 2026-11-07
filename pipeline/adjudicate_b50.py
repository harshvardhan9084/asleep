#!/usr/bin/env python3
"""adjudicate_b50.py — inject the B50 adjudications into merge_draft.py
(marker: adjudicate_b50, idempotent). Evidence probed from the live CSV +
parsed fulltexts before writing:
  * 2 TIE resolutions via RETARGET_KEEP_PUBLISHED_CODE_OWNER (B19 keeps with
    the published slot-row owners; units land on the name-identity rows)
  * 5 TIER2 same-subject ALLOWs (MBA era accumulators)
  * 1 wrong-subject FORCE_APPEND (recorded B28 ISM class)
"""
import json

M = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
s = open(M).read()
if "adjudicate_b50 marker" in s:
    print("already injected; no-op")
    raise SystemExit(0)

def RTK(key, target, keep, reason):
    return (f'    "{key}": {{\n        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER",\n'
            f'        "target": "{target}",\n'
            f'        "keep_published_codes": {json.dumps(keep)},\n'
            f'        "reason": "{reason}"}},\n')

def ALLOW(key, reason):
    return f'    "{key}": {{\n        "action": "ALLOW",\n        "reason": "{reason}"}},\n'

def FA(key, reason):
    return f'    "{key}": {{\n        "action": "FORCE_APPEND",\n        "reason": "{reason}"}},\n'

UHV_R = ("B50 TIE resolution (B41 corroborating-copy convergence + B49 Maths-IV class): draft 'Universal "
         "Human Values and Professional Ethics' (KVE301/KVE401/KVE301H/KVE401H, the detailed standalone "
         "UHV-II print, 5 verbatim units + objectives) hits a Tier-0 TIE across the flipped-name scheme "
         "slot rows technical-communication-universal-human-values (KVE301 owner, sess blank) and "
         "universal-human-values-technical-communication (KVE401;KAS401 owner, sess 2019-20). RETARGET "
         "pins the update on the KVE401 published owner (name-prefix identity 'Universal Human Values...', "
         "same 2019-20 K-era): the 5 verbatim units + objectives backfill its empty unit fields (GAP "
         "closure per §3); KVE301H/KVE401H (unowned H-variant prints) accumulate into all_codes. "
         "keep_published_codes keeps KVE301 with its published owner technical-communication-universal-"
         "human-values (G2 single ownership; the blank-session flipped pair cannot be ranked by "
         "newest-print-wins, so the conservative B19 keep applies). The flipped-name pair is recorded for "
         "owner reconciliation (B48 legacy (name,course)-variance class) - never silently merged.")

MFG_R = ("B50 TIE resolution (B31 slot-code-to-subject convergence class, conservative form): draft "
         "'MANUFACTURING PROCESS' (ROE030/ROE040, 5 verbatim units - the real OE subject) hits a Tier-0 "
         "TIE across the 2017-18 scheme slot rows science-based-open-elective (ROE030 primary owner) and "
         "mathematics-iii-science-based-open-elective (ROE040 owner). RETARGET pins the update on the "
         "EXACT-NAME row manufacturing-process (sess 2017-18, empty codes AND empty units): the 5 "
         "verbatim units backfill its empty unit fields (GAP closure per §3). Unlike the B31 STAND "
         "(whose pool rows owned G2-exempt RANGE prints 'EOE 031-038'), these slot rows own SPECIFIC "
         "code tokens, so the conservative B19 keep applies: ROE030/ROE040 stay with their published "
         "owners (G2 single ownership; the ROE prints recorded as narrative on the updated row). The "
         "slot-row-to-subject code consolidation is recorded for owner reconciliation.")

block = "    # --- B50 commit-run adjudications (adjudicate_b50 marker) ---\n"
block += RTK("02_btech_s3-4_kve301-401h-universal-human-values-professional-ethics::00::universal-human-values-and-professional-ethics",
             "universal-human-values-technical-communication",
             {"KVE301": "technical-communication-universal-human-values"}, UHV_R)
block += RTK("03_btech_s3-4_roe030-roe040-open-electives-science::00::manufacturing-process",
             "manufacturing-process",
             {"ROE030": "science-based-open-elective",
              "ROE040": "mathematics-iii-science-based-open-elective"}, MFG_R)
block += ALLOW("05_mba_syllabus::17::organisational-behaviour",
    "B50 TIER2 same-subject ALLOW (fuzzy 96, overlap 31): draft 'ORGANISATIONAL BEHAVIOUR' (MBA 112, "
    "UPTU-era master MBA print) vs the MBA organizational-behaviour accumulator (sess 2024-25, unit1 "
    "empty) - z/spelling variant of the same course (recorded singular/plural + spelling-variant "
    "class); tier-2 qualified per RULES §2. Same course MBA per §1b (cross-course guard clean). "
    "Update-first: the no-session print backfills empty unit fields per §3; MBA-112 unowned, "
    "accumulates into code_history.")
block += ALLOW("05_mba_syllabus::20::business-statistics",
    "B50 TIER2 same-subject ALLOW (fuzzy 97, overlap 21): draft 'BUSINESS STATISTICS' (MBA 115) vs the "
    "MBA businessstatistics accumulator (sess 2024-25, unit1 empty) - exact name modulo the subject_id "
    "hyphen artifact; tier-2 qualified per RULES §2. Same course MBA per §1b. Backfill update per §3; "
    "MBA-115 unowned, accumulates.")
block += ALLOW("05_mba_syllabus::22::accounting-and-financial-analysis",
    "B50 TIER2 same-subject ALLOW (fuzzy 100, overlap 42): draft 'ACCOUNTING AND FINANCIAL ANALYSIS' "
    "(MBA 217) vs the MBA financial-accounting-and-analysis accumulator (sess 2025-26, unit1 empty) - "
    "token-set-identical name (word-order variant, recorded era/name-variant class; unit-I shared "
    "distinctive accounting vocabulary: 'Accounting concepts, conventions and principles; Accounting "
    "Equations...' class); tier-2 qualified per RULES §2. Same course MBA per §1b. Backfill update "
    "per §3; MBA-217 unowned, accumulates.")
block += ALLOW("05_mba_syllabus::32::supply-chain-management-scm",
    "B50 TIER2 same-subject ALLOW (fuzzy 92, overlap 29): draft 'Supply Chain Management (SCM)' vs the "
    "MBA supply-chain-management-mba accumulator (sess 2021-22) - exact name modulo the '(SCM)' paren "
    "print (recorded paren-variant class, verifier v17 analogue); tier-2 qualified per RULES §2. Same "
    "course MBA per §1b. Backfill update per §3.")
block += ALLOW("05_mba_syllabus::34::management-information-system-mis",
    "B50 TIER2 same-subject ALLOW (fuzzy 92, overlap 22): draft 'Management Information System (MIS)' "
    "(MBA 218 core) vs the MBA management-information-systems-mba accumulator (sess 2024-25) - the "
    "SAME MIS subject family (this is NOT the recorded B48 ISM divergence: the B48 FORCE_APPEND was "
    "'Information Storage & Management' whose unit-I is the storage-technology print; the present "
    "draft is the MIS core course). Same course MBA per §1b; tier-2 qualified per RULES §2. Backfill "
    "update per §3; MBA-218 unowned, accumulates.")
block += FA("05_mba_syllabus::37::international-business-and-trade",
    "B50 wrong-subject FORCE_APPEND (recorded B28 ISM class): draft 'INTERNATIONAL BUSINESS AND TRADE' "
    "(MBA 412 elective, units = classic IB-THEORY print: u1 'Growth of international business: "
    "Globalisation...'; u2 Porter's model + Prahalad-Doz + FDI/JVs; u4 Absolute/Comparative Advantage "
    "+ Hecksher-Ohlin trade theories; u5 Forex theories - Mint Parity/PPP/BOP) vs the Tier-2 candidate "
    "international-business-strategy (RMBIIB07, sess 2022-23) whose 5 printed units are the FOREIGN-"
    "TRADE PROCEDURE course (u1 'Introduction of prospects of FT...'; u2/u3/u5 market-study/product-"
    "study/SWOT per product category; u4 Product and Market Strategy). Name fuzzy 86 with overlap 14 "
    "is token noise; the unit content DIVERGES COMPLETELY (different u1, different u4) - different "
    "subject despite the name family. Appends as its own row with a cross-reference note to the "
    "strategy row (RULES §4 determine-then-fix, proof kept).")
open(M, "w").write(s.replace("TIER2_OVERRIDES = {\n", "TIER2_OVERRIDES = {\n" + block, 1))
print("injected B50 adjudications: 2 RTK + 5 ALLOW + 1 FORCE_APPEND")
