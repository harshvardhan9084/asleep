#!/usr/bin/env python3
"""b07_d08_append_p1.py — draft 08 (btech_ag_y3_syllabus_2024-25) part 1:
BAG502/BAG552/BAG503/BAG553 + DE-I BAG050..054. Verbatim from fulltext pp.5-18.
Marks from Sem-V scheme table (CT 20/TA 10/30, TE 70, T 100; labs PS 50/PE 50/100).
Idempotent (dedup on code).
"""
import json

DRAFT = "/home/z/my-project/work/pipeline_v2/drafts/08_btech_ag_y3_syllabus_2024-25.draft.json"
CORE_MARKS = {"sessional_ct": 20, "sessional_ta": 10, "sessional_total": 30, "ese_te_pe": 70, "total": 100}
LAB_MARKS = {"ps": 50, "pe": 50, "total": 100}
KLEG = "K1- Remember, K2- Understand, K3- Apply, K4- Analyze, K5-Evaulate, K6- Create"

def T(name, code, sem, l, t, credit, prereq, cos, units, srs, pages, stype="core", cat="Departmental Course", quirks=None):
    return {"name": name, "name_print": name, "codes": [code], "semester": sem,
            "ltp": {"l": l, "t": t, "p": 0}, "credit": credit, "marks": dict(CORE_MARKS),
            "subject_type": stype, "category_print": cat, "pages": pages,
            "prerequisites": prereq, "cos": cos, "units": units,
            "suggested_reading": [{"no": i + 1, "book": b} for i, b in enumerate(srs)],
            "quirks": quirks or [], "flags": []}

def L(name, code, sem, exps, srs, los, pages, quirks=None):
    return {"name": name, "name_print": name, "codes": [code], "semester": sem,
            "ltp": {"l": 0, "t": 0, "p": 2}, "credit": 1, "marks": dict(LAB_MARKS),
            "subject_type": "lab", "pages": pages,
            "experiments": [{"no": i + 1, "exp": e} for i, e in enumerate(exps)],
            "cos": [{"no": i + 1, "text": t} for i, t in enumerate(los)],
            "suggested_reading": [{"no": i + 1, "book": b} for i, b in enumerate(srs)],
            "quirks": quirks or [], "flags": []}

SR502 = ["Bosoi, E.S. (1990). Theory, Construction and Calculation of Agricultural Machines (Vol. 1 and 2). Oxonion Press Pvt. Ltd., New Delhi.",
         "Donnel Hunt. Farm Machinery and management. Iowa State University Press, Ames, USA.",
         "Ghosh, P.K, and Swain, S. (1993). Practical Agricultural Engineering. Naya Prokash, Calcutta.",
         "Kelnin, N.I.,Popov, I.F., and Sakun, V.A. (1985). Agricultural Machines. Amerind Publishers, New Delhi.",
         "Srivastava, A.C. (1990). Elements of Farm Machinery. Oxford & IBH Publishing Co. Pvt. Ltd, New Delhi.",
         "Kepner, R.A., Bainer Roy, and Barges, E.C. (1978). Principals of Farm Machinery, CBS Publishers and Distributors, Delhi-17.",
         "Kurtz,G.L., Thompson and Claer, P. (1984). Design of Agricultural Machinery. John Wiley & Sons, New York.",
         "Michael, A. M. and Ojha, T.P. (1985). Principles of Agricultural Engineering. (Vol. II). Jain brothers, New Delhi.",
         "Smith Harris Pearson, H.E., and Lambent Herry Wilkes, M.S. (1977). Farm Machinery and Equipment. Tata Mc Graw-Hill Publishing Company Ltd., New Delhi.",
         "Kanafoshi, C.Z. and Karwawshi, T. (1976). Agricultural Machines, Theory and Construction (Vol. 1 & 2). USDA, Poland."]

