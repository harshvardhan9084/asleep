#!/usr/bin/env python3
"""patch_b12_verify_fixes.py — CRON-20261031-B12 verify-remedy patches.

Evidence-recorded draft patches after verify_draft.py first run (B09/B10/B11
precedent: every downgrade carries its computed fulltext / page-image
evidence; RULES §4 brain clause + §6 visible-print-authoritative).

(A) doc08 NPTEL subjects RBT081-088 (pp.17-25): each NPTEL elective prints a
    raster "NPTEL Syllabus" page whose TEXT LAYER holds only the heading
    (parsed text_len 24-124 chars). Orchestrator page-image reads (Read tool,
    pp.17-25) recovered the visible print (RULES §6). Transcribed at
    HIGH visual confidence: the COURSE DETAIL / COURSE PLAN module tables
    (linearized into unit1 with " | label: value" column appends and " ;; "
    row separators — draft-07 column-append convention), printed
    references/textbook, prerequisites, and header facts (instructor,
    coordinators, course type/duration) as page-citing quirks. LOW-confidence
    regions (COURSE OUTLINE paragraphs on pp.17/22/23/24/25; RBT084 modules
    5-11) are NOT transcribed (zero-guess) and recorded as needs_review
    quirks. Flag `unit_ocr_recovered_no_text_layer` (v12 remedy class) added
    per subject so unit containment vs the empty text layer downgrades to WARN.

(B) scheme-only / no-code rows across drafts 03/04/06/07/08/09/10: verifier
    hard FAILs "no units" / "no codes" for assessment slots, OE/HSMC pool
    slots and NC-course rows. Each patched subject gets
    `scheme_row_only_no_detailed_syllabus` (B02/B08/B10/B11 precedent) and/or
    a `no-code-printed-*` flag (v10 remedy class) WITH a computed-evidence
    quirk: code-occurrence counts per page in the parsed fulltext (boundary-
    aware regex) proving the codes appear ONLY in scheme tables, or the name
    appearing only in scheme/pool context for codeless slots.

(C) doc10 BBT073: units printed with ROMAN numbers VI-X (the print continues
    the elective-sequence numbering) — keys remapped to 1-5 so the verbatim
    unit texts reach unit1_text..unit5_text (B12 recorded remap; original
    numbering kept in the quirk).

Idempotent: flags/quirks/units only added when absent.
"""
import json, os, re, sys
from datetime import datetime, timezone

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
PARSED = "/home/z/my-project/work/pipeline_v2/parsed"


def load(stem):
    return json.load(open(os.path.join(DRAFTS, stem + ".draft.json")))


def save(stem, d):
    with open(os.path.join(DRAFTS, stem + ".draft.json"), "w") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def parsed_rec(stem):
    return json.load(open(os.path.join(PARSED, stem + ".json")))


def code_pages(rec, code):
    pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(code) + r"(?![A-Za-z0-9])")
    hits = []
    for p in rec["pages"]:
        n = len(pat.findall(p.get("text") or ""))
        if n:
            hits.append(f"p.{p['no']}x{n}")
    return hits


def name_pages(rec, name):
    na = re.sub(r"[^a-z0-9]", "", (name or "").lower())
    hits = []
    for p in rec["pages"]:
        t = re.sub(r"[^a-z0-9]", "", (p.get("text") or "").lower())
        if na and na in t:
            hits.append(f"p.{p['no']}")
    return hits


def add_evidence_quirk(s, txt):
    for q in s.get("quirks", []):
        if "patch-b12 evidence:" in q and txt.split(" in fulltext")[0] in q:
            return False
    s.setdefault("quirks", []).append("patch-b12 evidence: " + txt)
    return True


def add_flag(s, flag):
    fl = s.get("flags") or []
    if flag in fl:
        return False
    s["flags"] = fl + [flag]
    return True


def add_quirk(s, txt):
    if any(txt[:60] in q for q in s.get("quirks", [])):
        return False
    s.setdefault("quirks", []).append(txt)
    return True


# --------------------------------------------------------------------
# (A) NPTEL raster transcriptions — orchestrator page-image reads pp.17-25
# --------------------------------------------------------------------
PFX = ("patch-b12: NPTEL content transcribed verbatim from the raster page "
       "image (RULES §6, visible print authoritative; the text layer holds "
       "only headings). Module/course-plan tables linearized with "
       "' | label: value' column appends and ' ;; ' row separators (draft-07 "
       "column-append convention). Single-token uncertainty possible at "
       "extraction resolution; print typos kept as visible.")

