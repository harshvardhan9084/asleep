#!/usr/bin/env python3
"""b07_d03_append.py — complete draft 03 (btech_ag_y2_scheme-syllabus_2017-18):
append RAG401/402/403 + RAG451-454 (7 subjects) + non_subject_rows + quirks.
All strings verbatim from the parsed fulltext (pp.2-3 scheme, pp.12-18 details).
Incremental: 3 append phases. Idempotent: skips codes already present.
"""
import json

DRAFT = "/home/z/my-project/work/pipeline_v2/drafts/03_btech_ag_y2_scheme-syllabus_2017-18.draft.json"

THEORY_MARKS = {"sessional_ct": 20, "sessional_ta": 10, "sessional_total": 30, "ese_te_pe": 70, "total": 100}
LAB_MARKS = {"sessional_ct": 30, "sessional_ta": 20, "sessional_total": 50, "ese_te_pe": 50, "total": 100}

S401_1 = "Introduction to farm mechanization. Classification of farm machines. Unit operation in crop production. Hitching systems and controls of farm machinery. Calculation of field capacity and field efficiency."
S401_2 = "Introduction to seed-bed preparation . Familiarization with land reclamation and earth moving equipment. Machinery used for primary tillage, secondary tillage, rotary tillage, deep tillage and minimum tillage and conservation tillage. Measurement of draft of tillage tools and calculations for power requirement for the tillage machines.Tillage machines like mould-board plough, disc plough, chisel plough, sub-soiler, harrows, cultivators, Identification of major functional components. Attachments with tillage machinery."
S401_3 = "Introduction to sowing, planting & transplanting equipment. Working of seed drills, no-till drills, happy seeder and strip-till drills. Brief description and working of planters, bed-planters and other planting equipment. Study of types of furrow openers and metering systems in drills and planters. Calibration of seed-drills/ planters. Adjustments during operation. Introduction to materials used in construction of farm machines. Heat treatment processes and their requirement in farm machines. Properties of materials used for critical and functional components of agricultural machines. Introduction to steels and alloys for agricultural application. Identification of heat treatment processes specially for the agricultural machinery components."
S401_4 = "Selection of farm machinery. Calculation for economics of machinery usage comprasion of owenering with hiring of machinries and analysis of payback period of farm machinery."

S402_1 = "Applications of unit operations and principles in cleaning and grading, aspiration, scalping; size separators, screens, sieve analysis, capacity and effectiveness of screens. Various types of separators: specific gravity, magnetic, disc, spiral, pneumatic, inclined draper, velvet roll, colour sorters, cyclone, shape graders. Size reduction: principle, Bond's law, Kick's law, Rittinger's law, procedure (crushing, impact, cutting and shearing), And Size reduction machinery: Jaw crusher, Hammer mill, Plate mill, Ball mill. Material handling equipment. Types of conveyors: Belt, roller, chain and screw."
S402_2 = "Elevators: bucket, Cranes & hoists. Trucks (refrigerated/ unrefrigerated), Pneumatic conveying. Drying: moisture content and water activity; Free, bound and equilibrium moisture content, isotherm, hysteresis effect, EMC determination, Psychrometric chart and its use in drying, Drying principles and theory, Thin layer and deep bed drying analysis, Falling rate and constant rate drying periods, maximum and decreasing drying rate period, drying equations, Mass and energy balance, Shedd's equation, Dryer performance, Different methods of drying, batch-continuous; mixing-non-mixing, Sun-mechanical, conduction, convection, radiation, superheated steam, tempering during drying, Different types of grain dryers: bin, flat bed, LSU, columnar, RPEC, fluidized, rotary and tray."
S402_3 = "Mixing: Theory of mixing of solids and pastes, Mixing index, types of mixers for solids, liquid foods and pastes. Milling of rice: Conditioning and parboiling, advantages and disadvantages, traditional methods, CFTRI and Jadavpur methods, Pressure parboiling method, Types of rice mills, Modern rice milling, different unit operations and equipment. Milling of wheat, unit operations and equipment."
S402_4 = "Milling of pulses: traditional milling methods, commercial methods, pre-conditioning, dry milling and wet milling methods: CFTRI and Pantnagar methods. Pulse milling machines, Milling of corn and its products. Dry and wet milling. Milling of oilseeds: mechanical expression, screw press, hydraulic press, solvent extraction methods, preconditioning of oilseeds, refining of oil, stabilization of rice bran., Extrusion cooking: principle, factors affecting, single and twin screw extruders. By-products utilization."

