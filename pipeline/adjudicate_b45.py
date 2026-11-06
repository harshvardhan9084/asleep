#!/usr/bin/env python3
"""adjudicate_b45.py — inject the B45 TIER2_OVERRIDES adjudications into
merge_draft.py (marker: adjudicate_b45) + draft-side fixes:
  * AUC-001/002 alternative-pair slot prints -> non_subject_rows (B43/B28 class)
  * doc-05 KMTT101/105/106/151/251/201/205/206/207/152/252 association quirks
    (three agreeing orderings: p.2 scheme row order + footer code list +
    detail-page order — B44 doc-04 class)
  * crossref quirks on the FORCE_APPEND rows (02::10, 07::14)
Evidence: registry rows + parsed fulltext probed before writing (b45_probe_flags).
"""
import json, re

M = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
MARK45 = "    # --- B45 commit-run adjudications (adjudicate_b45 marker) ---\n"


def A(key, fuzzy, ov, draft, tgt, extra=""):
    """ALLOW entry."""
    return f'''    "{key}": {{
        "action": "ALLOW",
        "reason": "B45 TIER2 same-subject ALLOW (fuzzy {fuzzy}, overlap {ov}): draft '{draft}' vs the MBA {tgt[0]} accumulator ({tgt[1]}, sess {tgt[2]}){extra}. Tier-2 qualified per RULES §2 (same course MBA per §1b; name-variant/era class recorded). Update-first: fieldwise update; older prints corroborate code_history, newer prints win fieldwise per §3."}},'''


def RT(key, target, reason):
    return f'''    "{key}": {{
        "action": "RETARGET",
        "target": "{target}",
        "reason": "{reason}"}},'''


def RTK(key, target, keep, reason):
    return f'''    "{key}": {{
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER",
        "target": "{target}",
        "keep_published_codes": {json.dumps(keep)},
        "reason": "{reason}"}},'''


def FA(key, reason):
    return f'''    "{key}": {{
        "action": "FORCE_APPEND",
        "reason": "{reason}"}},'''


E = []
# ---- TIE resolutions (3) ----
E.append(RT("04_mba_tourism_syllabus_2014-15::13::cost-management-accounting",
            "cost-and-management-accounting",
            "B45 TIE resolution (fuzzy 93/cost-and-management-accounting vs 89/management-accounting) per the recorded B41/B44 CMA class: the name-identical higher-fuzzy joint Cost+Management-Accounting accumulator (BMB207;KMHC207;MBA026;NMBA026) takes the print; draft MBTM026 u1 ('Introduction: Accounting for Management, Role of Cost in decision making, Comparison of Management Accounting and Cost Accounting') is the same CMA core as the row's u1 ('Meaning, nature and scope of Management Accounting; Difference between management accounting and financial accounting, Cost concept...'). 2014-15 older than 2024-25 -> backfill/source-history only; MBTM026 joins code_history."))
E.append(RT("10_mba_y2_model-curriculum-rev-aicte_2019-20::06::investment-analysis-portfolio-management",
            "investment-and-portfolio-management",
            "B45 TIE resolution (fuzzy 95/investment-analysis-and-portfolio-management vs 91/investment-and-portfolio-management) on CONTENT evidence: draft KMBFM01 u1 ('Overview of Capital Market: Market of securities, Stock Exchange and New Issue Markets - their nature...') is VERBATIM-shared with the investment-and-portfolio-management row's u1 ('Investments (10 hrs) Overview of Capital Market: Market of securities, Stock Exchange and New Issue Markets - their nature, struct...'), while the higher-fuzzy 2026-27 row's u1 is the redesigned 'Module I: Conceptual Framework of Investments' print. The KMBFM01 (2019-20) print belongs to the BMBFM01 (2025-26) design lineage; the name is the &/and + 'Analysis' variant (recorded classes). The 2026-27 Module-I row corroborates as the same FM-elective family print."))