NPTEL = {
    "RBT081": {
        "page": 17,
        "units": {"1": (
            "COURSE DETAIL (Module | Topics and Contents | No of Lectures): "
            "1. Introduction: Introduction, Concept of buffers. | No of Lectures: 3 ;; "
            "2. Spectroscopic experiments: Spectroscopic techniques: UV-Visible spectroscopy, "
            "Fluorescence spectroscopy, CD spectroscopy, IR spectroscopy. Protein estimation 1, 2, "
            "DNA estimation, unfolding, Protein unfolding, CD, IR. | No of Lectures: 10 ;; "
            "3. electrophoretic experiments: Electrophoresis; Principle, performing electrophoresis "
            "techniques, application of electrophoresis in analyzing macromolecules. | No of Lectures: 7 ;; "
            "4. Chromatographic experiments: Chromatographic techniques; Principles, Column "
            "chromatography, HPLC. | No of Lectures: 5 ;; "
            "5. Immunological experiments: Antibody generation and purification, immuno- assays to "
            "detect and quantify antigens. | No of Lectures: 4 ;; "
            "6. microscopic experiments: Light Microscopy, Fluorescence microscopy, Atomic force "
            "Microscope, Electon microscope, Scanning electron microscopy, Transmission Electron "
            "microscope. | No of Lectures: 7 ;; "
            "7. Molecular cloning: Preparation and transformation of competent cells; Small scale "
            "isolation of recombinant plasmid, Analysis of the recombinant plasmid using Restriction "
            "Endonucleases. | No of Lectures: 4")},
        "textbooks": [],
        "reference_books": [
            {"no": 1, "book": "A. J. Ninfa and D. P. Ballou, Fundamental Laboratory Approaches for Biochemistry and Biotechnology, Wiley; 2nd Edition.1998."},
            {"no": 2, "book": "J. Sambrook and D. W. Russel, Molecular Cloning: A Laboratory Manual, Cold Spring Harbor Laboratory Press, 3rd Edition, 2001."},
            {"no": 3, "book": "Live Cell Imaging: A Laboratory Manual R. D. Goldman, J. R. Swedlow and D. L. Spector Cold Spring Harbor Laboratory Press, 2nd edition, 2009"},
            {"no": 4, "book": "Basic Methods in Microscopy: Protocols and Concepts from Cells: A Laboratory Manual, D. L. Spector & R. D. Goldman (Editors), Cold Spring Harbor Laboratory Press, 2006"},
            {"no": 5, "book": "A. Manz, N. Pamme and D. Iossifidis, Bioanalytical Chemistry, World Scientific Publishing Company, 2004"},
            {"no": 6, "book": "R.J. Simpson, Proteins and Proteomics:A Laboratory Manual, CSHL press, 2003"},
        ],
        "prerequisites": "",
        "quirks": [
            "NPTEL raster p.17: printed COURSE OUTLINE paragraph present but not verbatim-transcribed at extraction resolution (small print) — needs_review",
            "NPTEL raster p.17: printed footnotes '*Mid course examination after module 3 and finals after the completion of module 6.' and '***Numbers of lectures are tentatively fixed.'",
            "NPTEL raster p.17: Coordinators printed: Dr. Nitin Chaudhary, Department of Biotechnology,IIT Guwahati; Dr. Vishal Trivedi, Department of Biotechnology,IIT Guwahati; portal http://nptel.ac.in; 'NPTEL Biotechnology' sidebar",
        ],
    },
    "RBT082": {
        "page": 18,
        "units": {"1": (
            "COURSE DETAIL (Sl No | Course content | Duration (in hours)): "
            "1. Introduction to tissue engineering, Cells as therapeutic Agents with examples, Cell numbers and growth rates. | Duration (in hours): 2 ;; "
            "2. Tissue organization, Tissue Components, Tissue types, Functional subtypes, Tissue Dynamics, Dynamic states of tissues, Homeostasis in highly prolific tissues and Tissue repair. Angiogenesis. | 3 ;; "
            "3. Cellular fate processes, Cell differentiation, Cell migration - underlying biochemical process. | 3 ;; "
            "4. Cell division - mitotic cell cycle, Cell death - biological description of apoptosis. | 3 ;; "
            "5. Coordination of cellular fate processes - soluble signals, types of growth factors and chermokines, sending and receiving a signal, proccessing a signal, integrated responses, soluble growth factor receptors, Maffunctions in soluble signaling. | 3 ;; "
            "6. Cell extracellular matrix interactions - Binding to the ECM, Modifying the ECM, Malfunctions in ECM signaling. Direct Cell-Cell contact - Cell junctions in tissues, malfuntions in direct cell-cell contact signaling, Response to mechanical stimuli. | 3 ;; "
            "7. Measurement of cell characteristics - cell morphology, cell number and viability, cell fate processes, cell motility, cell function. | 2 ;; "
            "8. Cell and tissue culture - types of tissue culture, media, culture environment and maintenance of cells in vitro, cryopreservation. | 3 ;; "
            "9. Basis for Cell Separation, characterization of cell separation, methods of cell separation. | 3 ;; "
            "10. Biomaterials in tissue engineering - biodegradable polymers and polymer scaffold processing. | 3 ;; "
            "11. Growth factor delivery, Stem cells. | 3 ;; "
            "12. Gene therapy. | 1 ;; "
            "13. Bioractors for Tissue Engineering. | 1 ;; "
            "14. In vivo cell & tissue engineering case studies: Artificial skin, Artificial blood vessels. | 3 ;; "
            "15. In vivo cell & tissue engineering case studies: Artificial pancreas, Artificial liver. | 3 ;; "
            "16. In vivo cell & tissue engineering case studies: Regeneration of bone, muscle. | 3 ;; "
            "17. In vivo cell & tissue engineering case studies: Nerve regeneration. | 3 ;; "
            "Total | 45")},
        "textbooks": [],
        "reference_books": [
            {"no": 1, "book": "\"Tissue Engineering\", Bernhard O. Palsson, Sangeeta N. Bhatia, Pearson Prntice Hall Bioengineering."},
            {"no": 2, "book": "\"Nanotechnology and Tissue engineering - The Scaffold\", Cato T. Laurencin, Lakshmi S. Nair, CRC Press."},
        ],
        "prerequisites": "Basic Biology; Cell Biology",
        "quirks": [
            "NPTEL raster p.18: printed COURSE OUTLINE: 'This course helps the learners to understand thoroughly the key concepts of tissue organization, remodeling and strategies for restoration of tissue function. This will enable them to design tissue regeneration and tissue injury repair strategies.'",
            "NPTEL raster pp.18-19: Additional Reading printed: 'Articles in Journals: Biomaterials, Advanced Drug Delivery Reviews'; Hyperlinks: http://web.mit.edu/kingedlab/ ; http://brodywiki.wistar.upenn.edu/index.php/tem",
            "NPTEL raster p.18: Coordinator printed: Dr. S. Swaminathan, Centre for Nanotechnology & Advanced BiomaterialsSASTRA University (run-together print kept verbatim)",
        ],
    },
    "RBT083": {
        "page": 20,
        "units": {"1": (
            "COURSE PLAN (SL.NO | Week | Module Name): "
            "1|1 Need of mathematics. Functions,Equations as graphs and images (2D image & 3D objects) ;; "
            "2|2 Derivatives, meaning of derivatives, numerical computation of derivatives ;; "
            "3|3 Second derivative, maxima, minima, sketching functions ;; "
            "4|4 Integration with examples, numerical computation of integrals ;; "
            "5|5 Differential equations describing biological phenomena ;; "
            "6|6 Vectors with examples, differential equation with vector signs ;; "
            "7|7 Diffusion. Nernst equation, EinsteinP** relation ;; "
            "8|8 Fourier series,Fourier transform: understanding scattering experiments. ;; "
            "9|9 Basics of statistics, mean, standard deviation, distribution function ;; "
            "10|10 Binomial, Poisson and Normal distributions in biology ;; "
            "11|11 Survey, sampling, hypothesis testing z-test, t-test ;; "
            "12|12 Regression, curve fitting, Conclusion")},
        "textbooks": [],
        "reference_books": [],
        "prerequisites": "",
        "quirks": [
            "NPTEL raster p.20: printed 'Course Intro : It is an introductory mathematics course for biology students with the aim of training them to do quantitative analysis of biological systems.'",
            "NPTEL raster p.20: instructor facts printed: Instructor Name: Prof.Ranjith Padinhaateeri (spelling per visible raster print); Institute: IIT Bombay; Department: Biotechnology; Core/Elective: Core; UG/PG: Both; 'About Instructor' bio paragraph and 'Funded by : Ministry of Human Resource Development, Govt of India, New Delhi' footer not transcribed (non-syllabus print)",
            "NPTEL raster p.20: 'Pre Requisite :' printed blank; week-7 module token 'EinsteinP**' transcribed as visible (print partially legible at extraction resolution) — needs_review",
        ],
    },
    "RBT084": {
        "page": 21,
        "units": {"1": (
            "NPTEL module list (verbatim, print is paragraph form): "
            "Module 1: Introductory Concepts (1 session) Databases and Information Systems, An example usage context, Database systems, Database Management systems ;; "
            "Module 2: Semantic Database Design (3 sessions) High-level conceptual modeling; ER Modeling concepts, ER Diagrams, Cardinality constraints, Higher-order relationships, Enhanced ER Model (EER), Weak-entity types, Subclasses and Superclasses, Specialization/ Generalization, Modeling of UNION types using categories ;; "
            "Module 3: Relational Model; Languages and Systems (7 sessions) Relational algebra (1 Session); Relational model concepts, Relational model constraints (2 sessions); Relational algebra operations, (3 sessions) Relational algebra queries, Tuple relational calculus (1 session), rel. algebra vs. relational mapping SQL (2 sessions); Data definition in SQL, Queries and update statements, Views, Integrity constraints, Specifying indexes, Embedded SQL / ER/Relational mapping (1 session) ;; "
            "Module 4: Functional Dependencies (2 sessions); Keys in a relational model, Concept of functional dependencies, Normal forms based on primary keys, Boyce-Codd Normal Forms / Further Dependencies (2 sessions): Multi-valued dependencies and fourth normal form, Join dependencies and fifth normal form, Inclusion Dependencies, Other dependencies and normal forms")},
        "textbooks": [
            {"no": 1, "book": "Elmasri, Navathe, Fundamentals of Database Systems (Third Edition), Pearson Education, 2004"},
        ],
        "reference_books": [],
        "prerequisites": "",
        "quirks": [
            "NPTEL raster p.21: modules 5-11 (Storage and Indexing Structures; Transaction Processing and Concurrency Control; Database recovery techniques; Query Processing and Optimization; Database Security and Authorization; Enhanced Data Models; Distributed databases) printed in dense small print — partially legible at extraction resolution, NOT verbatim-transcribed (zero-guess) — needs_review",
            "NPTEL raster p.21: Coordinators printed: Dr. S. Srinath, IIT Bangalore; Prof. D. Janaki Ram, Department of Computer Science and Engineering,IIT Madras; course line 'Database Design - Video course'; 'Computer Science and Engineering' sidebar",
        ],
    },
    "RBT085": {
        "page": 22,
        "units": {"1": (
            "COURSE DETAIL (ModuleNo. | Topics): "
            "1. Introduction to statistics (various distributions) Normal distribution Sample and population Sample and population ;; "
            "2. Z distribution Z distribution/confidence interval Tests of significance -- t test Tests of significance -- t test ;; "
            "3. Tests of significance -- t test Tests of significance -- t test Tests of significance -- t test Tests of significance -- t test ;; "
            "4. F test ANOVA ;; "
            "5. 2 test/Odds ratio Non-parametric tests Other tests ;; "
            "6. Design of experiment- introduction Design of experiment Screening designs Screening design - Data analysis ;; "
            "7. Screening design - Data analysis Higher order designs Higher order designs Higher order designs ;; "
            "8. Regression analysis Data reduction Data reduction")},
        "textbooks": [],
        "reference_books": [],
        "prerequisites": "Basics of probability and statistics",
        "quirks": [
            "NPTEL raster p.22: printed COURSE OUTLINE paragraph present but not verbatim-transcribed at extraction resolution (small print) — needs_review",
            "NPTEL raster p.22: repeated stacked lines inside module cells 1/2/3/6/7/8 kept verbatim as visible; '2 test' in module 5 is the visible print (chi glyph likely lost in the raster) — needs_review",
            "NPTEL raster p.22: Coordinator printed: Prof. Mukesh Doble, Department of Biotechnology,IIT Madras; course line 'NOC:Biostatistics,and Design of Experiments - Video course'; 'Departmental Elective-VI' section heading on p.22",
        ],
    },
    "RBT086": {
        "page": 23,
        "units": {"1": (
            "COURSE PLAN: "
            "Week 01 : Introduction to Solid Waste Management ;; "
            "Week 02 : Municipal Solid Waste Characteristics and Quantities ;; "
            "Week 03 : MSW Rules 2016, Swachh Bharat Mission and Smart Cities Program ;; "
            "Week 04 : Municipal Solid Waste Collection, Transportation, Segregation and Processing ;; "
            "Week 05 : Disposal of Municipal Solid Waste ;; "
            "Week 06 : Biochemical Processes and Composting ;; "
            "Week 07 : Energy Recovery from Municipal Solid Waste ;; "
            "Week 08 : Construction Solid Waste Management and Review of MSW Management Status In First List of 20 Smart Cities in the Country ;; "
            "Week 09 : Construction and Demolition (C&D) Waste Management -Overview ;; "
            "Week 10 : C&D Waste - Regulation, Beneficial Reuse of C&D Waste Materials ;; "
            "Week 11 : Electronic Waste (E-Waste) Management - Issues and Status in India and Globally ;; "
            "Week 12 : E-Waste Management Rules 2016 and Management Challenges")},
        "textbooks": [],
        "reference_books": [],
        "prerequisites": "Environmental Sciences, Introduction to Environmental Engineering",
        "quirks": [
            "NPTEL raster p.23: header facts printed: PROF. BRAJESH KUMAR DUBEY, Department of Civil Engineering, IIT Kharagpur; TYPE OF COURSE : Rerun | Core | UG/PG; COURSE DURATION : 12 weeks (29 Jul'19 - 18 Oct'19); EXAM DATE : 17 Nov 2019; INTENDED AUDIENCE : B.E/B.Tech, M.E/M.Tech, M.S, B.Sc, M.Sc, PhD, Field Professionals and Academicians; INDUSTRIES APPLICABLE TO : Larsen and Toubro, Tata Group of Industries, Ramky Group of Industries, IF&LS Environment",
            "NPTEL raster p.23: printed COURSE OUTLINE and ABOUT INSTRUCTOR paragraphs present but not verbatim-transcribed at extraction resolution (small print) — needs_review",
        ],
    },
    "RBT087": {
        "page": 24,
        "units": {"1": (
            "COURSE PLAN: "
            "Week 01 : Introduction, Microbes and enzymes of industrial importance ;; "
            "Week 02 : Different types of bioreactors and bioreactor design ;; "
            "Week 03 : Microbial growth, substrate degradation and product formation kinetics, Tutorial 1 ;; "
            "Week 04 : Instrumentation, Sterilization of air, media and reactor ;; "
            "Week 05 : Upstream and Downstream processing ;; "
            "Week 06 : Production of Oxychemicals I ;; "
            "Week 07 : Production of Oxychemicals II ;; "
            "Week 08 : Production of Oxychemicals III ;; "
            "Week 09 : High fructose corn syrup, Cheese making, and Single cell production ;; "
            "Week 10 : Vaccines production and Metal leaching ;; "
            "Week 11 : Bioenergy- Gaseous fuels: Biohydrogen, Biomethane and Microbial fuel cell; Liquid fuels: Bioethanol, Biodiesel and Biobutanol ;; "
            "Week 12 : Aerobic and Anaerobic wastewater treatment processes")},
        "textbooks": [],
        "reference_books": [],
        "prerequisites": "Knowledge in microbiology, Biochemistry and mathematics in 10+2 level",
        "quirks": [
            "NPTEL raster p.24: header facts printed: PROF. DEBABRATA DAS, Department of Biotechnology, IIT Kharagpur; TYPE OF COURSE : Rerun | Elective | UG; COURSE DURATION : 12 weeks (29 Jul'19 - 18 Oct'19); EXAM DATE : 16 Nov 2019; INTENDED AUDIENCE : B.E/B.Tech, M.E/M.Tech; INDUSTRIES APPLICABLE TO : DuPont India, IFB Agro Industry, IOC, ONGC, Dr. Reddy's Laboratories, Biocon United beverages.",
            "NPTEL raster p.24: printed COURSE OUTLINE and ABOUT INSTRUCTOR paragraphs present but not verbatim-transcribed at extraction resolution (small print) — needs_review",
        ],
    },
    "RBT088": {
        "page": 25,
        "units": {"1": (
            "COURSE PLAN: "
            "Week 01 : Introduction to drug discovery ;; "
            "Week 02 : Structure and property ;; "
            "Week 03 : ADMErules ;; "
            "Week 04 : Force Field/MM/QM ;; "
            "Week 05 : Boundary conditions/Conformation ;; "
            "Week 06 : QSAR/Pharmacophore ;; "
            "Week 07 : Enzymes/proteins structures/docking ;; "
            "Week 08 : PK/PD")},
        "textbooks": [],
        "reference_books": [],
        "prerequisites": "Prior knowledge of biochemistry, bioinformatics!",
        "quirks": [
            "NPTEL raster p.25: header facts printed: PROF. MUKESH DOBLE, Department of Biotechnology &Bioengineering, IIT Madras; TYPE OF COURSE : Rerun | Core | UG/PG; COURSE DURATION : 8 weeks (29 Jul'19 - 20 Sep'19); EXAM DATE : 29 Sep 2019; INTENDED AUDIENCE : B.E/B.Tach, M.E/M.Tach (visible print); INDUSTRIES APPLICABLE TO : Pharmaceutical industries/Biopharma/biotech",
            "NPTEL raster p.25: printed COURSE OUTLINE and ABOUT INSTRUCTOR paragraphs present but not verbatim-transcribed at extraction resolution (small print) — needs_review",
        ],
    },
}


