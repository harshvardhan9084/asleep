#!/usr/bin/env python3
"""adjudicate_b44.py — inject the B44 TIER2_OVERRIDES adjudications into
merge_draft.py (marker: adjudicate_b44). Evidence: registry rows + parsed
fulltext verified before writing.

Classes exercised (all recorded in prior manifests):
  * name-variant ALLOWs: singular/plural, and/&-, z/s + behaviour/behavior,
    transposed word order (B39), context-print (B42), era-family.
  * B43 overlap-0 name-identity ALLOWs ×4 — the 2004-05 elective-book rows
    (MBAHR2/MBAHR4) are scheme-row-only with EMPTY unit text, so unit/CO
    vocab overlap is structurally impossible; name identity + same MBA-HR
    group slot + newer-session backfill is the recorded remedy.
  * B41 TIE class ×2 — CMA draft subjects RETARGETed to the name-identical
    higher-fuzzy joint cost+MA accumulator (BMB207).
  * B28 wrong-subject FORCE_APPEND ×1 — BMLS402 Risks Management vs the
    generic SCM intro row (unit-level evidence, zero shared curriculum).
"""
import json

MARK = "    # --- B44 commit-run adjudications (adjudicate_b44 marker) ---\n"

def A(key, fuzzy, ov, draft, tgt, extra=""):
    tgt_name, tgt_codes, tgt_sess = tgt
    return f'''    "{key}": {{
        "action": "ALLOW",
        "reason": "B44 TIER2 same-subject ALLOW (fuzzy {fuzzy}, overlap {ov}): draft '{draft}' vs the MBA {tgt_name} accumulator ({tgt_codes}, sess {tgt_sess}){extra}. Tier-2 qualified per RULES §2 (fuzzy {fuzzy} >= 85, shared distinctive unit terms {ov} >= 3; same course MBA per §1b so the cross-course guard does not apply). Update-first: fieldwise update of the existing row; the newer-session print wins fieldwise, older prints corroborate code_history."}},'''

E = []
E.append(A("01_mba_healthcare-hospital_s2_syllabus_2022-23::04::operation-research", 97, 42,
    "OPERATION RESEARCH", ("operations-research", "KMBI502;RMBI502", "2020-21"),
    " — singular/plural print variant (recorded class); draft unit-I ('Definition of operations research, models of operations research, scientific methodology...') is the same OR-core curriculum as the row's unit-I ('Operations Research: Uses, Scope and Applications of Operation Research in managerial decision-making...'); KMHC205 unowned, accumulates"))
E.append(A("02_mba_healthcare-hospital_syllabus_2022-23::00::management-concepts-organisational-behaviour", 96, 110,
    "MANAGEMENT CONCEPTS & ORGANISATIONAL BEHAVIOUR", ("management-concepts-and-organisation", "KMBA101;BMBA101;KMBN101;BMB101;BMBF101;BMBAB101", "2025-26"),
    " — B43 context-print class (concepts+OB combined-print of the healthcare program) with 110 shared distinctive terms"))
E.append(A("03_mba_logistics-scm_y1_syllabus-rev_2024-25::03::business-statistics-and-analytics", 94, 117,
    "BUSINESS STATISTICS & ANALYTICS", ("business-statistics-analytics", "BMBAB104;KMBF104;BMBF104;KMBA104;BMBA104;KMBN104", "2025-26"),
    " — 117 shared distinctive terms, name-identical modulo &/and"))
E.append(A("03_mba_logistics-scm_y1_syllabus-rev_2024-25::12::financial-management-and-corporate-finance", 95, 100,
    "FINANCIAL MANAGEMENT AND CORPORATE FINANCE", ("financial-management-corporate-finance", "KMBF204;BMBF204;KMBA204;BMBA204;KMBN204;BMB204", "2025-26"),
    " — the recorded B42 Financial-Management-and-Corporate-Finance multi-print accumulator class (4th print)"))
E.append(A("04_mba_logistics-scm_y1_syllabus_2020-21::05::basics-of-supply-chain-logistics-management", 88, 29,
    "BASICS OF SUPPLY CHAIN & LOGISTICS MANAGEMENT", ("logistics-and-supply-chain-management", "BMBAI502;KMBNOM01;BMBOM01", "2026-27"),
    " — B39 word-order + B42 context-print classes; draft unit-I ('Supply Chain Concepts: Objectives of a Supply Chain, Stages of Supply chain, Value Chain Process, Cycle view...') is the same intro-SCM curriculum as the row's unit-I ('Concept, evolution, scope, and objectives of supply chain management; logistics and supply chain integration...')"))