S403_1 = "Hydrologic cycle, precipitation and its forms, rainfall measurement and estimation of mean rainfall, frequency analysis of point rainfall. Mass curve, hyetograph, depth-area-duration curves and intensity-duration-frequency relationship. Hydrologic processes-Interception, infiltration -factors influencing, measurement and indices. Evaporation - Estimation and measurement. Runoff - Factors affecting, measurement, and stage - discharge rating curve, estimation of peak runoff rate and volume, rational method, Cook's method and SCS curve number method."
S403_2 = "Geomorphology of watersheds - Linear, aerial and relief aspects of watersheds- stream order, drainage density and stream frequency. Hydrograph - Components, base flow separation, unit hydrograph theory, S-curve, synthetic hydrograph, applications and limitations. Stream gauging - discharge rating curves, flood peak, design flood and computation of probable flood. Flood routing - channel and reservoir routing. Drought - classification causes and impacts, drought management strategy."
S403_3 = "Soil erosion - Introduction, causes and types - geological and accelerated erosion, agents, factors affecting and effects of erosion. Water erosion - Mechanics and forms - splash, sheet, rill, gully, ravine and stream bank erosion. Gullies - Classification, stages of development. Soil loss estimation - Universal soil loss equation (USLE) and modified USLE. Rainfall erosivity - estimation by KE>25 and EI30 methods. Soil erodibility - topography, crop management and conservation practice factors. Measurement of soil erosion - Runoff plots, soil samplers."
S403_4 = "Water erosion control measures - agronomical measures - contour farming, strip cropping, conservation tillage and mulching. Engineering measures- Bunds and terraces. Bunds - contour and graded bunds - design and surplussing arrangements. Terraces - level and graded broad base terraces, bench terraces - planning, design and layout procedure, contour stonewall and trenching."
S403_5 = "Gully and ravine reclamation - principles of gully control - vegetative measures, temporary structures and diversion drains. Grassed waterways and design. Wind erosion- Factors affecting, mechanics, soil loss estimation and control measures - vegetative, mechanical measures, wind breaks and shelter belts and stabilization of sand dunes. Land capability classification. Rate of sedimentation, silt monitoring and storage loss in tanks."

def subj(name, np_, codes, sem, ltp, credit, marks, stype, units, books=None, refs=None, exps=None, scheme_rows=None, quirks=None):
    d = {"name": name, "name_print": np_, "codes": codes, "semester": sem, "ltp": ltp,
         "credit": credit, "marks": marks, "subject_type": stype, "units": units}
    if books: d["textbooks"] = books
    if refs: d["reference_books"] = refs
    if exps: d["experiments"] = exps
    if scheme_rows: d["scheme_rows"] = scheme_rows
    d["quirks"] = quirks or []
    d["flags"] = []
    return d