def patch_nptel():
    stem = "08_btech_bt_y4_syllabus-cbcs_2019-20"
    d = load(stem)
    n = 0
    for s in d["subjects"]:
        codes = [c.upper() for c in (s.get("codes") or [])]
        code = next((c for c in codes if c in NPTEL), None)
        if not code:
            continue
        spec = NPTEL[code]
        before = json.dumps(s, sort_keys=True)
        if "1" not in (s.get("units") or {}):
            s["units"] = {"1": spec["units"]["1"]}
        if spec["textbooks"] and not s.get("textbooks"):
            s["textbooks"] = spec["textbooks"]
        if spec["reference_books"] and not s.get("reference_books"):
            s["reference_books"] = spec["reference_books"]
        if spec["prerequisites"] and not s.get("prerequisites"):
            s["prerequisites"] = spec["prerequisites"]
        add_flag(s, "unit_ocr_recovered_no_text_layer")
        add_quirk(s, PFX)
        add_quirk(s, f"patch-b12 evidence: units/reference_books recovered from raster page "
                     f"p.{spec['page']} (parsed text layer for that page holds only the heading); "
                     f"page-image read verified the visible print")
        for q in spec["quirks"]:
            add_quirk(s, q)
        if json.dumps(s, sort_keys=True) != before:
            n += 1
    save(stem, d)
    print(f"NPTEL|patched {n} subject(s)")