E.append(A("04_mba_logistics-scm_y1_syllabus_2020-21::12::financial-management-and-corporate-finance", 95, 100,
    "FINANCIAL MANAGEMENT AND CORPORATE FINANCE", ("financial-management-corporate-finance", "KMBF204;BMBF204;KMBA204;BMBA204;KMBN204;BMB204", "2025-26"),
    " — same row + class as 03::12 (the 2020-21 corroborating print of the B42 accumulator)"))
E.append(A("06_mba_syllabus_2008-09::00::principles-practice-of-management", 99, 37,
    "PRINCIPLES & PRACTICE OF MANAGEMENT", ("principles-practices-of-management", "KMBAI102;RMBI101", "2018-19"),
    " — singular/plural print variant (recorded class); MBA 011 is the establishing 2008-09 print"))
E.append(A("06_mba_syllabus_2008-09::02::accounting-and-financial-analysis", 100, 45,
    "ACCOUNTING AND FINANCIAL ANALYSIS", ("financial-accounting-and-analysis", "BMBAB103;KMBF103;BMBF103;KMBA103;BMBA103;KMBN103", "2025-26"),
    " — B39 transposed-word-order print variant of the same AFA course"))
E.append(A("06_mba_syllabus_2008-09::03::organisational-behaviour", 96, 45,
    "ORGANISATIONAL BEHAVIOUR", ("organizational-behavior", "KMBAI202;RMBI201;BMBAI-201", "2024-25"),
    " — z/s + behaviour/behavior spelling variants (recorded B40/B43 classes)"))
E.append(A("06_mba_syllabus_2008-09::04::business-statistics", 97, 33,
    "BUSINESS STATISTICS", ("business-statistics", "KMBAI205;RAS206;BMBAI-205", "2024-25"),
    " — name-identical modulo era; draft MBA 015 is the establishing 2008-09 print"))
E.append(A("06_mba_syllabus_2008-09::09::business-laws", 96, 41,
    "BUSINESS LAWS", ("business-law", "KMBAI203;RMBI202;BMBAI401", "2025-26"),
    " — singular/plural print variant; draft unit-I ('Contract Act, 1872...') verbatim-matches the row's Contract-Act core"))
E.append(A("06_mba_syllabus_2008-09::12::production-operations-management", 94, 27,
    "PRODUCTION & OPERATIONS MANAGEMENT", ("production-and-operations-management", "BMBAI402", "2025-26"),
    " — and/&- print variant; draft unit-I ('Operations Management – An overview...') is the same POM core"))
E.append(A("06_mba_syllabus_2008-09::15::managing-human-resources", 86, 44,
    "MANAGING HUMAN RESOURCES", ("human-resource-management", "KMBI404;RMBI404;BMBAI301;BMBAB202;KMBF202;BMBF202", "2025-26"),
    " — B42 context-print class ('Managing Human Resources' = the HRM course, 44 shared distinctive terms"))
E.append(A("06_mba_syllabus_2008-09::18::management-information-system", 98, 22,
    "MANAGEMENT INFORMATION SYSTEM", ("management-information-systems", "KMBN208;BMB208", "2024-25"),
    " — singular/plural print variant; draft unit-I ('Concept of Data and Information, Information Systems...') is the MIS core"))
E.append(A("06_mba_syllabus_2008-09::25::tax-planning-and-management", 92, 33,
    "TAX PLANNING AND MANAGEMENT", ("tax-planning-management", "BMBF-303;BMBFM02", "2025-26"),
    " — name-identical modulo spacing; MBA FM 04 2008-09 is the establishing print of the FM-group Tax Planning course"))
E.append(A("06_mba_syllabus_2008-09::33::international-logistic-management", 99, 10,
    "INTERNATIONAL LOGISTIC MANAGEMENT", ("international-logistics-management", "KMBIIB07;KBNIB3", "2022-23"),
    " — singular/plural print variant (logistic/logistics) of the same IB-group course (MBA IB 04 vs IB-07 print); 10 shared distinctive terms >= 3"))
E.append(A("06_mba_syllabus_2008-09::42::insurance-risk-management", 93, 27,
    "INSURANCE & RISK MANAGEMENT", ("insurance-and-risk-management", "BMBF-405", "2025-26"),
    " — and/&- print variant; draft unit-I ('Introduction and Scope of Insurance- Historical perspective...') verbatim-matches the row's insurance core"))
E.append(A("07_mba_syllabus_2013-14::04::business-statistics", 97, 34,
    "BUSINESS STATISTICS", ("business-statistics", "KMBAI205;RAS206;BMBAI-205", "2024-25"),
    " — name-identical modulo era; NMBA 015 is the 2013-14 corroborating print (same row + class as 06::04)"))
E.append(A("07_mba_syllabus_2013-14::08::managing-human-resources", 86, 44,
    "MANAGING HUMAN RESOURCES", ("human-resource-management", "KMBI404;RMBI404;BMBAI301;BMBAB202;KMBF202;BMBF202", "2025-26"),
    " — same row + class as 06::15 (the 2013-14 corroborating print)"))