PHASE1 = [
    subj("Farm Machinery and Equipment-I", "RAG401: FARM MACHINERY AND EQUIPMENT-I", ["RAG401"], 4,
         {"l": 3, "t": 0, "p": 0}, 3, dict(THEORY_MARKS), "core",
         {"1": S401_1, "2": S401_2, "3": S401_3, "4": S401_4},
         books=[{"no": 1, "book": "Kepner RA, Roy Barger & EL Barger. Principles of Farm Machinery."},
                {"no": 2, "book": "Smith HP and LH Wilkey. Farm Machinery and Equipment."},
                {"no": 3, "book": "Culpin Claude. Farm Machinery."},
                {"no": 4, "book": "Srivastava AC. Elements of Farm Machinery."},
                {"no": 5, "book": "Lal Radhey and AC Datta. Agricultural Engineering. through solved examples, Saroj Publication, Allahabad,"}],
         scheme_rows=[{"semester": 4, "print": "4. RAG401 | Farm Machinery and Equipment-I | 3-0-0 | 70 | 20 | 10 | 100 | 3 (2nd Year IV-SEMESTER scheme, p.3)"}],
         quirks=["Unit-IV verbatim typos kept: 'comprasion of owenering with hiring of machinries' (p.12)",
                 "Unit-II 'machines.Tillage' missing space after period kept verbatim (p.12)",
                 "Reading-list heading prints 'Suggested Reading:' (not Text Books) (p.12)"]),
    subj("Post Harvest Engg. of Cereals, Pulses & Oil Seeds", "RAG402: POST HARVEST ENGG. OF CEREALS, PULSES & OIL SEEDS", ["RAG402"], 4,
         {"l": 3, "t": 0, "p": 0}, 3, dict(THEORY_MARKS), "core",
         {"1": S402_1, "2": S402_2, "3": S402_3, "4": S402_4},
         books=[{"no": 1, "book": "Chakraverty, A. Post Harvest Technology of cereals, pulses and oilseeds. Oxford & IBH publishing Co. Ltd., New Delhi."},
                {"no": 2, "book": "Dash, S.K., Bebartta, J.P. and Kar, A. Rice Processing and Allied Operations. Kalyani Publishers, New Delhi."},
                {"no": 3, "book": "Sahay, K.M. and Singh, K.K. 1994. Unit operations of Agricultural Processing. Vikas Publishing house Pvt. Ltd. New Delhi."},
                {"no": 4, "book": "Geankoplis C. J. Transport processes and unit operations, Prentice Hall of India Pvt Ltd, New Delhi"},
                {"no": 5, "book": "Earle, R.L. 2003. Unit Operations in Food Processing. Pergamon Press. Oxford. U.K."},
                {"no": 6, "book": "Henderson, S.M., and Perry, R. L. Agricultural Process Engineering, Chapman and hall, London"},
                {"no": 7, "book": "McCabe, W.L., Smith J.C. and Harriott, P. Unit operations of Chemical Engineering. McGraw Hill."},
                {"no": 8, "book": "Singh, R. Paul. and Heldman, R.Dennis. 2004. Introduction to Food Engineering. 3rd Edition. Academic Press, London."}],
         scheme_rows=[{"semester": 4, "print": "5. RAG402 | Post Harvest Engg. of Cereals, Pulses & Oil Seeds | 3-0-0 | 70 | 20 | 10 | 100 | 3 (2nd Year IV-SEMESTER scheme, p.3)"}],
         quirks=["Unit-I mid-sentence 'And Size reduction machinery:' capitalization kept verbatim (p.13)",
                 "Unit-IV 'stabilization of rice bran.,' punctuation kept verbatim (p.13)",
                 "Suggested Reading list continues across page break p.13->p.14 (items 1-5 / 6-8) (p.13-14)"]),
    subj("Watershed Hydrology, Soil & Water Conservation Engineering", "RAG403: WATERSHED HYDROLOGY, SOIL & WATER CONSERVATION ENGINEERING", ["RAG403"], 4,
         {"l": 3, "t": 1, "p": 0}, 4, dict(THEORY_MARKS), "core",
         {"1": S403_1, "2": S403_2, "3": S403_3, "4": S403_4, "5": S403_5},
         books=[{"no": 1, "book": "Raghunath, HM, 2006. Hydrology: Principles Analysis and Design. Revised 2nd Edition, New Age International (P) Limited Publishers, New Delhi."},
                {"no": 2, "book": "Subramanya, K. 2008. Engineering Hydrology. 3rd Edition, Tata McGraw-Hill Publishing Co., New Delhi."},
                {"no": 3, "book": "Chow, VT, D.R. Maidment and L.W. Mays. 2010. Applied Hydrology, McGraw Hill Publishing Co., New York."},
                {"no": 4, "book": "Jaya Rami Reddy, P. 2011. A Text Book of Hydrology. University Science Press, New Delhi."},
                {"no": 5, "book": "Linsley, R.K., MA Kohler, and JLH Paulhus. 1984. Hydrology for Engineers. McGraw-Hill Publishing Co., Japan."},
                {"no": 6, "book": "Singh Gurmel, C. Venkataraman, G. Sastry and B.P. Joshi. 1996. Manual of Soil and Water Conservation Practices. Oxford and IBH Publishing Co. Pvt. Ltd., New Delhi."},
                {"no": 7, "book": "Mahnot, S.C. 2014. Soil and Water Conservation and Watershed Management. International Books and Periodicals Supply Service, New Delhi."},
                {"no": 8, "book": "Mal, BC 2014. Introduction to Soil and Water Conservation Engineering. 2014. Kalyani Publishers."},
                {"no": 9, "book": "Michael, AM and TP Ojha. 2003. Principles of Agricultural Engineering. Volume II. 4th Edition, Jain Brothers, New Delhi."}],
         scheme_rows=[{"semester": 4, "print": "6. RAG403 | Watershed Hydrology, Soil & Water Conservation Engineering 3-1-0 | 70 | 20 | 10 | 100 | 4 (2nd Year IV-SEMESTER scheme, p.3; LTP runs into title line in text layer)"}],
         quirks=["Book 8 prints year '2014' twice: 'Mal, BC 2014. ... Engineering. 2014.' kept verbatim (p.16)",
                 "Suggested Reading list continues across page break p.15->p.16 (items 1-2 / 3-9) (p.15-16)",
                 "Scheme title line wrap glues LTP: '...Conservation Engineering 3-1-0' in text layer (p.3)"]),
]

