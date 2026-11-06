#!/usr/bin/env python3
"""adjudicate_b42_live.py — second-wave B42 adjudications: the LIVE ladder
re-ran inside commit after same-batch updates shifted accumulator rows (the
recorded B41 lesson: the reassignment executor's post-plan strip creates
same-batch TIER2 flags). Evidence = the ladder's own fuzzy/overlap scores on
the live registry + verbatim draft units; all candidates are SAME-COURSE
(MBA) per the §1b-scoped ladder."""
MARK = "    # --- B42-live commit-run adjudications (adjudicate_b42_live marker) ---\n"
ENTRIES = '''    "09_mba_banking-fin-services_y1_syllabus_2025-26::02::financial-accounting-analysis": {
        "action": "ALLOW",
        "reason": "B42-live TIER2 same-subject ALLOW (fuzzy 94, overlap 102): draft 'FINANCIAL ACCOUNTING& ANALYSIS' (BMBF 103, MBA 2025-26 BFSI y1 print) vs the MBA financial-accounting accumulator — 102 shared distinctive unit terms is conclusive same-subject evidence (B41 ALLOW class cited overlaps 70-88); same course MBA per §1b. Update-first: 2025-26 is the newest session — fieldwise update; BMBF103 accumulates."},
    "09_mba_banking-fin-services_y1_syllabus_2025-26::10::quantitative-techniques-for-managers": {
        "action": "ALLOW",
        "reason": "B42-live TIER2 same-subject ALLOW (fuzzy 99, overlap 111): draft 'QUANTITATIVE TECHNIQUES FOR MANAGERS' (BMBF 206, MBA 2025-26 BFSI y1 print) vs the MBA quantitative-techniques accumulator — 111 shared distinctive unit terms, conclusive; same course MBA. Update-first fieldwise update; BMBF206 accumulates."},
    "10_mba_banking-fin-services_y2_syllabus_2025-26::01::financial-credit-and-risk-analysis": {
        "action": "ALLOW",
        "reason": "B42-live TIER2 name-identity ALLOW (fuzzy 100, overlap 0): draft 'FINANCIAL CREDIT AND RISK ANALYSIS' (BMBF 351-era BFSI y2 2025-26 print) vs the same-named MBA row established this same batch from the 2022-23 MBA-integrated y5 print (KMBIFM05, objectives_only_no_units_printed — its units column is empty by print design) — overlap 0 is an artifact of the empty-units counterpart, not divergence; name-identity + same course MBA + same finance-specialization family per the update-first rule. Fieldwise update; the BFSI code accumulates with both prints in source_history."},
    "10_mba_banking-fin-services_y2_syllabus_2025-26::03::investment-and-portfolio-management": {
        "action": "ALLOW",
        "reason": "B42-live TIER2 same-subject ALLOW (fuzzy 89, overlap 43): draft 'INVESTMENT AND PORTFOLIO MANAGEMENT' (BMBF 2025-26 BFSI y2 print) vs the MBA investment-management accumulator — 43 shared distinctive unit terms, conclusive; same course MBA. Update-first fieldwise update; the BFSI code accumulates."},
    "10_mba_banking-fin-services_y2_syllabus_2025-26::05::financial-markets-and-services": {
        "action": "ALLOW",
        "reason": "B42-live TIER2 same-subject ALLOW (fuzzy 87, overlap 60): draft 'FINANCIAL MARKETS AND SERVICES' (BMBF 2025-26 BFSI y2 print) vs the MBA financial-markets accumulator — 60 shared distinctive unit terms, conclusive; same course MBA. Update-first fieldwise update; the BFSI code accumulates."},
    "10_mba_banking-fin-services_y2_syllabus_2025-26::10::foreign-exchange-and-risk-management": {
        "action": "ALLOW",
        "reason": "B42-live TIER2 same-subject ALLOW (fuzzy 86, overlap 73): draft 'FOREIGN EXCHANGE AND RISK MANAGEMENT' (BMBF 2025-26 BFSI y2 print) vs the MBA foreign-exchange accumulator — 73 shared distinctive unit terms, conclusive; same course MBA. Update-first fieldwise update; the BFSI code accumulates."},
    "10_mba_banking-fin-services_y2_syllabus_2025-26::13::research-project-report-and-viva-voce": {
        "action": "ALLOW",
        "reason": "B42-live TIER2 name-identity ALLOW (fuzzy 94, overlap 0): draft 'RESEARCH PROJECT REPORT AND VIVA VOCE' (BMBF-451, MBA 2025-26 BFSI y2 print) vs the same-named MBA project row established this same batch (KMBI1051 scheme_row_only print, 2022-23 — project/viva rows carry no unit structure by print design, so overlap 0 is an artifact); same course MBA, identical course genre per the recorded B41 lab/project row class. Update-first fieldwise update; BMBF-451 accumulates with both prints in source_history."},
'''

src = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
text = open(src).read()
if "adjudicate_b42_live marker" in text:
    print("already injected")
else:
    anchor = "    # --- B40 commit-run adjudications (adjudicate_b40 marker) ---\n"
    assert anchor in text, "B40 marker not found"
    text = text.replace(anchor, ENTRIES + anchor, 1)
    open(src, "w").write(text)
    print("injected 7 B42-live TIER2_OVERRIDES entries")