E.append(A("07_mba_syllabus_2013-14::09::business-laws", 96, 47,
    "BUSINESS LAWS", ("business-law", "KMBAI203;RMBI202;BMBAI401", "2025-26"),
    " — singular/plural print variant; draft unit-I ('The Indian Contract Act, 1872...') verbatim-matches the row's Contract-Act core"))
E.append(A("07_mba_syllabus_2013-14::23::insurance-risk-management", 93, 31,
    "INSURANCE & RISK MANAGEMENT", ("insurance-and-risk-management", "BMBF-405", "2025-26"),
    " — same row + class as 06::42 (the 2013-14 corroborating print)"))
E.append(A("07_mba_syllabus_2013-14::31::tax-planning-and-management", 92, 32,
    "TAX PLANNING AND MANAGEMENT", ("tax-planning-management", "BMBF-303;BMBFM02", "2025-26"),
    " — same row + class as 06::25 (the 2013-14 corroborating print)"))
E.append(A("08_mba_syllabus_2017-18::07::security-analysis-portfolio-management", 95, 112,
    "SECURITY ANALYSIS & PORTFOLIO MANAGEMENT", ("security-analysis-and-portfolio-management", "KMBIFM01", "2021-22"),
    " — and/&- print variant (recorded B43 class) with 112 shared distinctive terms"))
E.append(A("08_mba_syllabus_2017-18::13::performance-reward-management", 94, 90,
    "PERFORMANCE & REWARD MANAGEMENT", ("performance-and-reward-management", "KMBIHR03;BMBAHR03;KMBNHR04;BMBHR03", "2025-26"),
    " — and/&- print variant with 90 shared distinctive terms; RMB HR 01 is the 2017-18 print"))
E.append(A("08_mba_syllabus_2017-18::26::system-analysis-design", 92, 34,
    "SYSTEM ANALYSIS & DESIGN", ("system-analysis-and-design", "KMBIIT03", "2021-22"),
    " — and/&- print variant; RMB IT 03 is the 2017-18 print of the IT-group SAD course"))
E.append(A("10_mba_tourism-mgmt_syllabus-rev-aicte_2018-19::04::organizational-behavior", 98, 36,
    "ORGANIZATIONAL BEHAVIOR", ("organizational-behavior", "KMBAI202;RMBI201;BMBAI-201", "2024-25"),
    " — z/s + behaviour/behavior spelling variants (recorded B40/B43 classes); KMT 105 is the 2018-19 AICTE-rev print"))

# B43 overlap-0 name-identity class x4 (2004-05 elective-book rows are scheme-row-only with EMPTY unit text)
NOU = (" — B43 overlap-0 name-identity class: the 2004-05 elective-book row is scheme-row-only with EMPTY unit text "
       "(unit1 blank by print), so unit/CO vocab overlap is structurally impossible; evidence is name identity + the same "
       "MBA-HR specialization-group slot + the newer-session draft fieldwise-backfilling the empty row (RULES §3 backfill)")
E.append(A("06_mba_syllabus_2008-09::27::industrial-relations-and-labour-enactments", 95, 0,
    "INDUSTRIAL RELATIONS AND LABOUR ENACTMENTS", ("industrial-relations-labour-enactments", "MBAHR2", "2004-05"), NOU))
E.append(A("06_mba_syllabus_2008-09::29::negotiation-counselling", 98, 0,
    "NEGOTIATION & COUNSELLING", ("negotiation-counseling", "MBAHR4", "2004-05"), NOU))
E.append(A("07_mba_syllabus_2013-14::33::industrial-relations-and-labour-enactments", 95, 0,
    "INDUSTRIAL RELATIONS AND LABOUR ENACTMENTS", ("industrial-relations-labour-enactments", "MBAHR2", "2004-05"), NOU))
E.append(A("07_mba_syllabus_2013-14::34::negotiation-counselling", 98, 0,
    "NEGOTIATION & COUNSELLING", ("negotiation-counseling", "MBAHR4", "2004-05"), NOU))

# B41 TIE class x2 — CMA
TIE = (" — B41 TIE resolution class: the two candidate rows are 'MANAGEMENT ACCOUNTING' (BMBAI-203;KMBI302;RMBI302, "
       "sess 2024-25 — the IB-group pure Management Accounting specialization course, fuzzy 89) and 'COST AND MANAGEMENT "
       "ACCOUNTING' (BMB207, sess 2024-25 — the MBA-common joint cost+MA course, fuzzy 93). The draft ('COST & MANAGEMENT "
       "ACCOUNTING', unit-I 'Introduction: Accounting for Management, Role of Cost in decision making, Comparison of "
       "Management Accounting [with Financial Accounting]...') carries the JOINT cost+management-accounting curriculum "
       "and is name-identical (and/& modulo) to the higher-fuzzy BMB207 accumulator, which takes the print per the recorded "
       "higher-fuzzy-name-identical rule; the pure Management Accounting row keeps its own specialization print")