def lab(name, np_, codes, exps, sr, quirks):
    return subj(name, np_, codes, 4, {"l": 0, "t": 0, "p": 2}, 1, dict(LAB_MARKS), "lab",
                {}, exps=exps, scheme_rows=sr, quirks=quirks)

PHASE2 = [
    lab("Farm Machinery and Equipment-I Lab", "RAG451: FARM MACHINERY AND EQUIPMENT-I LAB", ["RAG451"],
        [{"no": 1, "exp": "Familiarization with different farm implements and tools."},
         {"no": 2, "exp": "Study of hitching systems, Problems on machinery management."},
         {"no": 3, "exp": "Study of primary and secondary tillage machinery - construction, operation, adjustments and calculations of power and draft requirements."},
         {"no": 4, "exp": "Study of sowing and planting equipment - construction, types, calculation for calibration and adjustments."},
         {"no": 5, "exp": "Study of transplanters - paddy, vegetable, etc."},
         {"no": 6, "exp": "Identification of materials of construction in agricultural machinery and study of material properties."},
         {"no": 7, "exp": "Study of heat treatment processes subjected to critical components of agricultural machinery."}],
        [{"semester": 4, "print": "7. RAG451 | Farm Machinery and Equipment-I Lab | 0-0-2 | 50 | 30 | 20 | 100 | 1 (2nd Year IV-SEMESTER scheme, p.3)"}],
        ["Lab detail page prints experiment list only; no COs/books printed (p.17)"]),
    lab("Post Harvest Engg. of Cereals, Pulses & Oil Seeds Lab", "RAG452: POST HARVEST ENGG. OF CEREALS, PULSES & OIL SEEDS LAB", ["RAG452"],
        [{"no": 1, "exp": "Performance evaluation of different types of cleaners and separators."},
         {"no": 2, "exp": "Determination of separation efficiency,"},
         {"no": 3, "exp": "Study of different size reduction machines and performance evaluation,"},
         {"no": 4, "exp": "Determination of fineness modulus and uniformity index, Study of different types of conveying and elevating equipments."},
         {"no": 5, "exp": "Study of different types of mixers."},
         {"no": 6, "exp": "Measurement of moisture content: dry basis and wet basis,"},
         {"no": 7, "exp": "Study on drying characteristics of grains and determination of drying constant,"},
         {"no": 8, "exp": "Determination of EMC (Static and dynamic method),"},
         {"no": 9, "exp": "Study of various types of dryers,"},
         {"no": 10, "exp": "Study of different equipments in rice mills and their performance evaluation,"},
         {"no": 11, "exp": "Study of different equipments in pulse mills and their performance evaluation,"},
         {"no": 12, "exp": "Study of different equipments in oil mills and their performance evaluation,"},
         {"no": 13, "exp": "Type of process flow charts with examples relating to processing of cereals pulses and oil seeds,"},
         {"no": 14, "exp": "Visit to grain processing industries."}],
        [{"semester": 4, "print": "8. RAG452 | Post Harvest Engg. of Cereals, Pulses & Oil Seeds Lab | 0-0-2 | 50 | 30 | 20 | 100 | 1 (2nd Year IV-SEMESTER scheme, p.3)"}],
        ["Several experiment lines end with commas kept verbatim (p.17)"]),
    lab("Watershed Hydrology Lab", "RAG453: WATERSHED HYDROLOGY LAB", ["RAG453"],
        [{"no": 1, "exp": "Visit to meteorological observatory and study of different instruments."},
         {"no": 2, "exp": "Design of rain gauge network. Exercise on intensity - frequency - duration curves."},
         {"no": 3, "exp": "Exercise on intensity-frequency-duration curves"},
         {"no": 4, "exp": "Exercise on depth - area - duration and double mass curves."},
         {"no": 5, "exp": "Analysis of rainfall data and estimation of mean rainfall by different methods."},
         {"no": 6, "exp": "Exercise on frequency analysis of hydrologic data and estimation of missing data, test for consistency of rainfall records."},
         {"no": 7, "exp": "Exercise on computation of infiltration indices."},
         {"no": 8, "exp": "Computation of peak runoff and runoff volume by Cook's method and rational formula."}],
        [{"semester": 4, "print": "9. RAG453 | Watershed Hydrology Lab | 0-0-2 | 50 | 30 | 20 | 100 | 1 (2nd Year IV-SEMESTER scheme, p.3)"}],
        ["Exercises 2 and 3 near-duplicate (hyphen spacing variants) - both printed, kept verbatim (p.17)"]),
    lab("Soil & Water Conservation Engineering Lab", "RAG454: SOIL & WATER CONSERVATION ENGINEERING LAB", ["RAG454"],
        [{"no": 1, "exp": "Study of different types and forms of water erosion."},
         {"no": 2, "exp": "Exercises on computation of rainfall erosivity index."},
         {"no": 3, "exp": "Computation of soil erodibility index in soil loss estimation."},
         {"no": 4, "exp": "Determination of length of slope (LS) and cropping practice (CP) factors for soil loss estimation by USLE and MUSLE."},
         {"no": 5, "exp": "Exercises on soil loss estimation/measuring techniques."},
         {"no": 6, "exp": "Study of rainfall simulator for erosion assessment."}],
        [{"semester": 4, "print": "10. RAG454 | Soil & Water Conservation Engineering Lab | 0-0-2 | 50 | 30 | 20 | 100 | 1 (2nd Year IV-SEMESTER scheme, p.3)"}],
        ["Lab detail page prints experiment list only; no COs/books printed (p.18)"]),
]