E.append(RT("10_mba_y2_model-curriculum-rev-aicte_2019-20::26::sales-retail-management",
            "sales-and-retail-management",
            "B45 TIE resolution (fuzzy 92/sales-and-retail-management vs 85/retail-management) per the B41 name-identical-higher-fuzzy class: draft KMBMK01 u1 ('Introduction to Sales: Role of selling in marketing, Personal selling, Salesmanship and sales manager, Types of...') is verbatim-shared with the sales-and-retail-management row's u1 ('Introduction to Sales: Role of selling in marketing, Personal selling, Types of sales personnel...'); the retail-management row (MBAMK4, 2008-09 scheme-only print) keeps its own row (its draft sibling 08::44 updates it by code)."))

# ---- name-variant / era ALLOWs (recorded classes) ----
E.append(A("01_mba_tourism-mgmt_syllabus_2016-17::04::business-statistics", 97, 42, "Business Statistics",
           ("business-statistics", "KMBAI205;RAS206;BMBAI-205;MBA015;NMBA015", "2024-25"),
           " — name-identical modulo spacing (BUSINESSSTATISTICS single-token print); u1 'Measures of Central tendency – Mean' core shared; RMT104 unowned, joins code_history"))
E.append(A("01_mba_tourism-mgmt_syllabus_2016-17::05::organizational-behavior", 98, 39, "ORGANIZATIONAL BEHAVIOR",
           ("organizational-behaviour", "KMBAI202;RMBI201;BMBAI-201;MBA014;KMT105", "2024-25"),
           " — behaviour/behavior + z/s spelling variants (recorded B40/B43 classes); u1 'Introduction to OB: The meaning of OB' core shared; RMT105 unowned, joins"))
E.append(A("04_mba_tourism_syllabus_2014-15::04::business-statistics", 97, 33, "BUSINESS STATISTICS",
           ("business-statistics", "KMBAI205;RAS206;BMBAI-205;MBA015;NMBA015", "2024-25"),
           " — same row + class as 01::04 (the 2014-15 corroborating print); MBTM015 unowned, joins"))
E.append(A("04_mba_tourism_syllabus_2014-15::08::managing-human-resources", 86, 45, "Managing Human Resources",
           ("human-resource-management", "BMBAB202;KMBF202;BMBF202;KMBA204-era HRM accumulator", "2025-26"),
           " — recorded B42 context-print class (managing-human-resources → human-resource-management); u1 'Human Resources Management (HRM): Meaning, Nature and Scope, Difference between HRM and Personnel Management' core shared; MBTM021 unowned, joins"))
E.append(A("04_mba_tourism_syllabus_2014-15::09::business-laws", 96, 47, "BUSINESS LAWS",
           ("business-law", "KMBAI203;RMBI202;BMBAI401;MBA022;NMBA022", "2025-26"),
           " — singular/plural print variant (recorded class); u1 'The Indian Contract Act, 1872 Definition of a Contract and its essentials' core shared; MBTM022 unowned, joins"))
E.append(A("04_mba_tourism_syllabus_2014-15::14::travel-agency-and-tour-operations", 95, 107, "TRAVEL AGENCY AND TOUR OPERATIONS",
           ("travel-agency-and-tour-operators", "KMT208", "2018-19"),
           " — operators/operations print variant (recorded class); u1 'Travel formalities: Travel Formalities: Passport, Visa, Health requirements...' VERBATIM-shared; MBTM027 unowned, joins"))
E.append(A("05_mba_travel-tourism_y1_syllabus_2020-21::04::tourism-concepts-practices", 88, 31, "TOURISM: CONCEPTS & PRACTICES",
           ("tourism-concepts-impacts", "KMT206", "2018-19"),
           " — recorded B28 era-rewording class (AICTE-model redesign, not a different subject): u5 'Tourism Organizations: ... United Nations World Tourism Organization (WTO), Pacific Asia Travel Association(PATA)...' matches the row's u5 organizations core verbatim ('Origin, location and functions of WTO, IATA, PATA, ASTA, UFTAA'); u1 definitions/history core shared; the 2020-21 print is NEWER -> fieldwise wins per §3 (KMTT105 unowned, joins)"))
E.append(A("05_mba_travel-tourism_y1_syllabus_2020-21::16::travel-agency-and-tour-operations", 95, 88, "TRAVEL AGENCY AND TOUR OPERATIONS",
           ("travel-agency-and-tour-operators", "KMT208", "2018-19"),
           " — same row + class as 04::16; u1 'Introduction to Travel Trade: Historical Background of Travel Trade, Significance of Travel Agency Business' core shared; KMTT208 unowned, joins; 2020-21 newer -> fieldwise wins per §3"))