E.append('''    "06_mba_syllabus_2008-09::13::cost-management-accounting": {
        "action": "RETARGET", "target": "cost-and-management-accounting",
        "reason": "B44 TIE resolution''' + TIE + ''' (draft MBA 026, 2008-09 establishing print)"},
    "07_mba_syllabus_2013-14::13::cost-management-accounting": {
        "action": "RETARGET", "target": "cost-and-management-accounting",
        "reason": "B44 TIE resolution''' + TIE.replace("MBA 026, 2008-09 establishing print", "NMBA 026, 2013-14 corroborating print — same row + class as 06::13") + '''"},
''')

# B28 wrong-subject FORCE_APPEND x1
E.append('''    "05_mba_logistics-scm_y2_syllabus_2025-26::08::risks-management-in-supply-chain-and-logistics": {
        "action": "FORCE_APPEND",
        "reason": "B44 wrong-subject FORCE_APPEND (recorded B28 class, unit-level evidence): the Tier-2 hit (fuzzy 89, overlap 26) on the 'Logistics and Supply Chain Management' accumulator (BMBAI502;KMBNOM01;BMBOM01) is a name-collision — the draft 'RISKS MANAGEMENT IN SUPPLY CHAIN AND LOGISTICS' (BMLS402, 2025-26) unit-I is risk-management curriculum ('Risk Management: Concept and Process, An Action-Based Framework for Supply Chain Risk, Identification of Operational Risks...') while the row's unit-I is the generic SCM intro ('Concept, evolution, scope, and objectives of supply chain management...') — DIFFERENT curricula sharing supply-chain vocabulary. No dedicated risks-management row exists in MBA. Appended as its own row with a cross-reference note; BMLS402 unowned."},''')

ENTRIES = MARK + "\n".join(E) + "\n"

src = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
text = open(src).read()
if "adjudicate_b44 marker" in text:
    print("already injected")
else:
    anchor = "    # --- B40 commit-run adjudications (adjudicate_b40 marker) ---\n"
    assert anchor in text, "B40 marker not found"
    text = text.replace(anchor, ENTRIES + anchor, 1)
    open(src, "w").write(text)
    print("injected %d B44 TIER2_OVERRIDES entries" % (len(E)))

# --- addendum: commit-mode cascade flags (intra-batch matches vs rows appended earlier in the SAME commit;
#     dry-run plans are computed against the pre-commit CSV so these only surface in commit mode) ---
MARK_B = "    # --- B44 commit-cascade adjudications (adjudicate_b44b marker) ---\n"
ENTRIES_B = MARK_B + '''    "08_mba_syllabus_2017-18::10::working-capital-management": {
        "action": "ALLOW",
        "reason": "B44 TIER2 same-subject ALLOW (fuzzy 95, overlap 99) vs the 'MANAGEMENT OF WORKING CAPITAL' row appended earlier in THIS commit from the 2008-09 establishing print (MBA FM 01) — intra-batch cascade match (dry-run plans are computed against the pre-commit CSV so the match only surfaces in commit mode): name-identical modulo word order, 99 shared distinctive unit terms ('Nature, Scope and Definition of Working Capital, Working Capital Cycle, Assessment and Computation of Working Capital Requirement...' both sides). Tier-2 qualified per RULES §2; update-first: the 2008-09 print is the establishing session, the 2017-18 RMB FM 04 print corroborates fieldwise."},
    "08_mba_syllabus_2017-18::31::integrated-marketing-communication": {
        "action": "ALLOW",
        "reason": "B44 TIER2 same-subject ALLOW (fuzzy 99, overlap 68) vs the 'Integrated Marketing Communications' row appended earlier in THIS commit from the 2013-14 print (NMBA MK 02) — intra-batch cascade match (same commit-mode-only class as 08::10): singular/plural print variant (recorded class), 68 shared distinctive unit terms ('Marketing Communication: Objectives of Marketing Communication...' both sides). Tier-2 qualified per RULES §2; update-first: the 2013-14 print establishes, the 2017-18 RMB MK 05 print corroborates fieldwise."},
'''
src = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
text = open(src).read()
if "adjudicate_b44b marker" in text:
    print("addendum already injected")
else:
    anchor = "    # --- B44 commit-run adjudications (adjudicate_b44 marker) ---\n"
    assert anchor in text, "B44 marker not found"
    text = text.replace(anchor, ENTRIES_B + anchor, 1)
    open(src, "w").write(text)
    print("injected 2 cascade entries")