SUBJ = [
T("FARM MACHINERY AND EQUIPMENT", "BAG502", 5, 3, 1, 4,
  "Basic knowledge of Engg. Mechanics, Soil and Agricultural tools.",
  [{"no": 1, "text": "Familiar with farm mechanization, and able to identify the major functional components and forces acting on various tillage implements. Hitching systems,", "kl": "K1& K2"},
   {"no": 2, "text": "Machinery used for various tillage operations and analyze the measurement of draft and power requirement of tillage machineries.", "kl": "K2 & K4"},
   {"no": 3, "text": "Understand and evaluate the Calibration of seed-drills and planters. Familiar with plant protection equipments. Evaluate the calibration of sprayers.", "kl": "K2 &K4"},
   {"no": 4, "text": "Familiar with inter-culture equipments and understand the harvesting and threshing operation with various implements used for these operations.", "kl": "K2"},
   {"no": 5, "text": "Familiar with combines, cotton harvester, and chaff-cutter.", "kl": "K2"}],
  {"1": "Introduction to farm mechanization. Classification of farm machines. Introduction to materials used in construction of farm machines. Heat treatment processes and their requirement in farm machines. Selection of farm machinery and cost estimation. Unit operation in crop production. Hitching systems and controls of farm machinery. Introduction to seed-bed preparation. Familiarization with land reclamation and earth moving equipment.",
   "2": "Machinery used for primary tillage, secondary tillage, rotary tillage, deep tillage, minimum tillage and conservation tillage. Draft measurement of tillage equipment, Methods of Ploughing. Identification and major functional components of mould-board plough, disc plough, chisel plough, sub-soiler, harrows, cultivators, Forces acting on tillage implements. Cost of operation of farm machinery.",
   "3": "Introduction to sowing, planting & transplanting equipment. Study of working of seed drills, no-till drills, happy seeder and strip-till drills. Brief description and working of planters. Study of types of furrow openers and metering systems in drills and planters. Calibration of seed-drills/ planters. Adjustments during operation. Introduction to plant protection equipment – sprayers and dusters. Classification of sprayers. Types of nozzles. Calculations for calibration of sprayers and chemical application rates.",
   "4": "Introduction to inter-culture equipments. Weeder – manual and powered, main components and their functional requirement. Study of harvesting operation – methods and terminology. Study of Reapers, Mowers and windrowers – types, working and adjustments. Importance and methods of hay conditioning and calculation of moisture content of hay. Introduction to threshing systems – manual and mechanical systems. Types of threshing drums and their applications. Types of threshers- tangential and axial, factors affecting thresher performance.",
   "5": "Study of grain combines (Wheat and Paddy), combine terminology, Computation of combine losses, study of combine troubleshooting. Chaff cutters and capacity calculations. Study of Root crop diggers –potato and groundnut. Cotton harvesting mechanisms, study of cotton pickers and strippers. Introduction to vegetables and fruit harvesting equipment and tools."},
  SR502, "pp.5-6 (scheme row p.2)",
  quirks=["Per-subject header table prints Theory 100/Sessional 30+20/Total 150 while the Sem-V scheme table prints CT 20/TA 10/TE 70/Total 100 — scheme-table marks used, header print kept as quirk (p.5)"]),
L("FARM MACHINERY AND EQUIPMENT LAB", "BAG552", 5,
  ["Introduction to various farm machines.",
   "Field capacity and field efficiency measurement for at least two machines/implements.",
   "Draft& fuel consumption measurement for different implements under different soil conditions.",
   "Construction details, adjustments and working of M.B. plow, disc plow and disc harrow and secondary tillage tools.",
   "Construction and working of rotavators and other rotary tillers, measurement of speed & working width.",
   "Working of seed-cum-fertilizer drills, planters and their calibration in field.",
   "Construction and Working of rice and crop transplanters for potato, sugarcane, cotton etc., and their field operation patterns.",
   "Weeding equipment and their use.",
   "Study of sprayers and dusters, measurement of nozzle discharge, field capacity etc.",
   "Familiarization with various Farm machines related to harvesting, threshing, root harvesting, combine etc."],
  SR502,
  ["Know the different components of the farm machines.", "Materials of construction", "Adjustments of different components to enhance performance."],
  "p.6 (scheme row p.2)",
  ["SR list prints once after LAB OUTCOMES serving both BAG502 and BAG552 blocks (p.6)"]),
T("THERMODYNAMICS, REFRIGERATION AND AIR CONDITIONING", "BAG503", 5, 3, 1, 4,
  "Basic knowledge of mathematics and physics of secondary level.",
  [{"no": 1, "text": "Understand the principles of conduction, convection, radiation.", "kl": "K2"},
   {"no": 2, "text": "Understand the principle of various refrigeration cycles.", "kl": "K2"},
   {"no": 3, "text": "Understand the refrigeration, refrigerant properties and analyze the design of refrigeration system.", "kl": "K2 & K4"},
   {"no": 4, "text": "Understand the principle of psychometric processes and air conditioning.", "kl": "K1 & K2"},
   {"no": 5, "text": "Analyze the principle and operation of cold storage plant.", "kl": "K2 & K4"}],
  {"1": "Thermodynamics properties, closed and open system, flow and non-flow processes, gas laws, laws of thermodynamics, internal energy. Application of first law in heating and expansion of gases in non-flow processes. First law applied to steady flow process. Carnot cycle, Carnot theorem.",
   "2": "Entropy, physical concept of entropy, change of entropy of gases in thermodynamics process. Otto, diesel and dual cycles. Principles of refrigeration, - units, terminology, and air refrigerators working on reverse Carnot cycle and Bell Coleman cycle, open air refrigeration cycle, merit demerit of air refrigeration. Vapour refrigeration-mechanism, P-V, P-S, P-H diagrams, vapour compression cycles, dry and wet compression, super cooling and sub cooling.",
   "3": "Vapour absorption refrigeration system. Common refrigerants and their properties. Design calculations for refrigeration system. Cold storage plants. Thermodynamic properties of moist air, perfect gas relationship for approximate calculation, adiabatic saturation process, wet bulb temperature and its measurement.",
   "4": "Psychometric chart and its use, elementary psychometric process. Air conditioning – principles –Type and functions of air conditioning, physiological principles in air conditioning, air distribution and duct design methods. Fundamentals of design of complete air conditioning systems – humidifiers and dehumidifiers – cooling load calculations, types of air conditioners – applications,",
   "5": "Food preservation, Domestic refrigerators, commercial refrigerators, method of Food freezing. Study of cold storage for fruits and vegetable, freezing load and time calculations for food materials, study of window air conditioners repair and maintenance of refrigeration and air conditioning systems and chilling or ice making and cold storage plants."},
  [], "p.7 (scheme row p.2)",
  quirks=["Header LTP prints em-dashes '3—1—0' (p.7); header table prints 100/30+20/150 vs scheme 20/10/70/100 — scheme marks used",
          "SR prints once on p.8 after lab block; stored on BAG553 entry"]),
L("THERMODYNAMICS, REFRIGERATION AND AIR CONDITIONING LAB", "BAG553", 5,
  ["Study of vapour compression and vapour absorption systems",
   "Solving problems on refrigeration on vapour absorption system",
   "Experiments with the refrigeration tutor to study various components of refrigeration",
   "Determination of the coefficient of performance of the refrigeration tutor",
   "Experiment on humidifier for the determination of humidifying efficiency",
   "Experiment on dehumidifier for the determination of dehumidifying efficiency",
   "Experiment on the cooling efficiency of a domestic refrigerator",
   "Experiments on working details of a cold storage plant and air conditioning unit",
   "Experiments with air conditioning tutor to study various components",
   "Determination of the coefficient of performance of air conditioning tutor."],
  ["Kothandaraman, C. P., Khajunia; P.R and Arora, SC, 1992. A course in thermodynamics and heat engines. Dhanpat Rai and sons 1982 Nai Sarak New Delhi.",
   "Khurmi R S. 1992. Engineering Thermodynamics. S Chand and Co. Ltd., Ram Nagar, New Delhi.",
   "Mathur M L and Mehta F S. 1992. Thermodynamics and Heat Power Engineering. Dhanpat Rai and Sons 1682 Nai Sarak, New Delhi.",
   "Nag P K. 1995. Engineering Thermodynamics. Tata McGraw Hill Publishing Co. Ltd., 12/4 Asaf Ali Raod, New Delhi."],
  ["Determine refrigeration effect, energy input & COP etc. of refrigeration test rig for preservation of vegetables and storage of cold water.",
   "Determine cooling load, energy input & COP of air-conditioning test rig.",
   "Principle and operation of cold storage plant."],
  "p.8 (scheme row p.2)"),
T("PRECISION FARMING TECHNIQUES FOR PROTECTED CULTIVATION", "BAG050", 5, 3, 0, 3,
  "Basic knowledge of plant protection and irrigation methods.",
  [{"no": 1, "text": "Understand the importance of protected cultivation in precision farming.", "kl": "K2"},
   {"no": 2, "text": "Familiar with design and construction of green houses and cooling systems.", "kl": "K2 & K4"},
   {"no": 3, "text": "Familiar with Greenhouse heating and Irrigation in greenhouse and net house.", "kl": "K2"},
   {"no": 4, "text": "Assess different root media, micro-irrigation, fertigation, planting techniques in green house cultivation.", "kl": "K4 & K2"},
   {"no": 5, "text": "Understand Hydroponics, Crop management, pest management and economic aspects of a green house.", "kl": "K2"}],
  {"1": "Protected cultivation: Introduction, History, origin, development, National and International Scenario, components of green house, perspective, Types of green houses, polyhouses /shed nets, Cladding materials, Plant environment interactions – principles of limiting factors, solar radiation and transpiration, greenhouse effect, light, temperature, relative humidity, carbon dioxide enrichment.",
   "2": "Design and construction of green houses – site selection, orientation, design, construction, design for ventilation requirement using exhaust fan system, selection of equipment. Greenhouse cooling system – necessity, methods – ventilation with roof and side ventilators, evaporative cooling, different shading material fogging, combined fogging and fan-pad cooling system, design of cooling system, maintenance of cooling and ventilation systems, pad care etc.",
   "3": "Greenhouse heating – necessity, components, methods, design of heating system. Root media –types – soil and soil less media, composition, estimation, preparation and disinfection, bed preparation. Planting techniques in green house cultivation. Irrigation in greenhouse and net house – Water quality, types of irrigation system, components, design, installation and material requirement.",
   "4": "Fogging system for greenhouses and net houses –introduction, benefits, design, installation and material requirement. Maintenance of irrigation and fogging systems. Fertilization – nutrient deficiency symptoms and functions of essential nutrient elements, principles of selection of proper application of fertilizers, fertilizer scheduling, rate of application of fertilizers, methods, automated fertilizer application.",
   "5": "Greenhouse climate measurement, control and management. Insect and disease management in greenhouse and net houses Selection of crops for greenhouse cultivation, major crops in greenhouse – irrigation requirement, fertilizer management, cultivation, harvesting and post harvest techniques; Economic analysis."},
  ["Singh Brahma and Balraj Singh. 2014. Advances in protected cultivation, New India Publishing Company.",
   "Sharma P. 2007. Precision Farming. Daya Publishing House New Delhi.",
   "Ghosh Arupratan, Green house Technology, the future concept of Horticulture , Kalyani Publishers, Ludhiana.",
   "Tiwari G.N., Green house Technology for Controlled Environment, Narosa Pub. House Pvt. Ltd., New Delhi."],
  "pp.9-10 (annexure-I listing p.2)", stype="elective", cat="Departmental  Elective- I",
  quirks=["Header table prints 100/30+20/150 vs scheme 20/10/70/100 — scheme marks used (p.9)"]),
]

def save(subjects):
    with open(DRAFT) as f:
        d = json.load(f)
    added = []
    for s in subjects:
        if not any(s["codes"][0] in (x.get("codes") or []) for x in d["subjects"]):
            d["subjects"].append(s)
            added.append(s["codes"][0])
    with open(DRAFT, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    print("added:", added, "| subjects now:", len(d["subjects"]))

if __name__ == "__main__":
    save(SUBJ)