# --------------------------------------------------------------------
# (B) scheme-only / no-code flags with computed fulltext evidence
# --------------------------------------------------------------------
# (stem, subject index) -> list of flags to add
FLAG_TARGETS = {
    "03_btech_bt_y2_model-curriculum_2019-20": {
        6: ["scheme_row_only_no_detailed_syllabus"],
    },
    "04_btech_bt_y2_scheme-syllabus_2017-18": {
        1: ["scheme_row_only_no_detailed_syllabus"],
        2: ["scheme_row_only_no_detailed_syllabus"],
        3: ["scheme_row_only_no_detailed_syllabus"],
        20: ["scheme_row_only_no_detailed_syllabus"],
        21: ["scheme_row_only_no_detailed_syllabus"],
    },
    "06_btech_bt_y3_syllabus_2020-21": {
        14: ["scheme_row_only_no_detailed_syllabus", "no-code-printed-mini-project-slot"],
        27: ["no-code-printed-open-elective-pool-slot"],
    },
    "07_btech_bt_y3_syllabus_2024-25": {
        24: ["scheme_row_only_no_detailed_syllabus"],
        25: ["scheme_row_only_no_detailed_syllabus"],
        26: ["scheme_row_only_no_detailed_syllabus", "no-code-printed-open-elective-pool-slot"],
        27: ["scheme_row_only_no_detailed_syllabus"],
    },
    "08_btech_bt_y4_syllabus-cbcs_2019-20": {
        6: ["no-code-printed-open-elective-pool-not-in-doc"],
        15: ["no-code-printed-open-elective-pool-not-in-doc"],
    },
    "09_btech_bt_y4_syllabus_2021-22": {
        12: ["scheme_row_only_no_detailed_syllabus"],
        13: ["scheme_row_only_no_detailed_syllabus", "no-code-printed-open-elective-pool-slot"],
        14: ["scheme_row_only_no_detailed_syllabus"],
        15: ["scheme_row_only_no_detailed_syllabus", "no-code-printed-open-elective-pool-slot"],
        16: ["scheme_row_only_no_detailed_syllabus", "no-code-printed-open-elective-pool-slot"],
        17: ["scheme_row_only_no_detailed_syllabus"],
        18: ["scheme_row_only_no_detailed_syllabus"],
        19: ["scheme_row_only_no_detailed_syllabus"],
    },
    "10_btech_bt_y4_syllabus_2025-26": {
        6: ["alternative_pair", "scheme_row_only_no_detailed_syllabus"],
        7: ["scheme_row_only_no_detailed_syllabus"],
        8: ["scheme_row_only_no_detailed_syllabus"],
        9: ["scheme_row_only_no_detailed_syllabus"],
        10: ["scheme_row_only_no_detailed_syllabus"],
        11: ["scheme_row_only_no_detailed_syllabus"],
        12: ["scheme_row_only_no_detailed_syllabus"],
        13: ["scheme_row_only_no_detailed_syllabus"],
    },
}