E.append(A("07_mba_y1_model-curriculum_2018-19::04::organizational-behavior", 98, 37, "ORGANIZATIONAL BEHAVIOR",
           ("organizational-behaviour", "KMBAI202;RMBI201;BMBAI-201;MBA014;KMT105", "2024-25"),
           " — same row + class as 01::05; KMB105 unowned, joins"))
E.append(A("07_mba_y1_model-curriculum_2018-19::11::corporate-financial-management", 88, 74, "CORPORATE FINANCIAL MANAGEMENT",
           ("financial-management-corporate-finance", "KMBF204;BMBF204;KMBA204;BMBA204;KMBN204;BMB204;BMLS204", "2025-26"),
           " — recorded B42 accumulator class (5th print); u1 'Introduction to Finance & Corporate Finance: Finance & its scope...' VERBATIM-shared with the row's u1; the 2018-19 model-curriculum name 'CORPORATE FINANCIAL MANAGEMENT' is the era print of the same FM course; KMB204 unowned, joins"))
E.append(A("07_mba_y1_model-curriculum_2018-19::13::quantitative-techniques-in-management", 86, 92, "Quantitative Techniques in Management",
           ("quantitative-techniques-for-manager", "BMBAB206;KMBF206;BMBF206;KMBA206;BMBA206;KMBN206;BMB206", "2025-26"),
           " — name-variant class ('in Management' vs 'FOR MANAGER' era prints); u1 'Operations Research Introduction... Scope of Operations Research, Phases of Operations Research' core shared with the row's 'Unit I (6 Hrs)-Operations Research & Decision-Making Environments...'; KMB206 unowned, joins"))
E.append(A("09_mba_y1_scheme_2016-17::03::business-statistics", 97, 38, "BUSINESS STATISTICS",
           ("business-statistics", "KMBAI205;RAS206;BMBAI-205;MBA015;NMBA015", "2024-25"),
           " — same row + class as 01::04; RMB104 unowned, joins"))
E.append(A("09_mba_y1_scheme_2016-17::04::organizational-behavior", 98, 38, "ORGANIZATIONAL BEHAVIOR",
           ("organizational-behaviour", "KMBAI202;RMBI201;BMBAI-201;MBA014;KMT105", "2024-25"),
           " — same row + class as 01::05; RMB105 unowned, joins"))
E.append(A("09_mba_y1_scheme_2016-17::12::management-accounting-and-control", 92, 65, "Management Accounting And Control",
           ("cost-and-management-accounting", "BMB207;KMHC207;MBA026;NMBA026", "2024-25"),
           " — the 2016-17 RMB-era y1 name of the CMA course ('and Control' era tail, recorded B41 CMA class); u1 'Introduction: Nature and scope of cost Accounting and Management Accounting, Cost Accounting VS Management Accounting vs Financial Accounting' core shared; RMB205 unowned, joins"))
E.append(A("10_mba_y2_model-curriculum-rev-aicte_2019-20::08::financial-market-and-services", 85, 37, "Financial Market and Services",
           ("financial-markets-products-and-services", "FM02;BMBF-306", "2026-27"),
           " — name-variant class ('and Services' vs 'Products and Services' era prints); u1 'Structure of Indian financial system: An overview...' core shared with the row's 'Module I: Financial System and Market Structure (10 Hours)...'; KMBFM03 unowned, joins"))
E.append(A("10_mba_y2_model-curriculum-rev-aicte_2019-20::09::working-capital-management", 95, 48, "Working Capital Management",
           ("management-of-working-capital", "MBAFM01;RMBFM04", "2017-18"),
           " — word-order print variant (recorded B39 class); u1 'Introduction to Working Capital (10 Hrs) Nature, Scope and Definition of Working Capital, Types of working Capital, Determinants...' VERBATIM-shared; KMBFM04 unowned, joins"))