NSR = [
    {"kind": "elective_slot", "print": "1. ROE030 to 039/ RAS304 | Science Based Open Elective/ Engineering Mathematics-III | 3-1-0 | 70 | 20 | 10 | 100 | 4", "locator": "2nd Year III-SEMESTER scheme row 1, p.2"},
    {"kind": "elective_slot", "print": "2. RVE301/ RAS302 | Universal Human Values & Professional Ethics/ Environment & Ecology | 3-0-0 | 70 | 20 | 10 | 100 | 3", "locator": "2nd Year III-SEMESTER scheme row 2, p.2"},
    {"kind": "semester_summary", "print": "Total 1000 24", "locator": "2nd Year III-SEMESTER scheme table total, p.2"},
    {"kind": "legend", "print": "CT: Class Test", "locator": "p.2"},
    {"kind": "legend", "print": "TA: Teacher Assessment", "locator": "p.2"},
    {"kind": "legend", "print": "L/T/P: Lecture/ Tutorial/ Practical", "locator": "p.2"},
    {"kind": "note", "print": "*B.Tech. IInd year lateral entry students belonging to B.Sc. Stream, shall clear the subjects RCE151/RCE251 and RME101/201 of the first year Engineering Programme along with the second year subjects.", "locator": "p.2 (repeated p.3)"},
    {"kind": "elective_pool", "print": "Science Based Open Electives: a. ROE030/ROE040 Manufacturing Process; b. ROE031/ROE041 Introduction to soft computing; c. ROE032/ROE042 Nano Science; d. ROE033/ROE043 Laser System and Application; e. ROE034/ROE044 Space Science; f. ROE035/ROE045 Polymer Science & Technology; g. ROE036/ROE046 Nuclear Science; h. ROE037/ROE047 Material Science; i. ROE038/ROE048 Discrete Mathematics; j. ROE039/ROE049 Applied Linear Algebra", "locator": "p.2 (repeated p.3)"},
    {"kind": "elective_slot", "print": "1. RAS404/ ROE040 to 049 | Mathematics-III/ Science Based Open Elective | 3-1-0 | 70 | 20 | 10 | 100 | 4", "locator": "2nd Year IV-SEMESTER scheme row 1, p.3"},
    {"kind": "elective_slot", "print": "2. RAS402/ RVE401 | Environment & Ecology/ Universal Human Values & Professional Ethics | 3-0-0 | 70 | 20 | 10 | 100 | 3", "locator": "2nd Year IV-SEMESTER scheme row 2, p.3"},
    {"kind": "semester_summary", "print": "Total 1000 24", "locator": "2nd Year IV-SEMESTER scheme table total, p.3"},
    {"kind": "legend", "print": "CT: Class Test", "locator": "p.3"},
    {"kind": "legend", "print": "TA: Teacher Assessment", "locator": "p.3"},
    {"kind": "legend", "print": "L/T/P: Lecture/ Tutorial/ Practical", "locator": "p.3"},
]