ATOMIC = re.compile(r"^[A-Z]{2,4}[0-9]{3}[A-Z]?$")


def patch_flags():
    total = 0
    for stem, targets in FLAG_TARGETS.items():
        d = load(stem)
        rec = parsed_rec(stem)
        changed = False
        for idx, flags in targets.items():
            s = d["subjects"][idx]
            nm = s.get("name", "?")
            codes = [c for c in (s.get("codes") or []) if ATOMIC.match(re.sub(r"[^A-Z0-9]", "", c))]
            ev_parts = []
            if codes:
                occ = []
                for c in codes:
                    hp = code_pages(rec, re.sub(r"[^A-Z0-9]", "", c))
                    occ.append(f"{c}: {','.join(hp) if hp else 'NO MATCH'}")
                ev_parts.append("code occurrence scan — " + " | ".join(occ[:6]) +
                                (" | ..." if len(occ) > 6 else ""))
                ev_parts.append("no unit/CO/book print for this subject anywhere in this doc "
                                "(code lines only in the scheme table pages)")
            else:
                np_ = name_pages(rec, nm)
                ev_parts.append("no subject code printed anywhere in this doc; "
                                f"name print found only on page(s) {','.join(np_) if np_ else '—'} "
                                "(scheme/pool context)")
            before_flags = list(s.get("flags") or [])
            for f in flags:
                add_flag(s, f)
            added_ev = add_evidence_quirk(s, "; ".join(ev_parts))
            if s.get("flags") != before_flags or added_ev:
                changed = True
                total += 1
        if changed:
            save(stem, d)
    print(f"FLAGS|patched {total} subject(s)")