E.append(A("10_mba_y2_model-curriculum-rev-aicte_2019-20::19::international-trade-law", 98, 124, "International Trade Law",
           ("international-trade-laws", "KMBIIB08;KMBNIB05", "2022-23"),
           " — singular/plural print variant (recorded class); u1 '(6 Hours) The World Trade Organization: Introduction to International trade and the law of the WTO, Sources of WTO Law...' VERBATIM-shared; KMBIB04 unowned, joins"))
E.append(A("10_mba_y2_model-curriculum-rev-aicte_2019-20::22::web-technology-e-commerce", 93, 77, "Web Technology & E-Commerce",
           ("web-technology-and-e-commerce", "RMBIT02", "2017-18"),
           " — &/and print variant (recorded class); u1 'History of Web and Internet...' core shared; KMBIT02 unowned, joins"))
E.append(A("10_mba_y2_model-curriculum-rev-aicte_2019-20::25::system-analysis-design", 92, 38, "System Analysis & Design",
           ("system-analysis-and-design", "KMBIIT03;RMBIT05", "2021-22"),
           " — &/and print variant; u1 'Systems: Concept & Characteristics of a System, Elements of System, Types of Systems' core shared with the row's 'System Concepts and Information Systems Environment: The System Concept: Definition, Characteristics of Systems...'; KMBIT05 unowned, joins"))
E.append(A("10_mba_y2_model-curriculum-rev-aicte_2019-20::27::consumer-behaviour-marketing-communication", 99, 95, "Consumer Behaviour & Marketing Communication",
           ("consumer-behavior-marketing-communication", "KMBI MK01;KMBNMK01;MBA034", "2021-22"),
           " — behaviour/behavior spelling variant (recorded class); u1 'Introduction: Introduction to Consumer Behavior...' core shared; KMBMK02 unowned, joins"))
E.append(A("10_mba_y2_model-curriculum-rev-aicte_2019-20::31::supply-chain-logistics-management", 94, 36, "Supply Chain & Logistics Management",
           ("logistics-and-supply-chain-management-mba", "BMBAI502;KMBNOM01;BMBOM01;BMLS106;KMLS106", "2026-27"),
           " — word-order + &/and print variants (recorded B39 class); u1 'Supply Chain Concepts: Objectives of a Supply Chain, Stages of Supply chain, Value Chain Process, Cycle view...' core shared (the row's u1 is the same intro-SCM curriculum per the recorded B44 04::05 evidence); KMBOM01 unowned, joins"))
E.append(A("10_mba_y2_model-curriculum-rev-aicte_2019-20::32::operations-planning-and-control", 93, 103, "Operations Planning and Control",
           ("operations-planning-control", "KMBNOM02", "2021-22"),
           " — &/and print variant; u1 'Introduction: Meaning and objective of Production Planning & Control, functions, roles & responsibilities of PPC manager...' VERBATIM-shared; KMBOM02 unowned, joins"))

# ---- content-evidence RETARGETs (beyond fuzzy) ----
E.append(RT("01_mba_tourism-mgmt_syllabus_2016-17::01::management-concepts-and-applications",
            "management-concepts-and-organisational-behaviour",
            "B45 RETARGET below the fuzzy threshold on unit evidence (recorded B43 combined-print class): draft RMT101 u1 ('Management practices from past to present, Different levels of management, Managerial skills, Roles& Functions, Manager and Business environment. (7 hours)') is near-verbatim the concepts+OB accumulator's u1 ('Fundamentals of Management: Management practices from past to present, Different levels of management, Managerial skills and Managerial Functions...'); the 2016-17 RMT-era y1 name 'Management Concepts and Applications' is the era print of the same AICTE-model course. RMT101 unowned, joins code_history."))
E.append(RT("01_mba_tourism-mgmt_syllabus_2016-17::08::computer-applications-and-management-information-system",
            "computer-applications-in-management",
            "B45 RETARGET below the fuzzy threshold on unit evidence: draft RMT108 u1 ('Unit I (05 hours) Introduction Hardware: (a) Input devices - keyboard, printing devices, voice speech devices, scanner, MICR, OMR, Bar code reader...') is verbatim the computer-applications-in-management row's u1 ('UNIT I (05 hours) Conceptual Framework Hardware: (a) Input devices - keyboard...'); the row already owns KMT108 (the 2018-19 tourism print of the same course) + MBA017; RMT108 joins."))
