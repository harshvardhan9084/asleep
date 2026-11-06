#!/usr/bin/env python3
"""adjudicate_b42.py — inject the B42 TIER2_OVERRIDES adjudications into
merge_draft.py (marker: adjudicate_b42). Evidence: registry rows + parsed
fulltext verified before writing. 2 same-subject ALLOWs (Tier-2 qualified:
fuzzy >= 85 AND shared-distinctive-term overlap >= 3, same course per §1b;
word-order/BFSI-print variants per the recorded B39 word-order class)."""
import json

MARK = "    # --- B42 commit-run adjudications (adjudicate_b42 marker) ---\n"
ENTRIES = '''    "01_mba-integrated_y3_syllabus_2026-27::08::corporate-governance-ethics": {
        "action": "ALLOW",
        "reason": "B42 TIER2 same-subject ALLOW (fuzzy 86, overlap 22): draft 'Corporate Governance & Ethics' (BMBAI603, MBA 2026-27 y3 NEP print) vs the MBA business-ethics-corporate-governance accumulator (KMBI601;RMBI601, sess 2020-21) — transposed word-order print variant of the same two-concept course (recorded B39 word-order class; same course MBA per §1b so the cross-course guard does not apply). Tier-2 qualified: fuzzy 86 >= 85 with 22 shared distinctive unit terms >= 3. Update-first: the 2026-27 print is the newer session — fieldwise update of the existing MBA row; BMBAI603 unowned, accumulates into code_history."},
    "10_mba_banking-fin-services_y2_syllabus_2025-26::06::customer-relationship-management-in-bfsi": {
        "action": "ALLOW",
        "reason": "B42 TIER2 same-subject ALLOW (fuzzy 89, overlap 26): draft 'CUSTOMER RELATIONSHIP MANAGEMENT IN BFSI' (BMBF-307, MBA 2025-26 Banking-Financial-Services specialization print) vs the MBA customer-relationship-management row (BMBAI306, sess 2025-26, established by the 2025-26 MBA-integrated y2 print) — same course MBA per §1b; draft unit-I explicitly covers the generic CRM core ('Concept, Evolution and Importance of CRM; CRM in Banking, Financial Services and Insurance; CRM Process; Customer Life Cycle; Customer Expectations and Satisfaction...') i.e. the BFSI-context print of the MBA CRM course, NOT a divergent-tail split (recorded B28 same-core-different-tail class does not apply: 26 shared distinctive terms). Tier-2 qualified: fuzzy 89 >= 85, overlap 26 >= 3. Update-first: fieldwise update; BMBF-307 unowned, accumulates into code_history with the BFSI print recorded in source_history."},
'''

src = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
text = open(src).read()
if "adjudicate_b42 marker" in text:
    print("already injected")
else:
    anchor = "    # --- B40 commit-run adjudications (adjudicate_b40 marker) ---\n"
    assert anchor in text, "B40 marker not found"
    text = text.replace(anchor, ENTRIES + anchor, 1)
    open(src, "w").write(text)
    print("injected 2 B42 TIER2_OVERRIDES entries")