QUIRKS = [
    "Dual-code detail headers across sessions: 'RAS304/RAS404: ENGINEERING MATHS-III' (p.4); UHV subject header prints RVE301/RVE401 (p.3 area); codes captured in respective subject entries",
    "Scheme-vs-detail name variant: scheme prints 'Theory of Machines & Machine Design' (p.3) vs detail header 'THEORY OF MACHINE AND MACHINE DESIGN' (p.11)",
    "Semester credit totals print-verified: III-sem 4+3+3+3+4+3+1+1+1+1 = 24, IV-sem 4+3+3+3+3+4+1+1+1+1 = 24 (pp.2-3)",
    "No COs/K-levels, objectives, or prerequisites printed anywhere in this doc for RAG*/RCE*/REC*/RME* subjects - keys omitted per zero-guessing",
    "Text-layer 'No default Layer config' MuPDF warning during parse (doc-level, harmless)",
    "First-year carry-over rows RME101*/RCE151* (III-sem, p.2) and RME201*/RCE251* (IV-sem, p.3) print 100* marks with '--' credit; captured as scheme-only subjects RME101(codes RME101,RME201) and RCE151(codes RCE151,RCE251) in this draft",
]

def load():
    with open(DRAFT) as f:
        return json.load(f)

def save(d):
    with open(DRAFT, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)

def have(d, code):
    for s in d["subjects"]:
        if code in (s.get("codes") or []):
            return True
    return False

def main():
    d = load()
    added = []
    for s in PHASE1 + PHASE2:
        if not any(have(d, c) for c in s["codes"]):
            d["subjects"].append(s)
            added.append(s["codes"][0])
    save(d)
    print("PHASE1+2 appended:", added, "subjects now:", len(d["subjects"]))
    d = load()
    if not d.get("non_subject_rows"):
        d["non_subject_rows"] = NSR
    existing_q = [q for q in d.get("quirks", [])]
    for q in QUIRKS:
        if q not in existing_q:
            d.setdefault("quirks", []).append(q)
    save(d)
    print("NSR:", len(d["non_subject_rows"]), "quirks:", len(d["quirks"]))
    print("FINAL subjects:", len(d["subjects"]),
          "codes:", sorted({c for s in d["subjects"] for c in s.get("codes", [])}))

if __name__ == "__main__":
    main()