E.append(RT("01_mba_tourism-mgmt_syllabus_2016-17::13::management-accounting-control",
            "cost-and-management-accounting",
            "B45 RETARGET below the fuzzy threshold on unit evidence (recorded B41 CMA class): draft RMT205 u1 ('Introduction: Nature and scope of cost Accounting and Management Accounting, Cost Accounting VS Management Accounting vs Financial Accounting') is topic-identical to the CMA accumulator's u1 ('Meaning, nature and scope of Management Accounting; Difference between management accounting and financial accounting, Cost concept...') and near-verbatim the 09::12 sibling's u1 (which the ladder itself resolved to this row at fuzzy 92/overlap 65); the '& Control' tail is the 2016-17 era print. RMT205 unowned, joins."))
E.append(RT("01_mba_tourism-mgmt_syllabus_2016-17::00::comprehaensive-viva",
            "comprehensive-viva",
            "B45 RETARGET (codeless print-typo row): draft 'Comprehaensive Viva' is the VERBATIM p.2 print typo of 'Comprehensive Viva' (RULES §6 — kept in name_print with quirk); the scheme row prints NO code (no-code evidence quirk recorded); the comprehensive-viva accumulator already owns the tourism-era viva print KMT209 (2018-19), so the 2016-17 RMT-era scheme print corroborates the same accumulator. Codeless: nothing joins code_history; source_history only. Zero-GAP holds (the subject owns a row)."))
E.append(RT("07_mba_y1_model-curriculum_2018-19::07::computer-applications-and-management-information-system",
            "computer-applications-in-management",
            "B45 RETARGET below the fuzzy threshold on unit evidence: draft KMB108 u1 ('UNIT I (05 hours) Conceptual Framework Hardware: (a) Input devices - keyboard...') is verbatim the row's u1; the 2018-19 scheme prints 'KMB108 COMPUTER APPLICATION IN MANAGEMENT' while the detail page (p.19) prints 'Computer Applications and Management Information System KMB108' — both forms of the same course the row owns (KMBAI105;RCS102;MBA017;KMT108); KMB108 joins."))
E.append(RT("08_mba_y1_scheme_2008-09::01::accounting-financial-analysis",
            "financial-accounting-and-analysis",
            "B45 RETARGET superseding the B21 code-slot-collision auto: the 2008-09 scheme's 'Accounting & Financial Analysis' (MBA 012) is the SAME print the B44 book doc (06::02) ALLOWed onto the financial-accounting-and-analysis accumulator per the recorded B39 transposed-word-order class ('ACCOUNTING AND FINANCIAL ANALYSIS' vs 'Financial Accounting and Analysis') — collapsed-name similarity 0.70 mis-measures the transposed pair; the recorded B39/B44 adjudication governs. MBA012 stays owned by the accumulator (no transfer); the scheme row corroborates (2008-09 older -> backfill/source-history only)."))
E.append(RT("08_mba_y1_scheme_2008-09::14::managing-human-resources",
            "human-resource-management",
            "B45 RETARGET superseding the B21 code-slot-collision auto per the recorded B42 context-print class ('managing-human-resources' → 'human-resource-management', printed evidence recorded in B44): the 2008-09 scheme's 'Managing Human Resources' (MBA 028) is the same print B44's book doc already consolidated onto the HRM accumulator; MBA028 stays owned (no transfer); the scheme row corroborates."))
E.append(RT("09_mba_y1_scheme_2016-17::00::management-concepts-and-application",
            "management-concepts-and-organisational-behaviour",
            "B45 RETARGET on unit evidence (same row + class as 01::01): draft RMB101 u1 ('Management practices from past to present, Different levels of management, Managerial skills, Roles& Functions...') near-verbatim the accumulator's u1; the 2016-17 RMB-era y1 print is the same AICTE-model course; RMB101 unowned, joins."))
E.append(RT("09_mba_y1_scheme_2016-17::07::computer-applications-and-management-information-system",
            "computer-applications-in-management",
            "B45 RETARGET on unit evidence (same row + class as 01::08): draft RMB108 u1 ('Unit I (05 hours) Conceptual Framework Hardware: (a) Input devices...') verbatim the row's u1; RMB108 unowned, joins."))