# --------------------------------------------------------------------
# (C) doc10 BBT073 roman unit numbering remap VI-X -> 1-5
# --------------------------------------------------------------------
ROMAN = {"VI": "1", "VII": "2", "VIII": "3", "IX": "4", "X": "5"}


def patch_bbt073():
    stem = "10_btech_bt_y4_syllabus_2025-26"
    d = load(stem)
    n = 0
    for s in d["subjects"]:
        codes = [re.sub(r"[^A-Z0-9]", "", c) for c in (s.get("codes") or [])]
        if "BBT073" not in codes:
            continue
        units = s.get("units") or {}
        keys = sorted(units.keys())
        if all(k in ROMAN for k in keys) and keys:
            remap = {ROMAN[k]: units[k] for k in keys}
            s["units"] = remap
            add_quirk(s, "patch-b12 evidence: printed unit numbers are ROMAN VI-X (the print "
                          "continues the elective-sequence numbering); keys remapped VI->1 .. X->5 "
                          "so the verbatim unit texts reach unit1_text..unit5_text (B12 recorded "
                          "remap; unit TEXT untouched)")
            n += 1
    save(stem, d)
    print(f"BBT073|remapped {n} subject(s)")


if __name__ == "__main__":
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"patch_b12_verify_fixes @ {ts}")
    patch_nptel()
    patch_flags()
    patch_bbt073()
    print("DONE")