E.append(RT("09_mba_y1_scheme_2016-17::13::production-operations-and-supply-chain-management",
            "operations-management",
            "B45 RETARGET below the fuzzy threshold on unit-structure evidence (recorded era-rename class): draft RMB206's five units ('Production Concept...' / 'Operation Concept...' / 'Material and Inventory Management Types of production planning...' / 'Supply Chain Management Conceptual model of SCM, Supply chain drivers...' / 'Productivity and Quality TQM, Deming's 14 principles, PDCA cycle - KAIZEN...') follow the IDENTICAL topic chain as the operations-management accumulator's units (which owns NMBA027 'Production & Operations Management' 2013-14 + RMBI405); u3/u4/u5 cores verbatim-shared. The 2016-17 name adds 'Supply Chain' (the era print of the same course). RMB206 unowned, joins."))
E.append(RT("09_mba_y1_scheme_2016-17::16::comprehaensive-viva",
            "comprehensive-viva",
            "B45 RETARGET (print-typo row, same class as 01::00): draft 'Comprehaensive Viva' is the verbatim print typo of 'Comprehensive Viva'; the RMB209 code is unowned and joins the accumulator's code_history (the accumulator owns KMBI406;RMBI406;RMBI606;KMT209). Zero-GAP holds."))
E.append(RT("03_mba_tourism-mgmt_y2_model-curriculum_2019-20::10::mice-and-hospitality-management",
            "event-hospitality-management",
            "B45 RETARGET to the row appended EARLIER IN THIS COMMIT by 02::10's FORCE_APPEND (intra-batch cascade; the live commit re-ladder sees the appended row): draft KMT403 u1/u2 ('Concept of MICE, Scope - Nature and Importance – Types of Events in MICE...' / 'Important Events Organization Agencies. History & Functions of ICCA, Role of ICPB...') are VERBATIM-identical to the 2017-18 RMT401 print's u1/u2 — the 2019-20 'MICE and Hospitality Management' name is the era print of the same course. 2019-20 NEWER than 2017-18 -> fieldwise wins per §3."))
E.append(RT("05_mba_travel-tourism_y1_syllabus_2020-21::09::computerized-reservation-system",
            "computerized-reservation-system",
            "B45 RETARGET to the row appended EARLIER IN THIS COMMIT by 02::07 'Computerized Reservation System' (RMT305, 2017-18) — intra-batch cascade (both docs print the same-titled course; the commit re-ladder resolves): the 2020-21 KMTT201 print is newer -> fieldwise wins per §3. (If the ladder's live plan already resolves by T1 name-identity, this entry is a recorded no-op stand.)"))
E.append(RT("05_mba_travel-tourism_y1_syllabus_2020-21::13::tourism-marketing",
            "tourism-marketing",
            "B45 RETARGET to the row appended EARLIER IN THIS COMMIT by 03::09 'Tourism Marketing' (KMT305? 2019-20) — intra-batch cascade stand: the 2020-21 KMTT205 print is newer -> fieldwise wins per §3. (Recorded no-op stand if the live ladder already T1-matches.)"))
E.append(RT("05_mba_travel-tourism_y1_syllabus_2020-21::15::cultural-tourism-in-india",
            "cultural-tourism-in-india",
            "B45 RETARGET to the row appended EARLIER IN THIS COMMIT by 03::07 'Cultural Tourism in India' — intra-batch cascade stand: the 2020-21 KMTT207 print is newer -> fieldwise wins per §3. (Recorded no-op stand if the live ladder already T1-matches.)"))
E.append(RT("06_mba_travel-tourism_y2_syllabus_2021-22::05::global-tourism-geography",
            "geography-of-international-tourism",
            "B45 RETARGET to the row appended EARLIER IN THIS COMMIT by 02::08 'Geography of International Tourism' (RMT306; 03::05 corroborates verbatim) — intra-batch cascade on the recorded B28 era-rewording class: the 2021-22 'GLOBAL TOURISM GEOGRAPHY' (KMTT305) is the AICTE redesign print of the same tourism-geography course (u1 geography-elements/climate/importance core shared; u2 IATA areas/codes/GMT is the expanded print of the maps/date-line/time core). 2021-22 NEWEST -> fieldwise wins per §3."))

# ---- keep-published-code-owner RETARGETs (B20/B25 class; the 3 CODE-REASSIGNED autos) ----
E.append(RTK("08_mba_y1_scheme_2008-09::27::management-of-financial-institutions-services",
             "management-of-financial-institutions-and-services",
             {"MBAFM03": "management-of-financial-institutions-and-services"},
             "B45 KEEP-PUBLISHED-CODE-OWNER (recorded B20/B25 class, superseding the name-transfer auto): the &-form draft name is the print variant of the AND-form accumulator that ALREADY owns MBAFM03 (consolidated in B44 from the 2008-09 book's MBA FM 03 detail print); the 2004-05 MBAFM3 row is a DIFFERENT token (MBAFM3 vs MBAFM03) and keeps its own row; the 2008-09 scheme print corroborates the accumulator (older -> backfill/source-history only). G2 clean: no transfer."))
E.append(RTK("08_mba_y1_scheme_2008-09::28::tax-panning-financial-reporting",
             "tax-planning-management",
             {"MBAFM04": "tax-planning-management"},
             "B45 KEEP-PUBLISHED-CODE-OWNER (B20/B25 class, superseding the name-transfer auto): the scheme's 'Tax Panning & Financial Reporting' is the print of MBA FM 04 whose B44 label-verification recorded the book's own print as 'TAX PLANNING AND MANAGEMENT' (zero-guess page-anchored verification); 'Panning' is a verbatim print typo of 'Planning' (RULES §6 — kept in name_print with quirk) and the accumulator already owns MBAFM04. G2 clean: no transfer."))
E.append(RTK("08_mba_y1_scheme_2008-09::43::sales-distribution-management",
             "sales-and-distribution-management",
             {"MBAMK03": "sales-and-distribution-management"},
             "B45 KEEP-PUBLISHED-CODE-OWNER (B20/B25 class, superseding the name-transfer auto): the &-form draft name is the print variant of the AND-form accumulator that ALREADY owns MBAMK03 (B44 book consolidation); the RMBMK01-era sales-distribution-management row keeps its own row pending the owner's variant-name reconciliation (recorded open item); the 2008-09 scheme print corroborates the accumulator. G2 clean: no transfer."))

# ---- FORCE_APPENDs (wrong-subject / split classes) ----
E.append(FA("02_mba_tourism-mgmt_syllabus_2017-18::10::event-hospitality-management",
            "B45 wrong-subject FORCE_APPEND (recorded B28 same-core-different-tail split class): draft 'Event & Hospitality Management' (RMT401, 2017-18) units I-III are the MICE/EVENT core ('Concept of MICE...', 'Important Events Organization Agencies. History & Functions of ICCA, Role of ICPB...', 'Introduction to Event Planning...') with ZERO counterpart in the hospitality-management row (RMBI802;MBAOP02 — all five units are hotel/hospitality operations: front office, housekeeping, F&B, supporting departments, hotel economics); units IV-V overlap the hotel core topically only. Updating the row would (a) drop the MICE units (older session -> backfill-only) violating zero-GAP, or (b) overwrite the hotel accumulator with a combined-events design. The draft appends as its own row; crossref note to hospitality-management recorded in quirks. The 2019-20 KMT403 sibling (03::10) RETARGETs onto this row (verbatim u1/u2)."))

ENTRIES = MARK45 + "\n".join(E) + "\n"

src = open(M).read()
if "adjudicate_b45 marker" in src:
    # remove the superseded stray ALLOW if a previous injection included it
    stray = '    "02_mba_tourism-mgmt_syllabus_2017-18::10::event-hospitality-management": {\n        "action": "ALLOW",\n        "reason": "B45 TIER2 same-subject ALLOW (fuzzy 88, overlap 30): draft \'Event & Hospitality Management\' vs the MBA hospitality-management accumulator (RMBI802;MBAOP02, sess 2020-21) — (see FORCE_APPEND: superseded; this ALLOW entry is not used because units I-III diverge)'
    if stray in src:
        src = src.replace(stray + "},\n", "", 1)
        open(M, "w").write(src)
        print("removed superseded stray ALLOW entry")
    else:
        print("B45 entries already injected (clean)")
else:
    anchor = "    # --- B44 commit-run adjudications (adjudicate_b44 marker) ---\n"
    assert anchor in src, "B44 marker not found"
    src = src.replace(anchor, ENTRIES + anchor, 1)
    open(M, "w").write(src)
    print(f"injected {len(E)} B45 entries")

# ---------------- draft-side fixes ----------------
# 1. AUC pair -> non_subject_rows (B43/B28 slot class)
stem = "04_mba_tourism_syllabus_2014-15"
p = f"{DRAFTS}/{stem}.draft.json"
d = json.load(open(p))
moved = []
keep = []
for s in d["subjects"]:
    codes = [re.sub(r"[^A-Z0-9]", "", c.upper()) for c in (s.get("codes") or [])]
    if any("AUC001" in c or "AUC002" in c for c in codes) and any("alternative_pair" in str(f) for f in (s.get("flags") or [])):
        moved.append(s)
    else:
        keep.append(s)
if moved:
    for s in moved:
        d.setdefault("non_subject_rows", []).append({
            "kind": "alternative_pair_slot_print",
            "print": (s.get("name_print") or s.get("name") or "") + " | codes " + ";".join(s.get("codes") or []),
            "locator": "2014-15 scheme pp.4-5 (AUC-001/AUC-002 alternative pair; B43/B28 slot class — members own BTech rows; MBA slot print is program structure)"})
        d.setdefault("quirks", []).append(
            "AUC-001/AUC-002 alternative-pair scheme slot prints moved to non_subject_rows (recorded B43/B28 class: a slot print is program structure, not a subject; the member subjects UHV/Cyber-Security own BTech rows per §1b course boundary)")
    d["subjects"] = keep
    json.dump(d, open(p, "w"), indent=1, ensure_ascii=False)
    print(f"AUC pair moved to non_subject_rows ({len(moved)} rows; subjects now {len(keep)})")

# 2. doc-05 association quirks (three agreeing orderings)
stem = "05_mba_travel-tourism_y1_syllabus_2020-21"
p = f"{DRAFTS}/{stem}.draft.json"
d = json.load(open(p))
FOOTER = {"KMTT101", "KMTT105", "KMTT106", "KMTT151", "KMTT152", "KMTT201", "KMTT205", "KMTT206", "KMTT207", "KMTT251", "KMTT252"}
n = 0
for s in d["subjects"]:
    cs = {c.replace(" ", "").upper() for c in (s.get("codes") or [])}
    if cs & FOOTER and not any("three agreeing orderings" in q for q in (s.get("quirks") or [])):
        s.setdefault("quirks", []).append(
            "code not printed on the subject's own detail page; associated via three agreeing orderings — p.2 scheme table row order (empty code cell), p.2 footer code list (KMTT101 KMTT105 KMTT106 KMTT151 KMTT152 KMTT201 KMTT205 KMTT206 KMTT207 KMTT251 KMTT252), and detail-page order (recorded B44 doc-04 class)")
        n += 1
json.dump(d, open(p, "w"), indent=1, ensure_ascii=False)
print(f"doc-05 association quirks added: {n}")

# 3. crossref quirks for the FORCE_APPEND rows
for stem, code, note in [
    ("02_mba_tourism-mgmt_syllabus_2017-18", "RMT401",
     "kept separate from the hospitality-management accumulator (RMBI802;MBAOP02): units I-III are the MICE/event core not printed in that row (same name family, different course design — B28 split class)"),
    ("07_mba_y1_model-curriculum_2018-19", "KMB207",
     "kept separate from the business-law (KMBAI203-era) and business-environment-legal-aspect-of-business (KMBA201-era) rows: unit compositions differ (NI Act u2, Companies Act u3, IT Act u5 not printed in those rows; same law-course family — B28 split class)"),
]:
    p = f"{DRAFTS}/{stem}.draft.json"
    d = json.load(open(p))
    for s in d["subjects"]:
        if code in [c.replace(" ", "") for c in (s.get("codes") or [])]:
            if not any("kept separate" in q for q in (s.get("quirks") or [])):
                s.setdefault("quirks", []).append("crossref: " + note)
                print("crossref quirk:", stem[:2], code)
    json.dump(d, open(p, "w"), indent=1, ensure_ascii=False)
