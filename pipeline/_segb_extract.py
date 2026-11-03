#!/usr/bin/env python3
"""B01-S05 segment b (Semester II, parsed pages 34-64) -> DRAFT_OUT (05b_...json).
Incremental: header first, then load/append/dump after EVERY subject, then non_subject_rows.
"""
import json, os

ROOT = '/home/z/my-project'
OUT = f'{ROOT}/work/pipeline_v2/drafts/05b_bpharm_scheme-syllabus_2026-27.json'

def J(*lines):
    return "\n".join(lines)

def scheme(L, T, P, credit, ct, ta, stot, ese, total, line, sn=""):
    return {"L": L, "T": T, "P": P, "credit": credit,
            "sessional_ct": ct, "sessional_ta": ta, "sessional_total": stot,
            "ese_te_pe": ese, "total_marks": total,
            "scheme_line_print": line, "sn": sn}

HDR = {
    "pdf_rel": "5-course/2026-27/bpharm_scheme-syllabus_2026-27.pdf",
    "stem": "05_bpharm_scheme-syllabus_2026-27",
    "session": "2026-27",
    "sha16": "97b5d901f34c75a4",
    "doc_meta": {
        "course": "B.Pharm",
        "program_year": "1",
        "branches": [],
        "effective_session": "2026-27",
        "curriculum_basis": "",
        "doc_kind": "syllabus",
        "segment": "b",
        "title_print": ""
    },
    "subjects": [],
    "non_subject_rows": [],
    "doc_level_flags": [],
    "doc_level_notes": [
        "Segment b covers Semester II only: parsed-JSON pages 34-64 (printed pp. 29-59): scheme table p.34, subject cards BP201T-BP211P pp.35-63, elective slot p.64.",
        "Scheme table header prints garbled: 'Continuous Mode (Marks) Sessional Exam (Marks) Sessional Duration Internal Total End Semester Marks Exam Duration Total Marks Credit points'. Each row prints two equal Continuous-Mode marks numbers; mapped to sessional_ct/sessional_ta in printed order (totals row CT 160 = sum of col 1, TA 160 = col 2 confirms mapping).",
        "Scheme table hours column prints combined 'No. of hours/week (L/P)' — not separated, so L/T/P are NOT taken from the table; per-course cards (pp.35-64) print 'Hours Per Week (L-T-P)' separated and are used instead ('--' printed for unused slots kept as empty fields).",
        "Card 'Maximum Marks' line prints three values under labels 'SE ESE' in order Total, SE, ESE (e.g. BP201T '50 20 30'); cross-checked against scheme table (internal 20, ESE 30, total 50) for all 11 rows + slot — mapping consistent.",
        "Card value order for 'Credit / Hours Per Week (L-T-P) / Max. Hours' row prints as: Credit, L, T, P, Max. Hours (e.g. BP207P: 1, --, --, 3, 45)."
    ]
}

S = []

# ---------------- BP201T ----------------
S.append({
    "subject_name": "Applied Biostatistics and Data Analytics for Pharmaceutical Sciences",
    "subject_name_print": "Applied Biostatistics and Data Analytics for Pharmaceutical Sciences (Theory)",
    "primary_code": "BP201T", "all_codes": ["BP201T"], "is_lab": False,
    "scheme": scheme("2", "", "", "2", "10", "10", "20", "30", "50",
        "BP201T | Applied Biostatistics and Data Analytics for Pharmaceutical Sciences (Theory) | 2 | 10 | 10 | 1 Hr | 20 | 30 | 1.5 Hr | 50 | 2"),
    "placement": {"semesters": [2], "branches_note": ""},
    "has_detailed_syllabus": True, "prerequisites": "",
    "units": {
        "unit1": J("Descriptive Statistics",
            "Types of data in pharmaceutical sciences (nominal, ordinal, interval, ratio)",
            "Sources of data in pharmacy: clinical trials, pharmacovigilance, quality control, PK studies",
            "Measures of central tendency: mean, median, mode, their calculation and interpretation",
            "Measures of dispersion (range, variance, standard deviation) and their interpretation using pharmaceutical data",
            "Skewness and understanding distribution shape in biological measurements",
            "Perform descriptive statistical analysis using Python libraries such as NumPy and Pandas, with focus on Interpretation of results"),
        "unit2": J("Probability & Statistical Distributions in Healthcare",
            "Basic probability concepts and laws (addition and multiplication rules), conditional probability and its interpretation",
            "Bayes' theorem and its application in clinical decision-making",
            "Concept of random variables (discrete and continuous)",
            "Normal distribution and its importance in biological and pharmaceutical measurements,",
            "Binomial distribution demonstrating applications in clinical trial outcomes",
            "Poisson distribution for modeling rare events such as adverse drug reactions",
            "Graphical visualization of these probability distributions using Python"),
        "unit3": J("Sampling & Statistical Inference",
            "Population versus sample, sampling techniques used in clinical research, Sampling error and bias",
            "Conceptual understanding of the Central Limit Theorem",
            "Confidence intervals and their interpretation",
            "Hypothesis testing framework (null and alternative hypotheses)",
            "Type I and Type II errors, p-value and statistical significance",
            "Demonstration, calculation and interpretation of these parameters using python with pharmaceutical data"),
        "unit4": J("Basics of Correlation & Regression",
            "Conceptual understanding of the following concepts with emphasis on their interpretation- correlation and Pearson correlation coefficients",
            "Interpretation of positive and negative correlations",
            "Scatter plots and trend visualization using pharmaceutical data such as dose-response relationships",
            "Simple linear regression concept, interpretation of regression coefficients",
            "Introduction to odds ratio and its application in clinical risk analysis"),
        "unit5": J("Statistical Analysis Using Python",
            "Case based learning",
            "Demonstration of descriptive statistics, correlation analysis and linear regression using Python libraries- SciPy / Statsmodels / Scikit-learn on pharmaceutical datasets",
            "Interpretation of the output summaries and p-values",
            "Preparation of statistical reports")
    },
    "lectures_per_unit": "6 hours per unit (printed under 'No. of Lectures' for each of units I-V)",
    "co_count": 5,
    "co_texts": [
        "Classify pharmaceutical data using appropriate descriptive statistics.",
        "Apply probability concepts and statistical distributions in clinical and pharmaceutical contexts.",
        "Perform sampling and hypothesis testing for decision-making in research.",
        "Analyze correlation and regression relationships in pharmaceutical datasets.",
        "Demonstrate statistical analysis using Python and interpret outputs appropriately."
    ],
    "co_kls": [],
    "textbooks": [
        "Lane, D.M., Introduction to Statistics. Houston: Rice University. Available at: https://onlinestatbook.com/2/index.html",
        "Walters, S.J., Campbell, M.J. and Machin, D., Medical Statistics: A Textbook for the Health Sciences. Hoboken, NJ: Wiley-Blackwell.",
        "Rowe, P., Essential Statistics for the Pharmaceutical Sciences. London: Pharmaceutical Press.",
        "Bolton, S. and Bon, C., Pharmaceutical Statistics: Practical and Clinical Applications. New York: Informa Healthcare.",
        "De Muth, J.E., Basic Statistics and Pharmaceutical Statistical Applications. Boca Raton, FL: CRC Press."
    ],
    "reference_books": [],
    "experiments": [],
    "objectives": [
        "Explain fundamental statistical concepts relevant to pharmaceutical sciences.",
        "Develop the ability to interpret clinical and experimental data scientifically.",
        "Apply statistical methods for analyzing pharmaceutical and biomedical data.",
        "Demonstrate the use of Python-based tools for statistical analysis and data handling.",
        "Recognize the role of statistical analysis in evidence-based decision making and machine learning applications in healthcare."
    ],
    "source_pages": {"scheme": "34", "detailed": "35-37", "units": "35-36", "cos": "35", "books": "37", "experiments": ""},
    "notes": ["Card (p.35) prints: Course Type 'Core'; Credit 2; Hours Per Week (L-T-P): L 2, T --, P --; Max. Hours 30; Maximum Marks line 'SE ESE 50 20 30'."],
    "print_quirks": [], "needs_review": False
})

# ---------------- BP202T ----------------
S.append({
    "subject_name": "Biochemistry",
    "subject_name_print": "Biochemistry (Theory)",
    "primary_code": "BP202T", "all_codes": ["BP202T"], "is_lab": False,
    "scheme": scheme("3", "", "", "3", "15", "15", "30", "45", "75",
        "BP202T | Biochemistry (Theory) | 3 | 15 | 15 | 1 Hr | 30 | 45 | 2 Hr | 75 | 3"),
    "placement": {"semesters": [2], "branches_note": ""},
    "has_detailed_syllabus": True, "prerequisites": "",
    "units": {
        "unit1": J("Enzymology",
            "a. Introduction, properties, nomenclature, and IUB classification of enzymes and coenzymes. Enzyme kinetics (Michaelis plot, Lineweaver Burk plot). Enzyme inhibitors with examples. Regulation of enzymes: enzyme induction and repression, allosteric enzyme regulation. Therapeutic and diagnostic application of enzymes and isoenzymes. Factors affecting enzyme activity. Digestion, absorption function of dietary Macro and Micronutrients, including Vitamins and Minerals, Biochemical functions of vitamins and associated diseases.",
            "b. Clinical Chemistry: Liver function tests (routinely performed tests based on liver function). Renal function tests (routinely performed tests based on kidney function, ELISA test)"),
        "unit2": J("a. Introduction about biomolecules",
            "Introduction of carbohydrate, lipids, nucleic acids, amino acids and proteins.",
            "b. Bioenergetics: Concept of free energy; relationship between free energy, enthalpy, and entropy; redox potential; energy-rich compounds (ATP, GTP, etc.) and their biological significance.",
            "c. Carbohydrate Metabolism and their role in diabetes mellitus: Overview and significance of major pathways: Glycolysis, Citric Acid Cycle (TCA), Gluconeogenesis, Hexose Monophosphate (HMP) shunt, and Glycogen metabolism; regulation of blood glucose levels; metabolic adaptations during fed state, fasting, and prolonged starvation; metabolic derangements in diabetes mellitus and related disorders.",
            "d. Biological Oxidation: Electron Transport Chain (ETC), oxidative phosphorylation, and mechanisms of ATP synthesis; regulation and clinical implications of mitochondrial dysfunction and oxidative stress."),
        "unit3": J("Lipid metabolism",
            "a. Classification, functions, and properties of lipids and lipoproteins (HDL, LDL, VLDL, chylomicrons)",
            "-oxidation and de-novo synthesis of fatty acids: Ketone bodies: synthesis, utilization, and clinical significance",
            "c. Biological significance of cholesterol, lipid profile, and its clinical significance",
            "d. Disorders associated with lipid metabolism: Hyperlipidaemias and hypercholesterolemia, lipid storage diseases, atherosclerosis, fatty liver disease, and obesity"),
        "unit4": J("Amino acids and protein metabolism",
            "a. Classification and Biological Functions: Classification and physiological roles of amino acids. Structure and functions of proteins and plasma proteins",
            "b. General Metabolism of Amino Acids: Transamination, oxidative and non-oxidative deamination, decarboxylation. Urea cycle nitrogen disposal and detoxification. Fate of carbon skeletons of amino acids (glucogenic vs ketogenic).",
            "c. Catabolism of Specific Amino Acids and Related Disorders: Catabolism of phenylalanine and tyrosine and their metabolic disorders (Phenylketonuria, Albinism, Alkaptonuria, Tyrosinemia) and Inborn errors of branched chain and aromatic amino acids",
            "d. Biochemical significance of neurotransmitters and hormones derived from amino acids: 5-HT (serotonin), melatonin, dopamine, noradrenaline, adrenaline",
            "e. Catabolism of heme and related disorders (jaundice)."),
        "unit5": J("Nucleic acid metabolism and genetic information transfer",
            "a. Nucleotide Metabolism and their related disorders: Biosynthesis of purine and pyrimidine nucleotides. Catabolism of purine nucleotides (uric acid formation). Clinical significance of Hyperuricemia and Gout.",
            "b. Genome Structure and Central Dogma: Organization of the mammalian genome. Introduction to DNA replication, Transcription, and Translation.",
            "c. Genetic Code and Regulation of Protein Synthesis: Properties of the genetic code: Inhibitors of transcription and translation (antibiotics, toxins)",
            "d. DNA Repair and Related Disorders: DNA damage types, Repair mechanisms. Overview of clinical disorders associated with faulty DNA repair.")
    },
    "lectures_per_unit": "varies (printed): I=10, II=10, III=7, IV=10, V=8",
    "co_count": 5,
    "co_texts": [
        "Explain the principles of enzymology and various tests in clinical chemistry",
        "Describe the classification, the classification, structure, and functions of major biomolecules such as carbohydrates, lipids, proteins, nucleic acids, enzymes, and vitamins.",
        "Explain the principles of bioenergetics, biological oxidation, and the overview of metabolic pathways of biomolecules, along with their clinical significance.",
        "Understand metabolism of lipid and its significance.",
        "Understand metabolism of proteins & its significance and monitoring of metabolic and organ-specific disorders."
    ],
    "co_kls": [],
    "textbooks": [
        "Nelson, D.L., Cox, M.M. and Hoskins, A., Lehninger Principles of Biochemistry. New York: W.H. Freeman.",
        "Kennelly, P.J., Rodwell, V.W., Bender, D.A., Botham, K.M. and Weil, P.A., Illustrated Biochemistry. New York: McGraw-Hill Education.",
        "Murray, R.K., Bender, D.A., Botham, K.M., Kennelly, P.J., Rodwell, V.W. and Weil, P.A., . New York: McGraw-Hill.",
        "Voet, D. and Voet, J.G., Biochemistry. New York: John Wiley & Sons.",
        "Devlin, T.M., Textbook of Biochemistry with Clinical Correlations. New York: Wiley-Liss.",
        "Satyanarayana, U. and Chakrapani, U., Biochemistry. Kolkata: Books and Allied (P) Ltd.",
        "Stryer, L., Biochemistry. New York: W.H. Freeman."
    ],
    "reference_books": [],
    "experiments": [],
    "objectives": [
        "Know about enzymology and various tests in clinical chemistry",
        "Understand the biochemical pathways and clinical relevance of carbohydrate, lipid and protein metabolism.",
        "Describe energetics and biological oxidation.",
        "Explain aminoacid and protein metabolism",
        "Understand Nucleic acid metabolism and genetic information."
    ],
    "source_pages": {"scheme": "34", "detailed": "38-40", "units": "38-40", "cos": "38", "books": "40", "experiments": ""},
    "notes": ["Card (p.38) prints: Course Type 'Core'; Credit 3; Hours Per Week (L-T-P): L 3, T --, P --; Max. Hours 45; Maximum Marks line 'SE ESE 75 30 45'. CO table prints labels CO1-CO5."],
    "print_quirks": [
        "CO2 prints duplicated phrase 'the classification, the classification,' — kept as printed.",
        "Unit III: sub-item 'b.' label not printed; line prints '-oxidation and de-novo synthesis of fatty acids' (leading symbol likely lost in print) — kept as printed.",
        "Ref 2 prints a dangling comma/blank before the title ('...Weil, P.A., Illustrated Biochemistry...') — leading title word(s) not printed; kept as printed.",
        "Ref 3 prints author list then ', . New York: McGraw-Hill.' — book title not printed; kept as printed."
    ],
    "needs_review": False
})

# ---------------- BP203T ----------------
S.append({
    "subject_name": "Human Anatomy, Physiology and Pathophysiology II",
    "subject_name_print": "Human Anatomy, Physiology and Pathophysiology II (Theory)",
    "primary_code": "BP203T", "all_codes": ["BP203T"], "is_lab": False,
    "scheme": scheme("4", "", "", "4", "20", "20", "40", "60", "100",
        "BP203T | Human Anatomy, Physiology and Pathophysiology II (Theory) | 4 | 20 | 20 | 1 Hr | 40 | 60 | 3 Hr | 100 | 4"),
    "placement": {"semesters": [2], "branches_note": ""},
    "has_detailed_syllabus": True, "prerequisites": "",
    "units": {
        "unit1": J("Nervous System",
            "a) Organization of nervous system, neuron, neuroglia, classification and properties of nerve fibre, electrophysiology, action potential, nerve impulse, receptors, synapse and neurotransmitters.",
            "Central nervous system: Meninges, ventricles of brain and cerebrospinal fluid. Structure and functions of brain (cerebrum, brain stem and cerebellum), spinal cord (gross structure, functions of afferent and efferent nerve tracts, reflex activity)."),
        "unit2": J("Gastrointestinal System",
            "a) Anatomy of GI tract with special reference to anatomy and functions of stomach (acid production in the stomach and its regulation through parasympathetic nervous system; role of pepsin in protein digestion). Anatomy and functions of small intestine and large intestine. Anatomy and functions of salivary glands, pancreas and liver. Movements of GIT, digestion and absorption of nutrients.",
            "b) Pathophysiology of inflammatory bowel diseases, peptic ulcer, jaundice, hepatitis, typhoid and alcoholic and non alcoholic fatty liver disease"),
        "unit3": J("a) Respiratory System",
            "Anatomy of respiratory system with special reference to anatomy of lungs. Mechanism of respiration and regulation of respiration. Lung volumes and capacities, transport of respiratory gases, artificial respiration and resuscitation methods.",
            "b) Pathophysiology of asthma, chronic obstructive pulmonary diseases and tuberculosis.",
            "c) Urinary System",
            "Anatomy of urinary tract with special reference to anatomy of kidney and nephrons. Functions of kidney and urinary tract. Physiology of urine formation, micturition reflex and role of kidneys in acid base balance. Role of Renin Angitensin Aldosterone System in kidney.",
            "d) Pathophysiology of acute and chronic renal failure and urinary tract infections."),
        "unit4": J("Endocrine System",
            "a) Classification of hormones and mechanism of hormone action. Structure and functions of pituitary gland, thyroid gland, parathyroid gland, adrenal gland, pancreas, pineal gland and thymus.",
            "b) Pathophysiology of diabetes, hypothyroidism, hyperthyroidism, goitre and polycystic ovary syndrome."),
        "unit5": J("Reproductive System and Cancer",
            "a) Anatomy of male and female reproductive system. Functions of male and female reproductive system, sex hormones, physiology of menstruation, fertilization, spermatogenesis, oogenesis, pregnancy and parturition.",
            "b) Pathophysiology of sexually transmitted diseases: AIDS, syphilis and gonorrhea.",
            "c) Etiology and pathogenesis of cancer.")
    },
    "lectures_per_unit": "varies (printed): I=14, II=12, III=12, IV=10, V=12",
    "co_count": 5,
    "co_texts": [
        "Describe the structural organization of the nervous, gastrointestinal, respiratory, urinary, endocrine and reproductive systems.",
        "Explain the physiological mechanisms that regulate the functions of nervous, endocrine and reproductive systems.",
        "Illustrate the etiology and development of common diseases affecting different organ systems including cancer.",
        "Analyze the pathophysiological alterations associated with disorders of the nervous, gastrointestinal, respiratory, renal and endocrine systems.",
        "Interpret clinical manifestations and case findings related to organ system dysfunctions."
    ],
    "co_kls": [],
    "textbooks": [
        "Wilson, K.J.W., Ross and Wilson Anatomy and Physiology in Health and Illness. Churchill Livingstone, New York.",
        "Tortora, G.J. and Grabowski, S.R., Principles of Anatomy and Physiology. Palmetto, GA, U.S.A.",
        "Guyton, A.C. and Hall, J.E., Textbook of Medical Physiology. Elsevier.",
        "Chatterjee, C.C., Human Physiology (Vol. I & II). Academic Publishers, Kolkata.",
        "Mohan, H., Textbook of Pathology. Jaypee Publishers.",
        "Porth, C.M., Pathophysiology: Concepts of Altered Health States. Lippincott Williams & Wilkins.",
        "Kumar, V., Abbas, A.K., Aster, J.C. and Deyrup, A.T., Robbins and Kumar Basic Pathology. Elsevier."
    ],
    "reference_books": [],
    "experiments": [],
    "objectives": [
        "Understand the anatomy and physiology of major body systems.",
        "Learn mechanisms of neurological, gastrointestinal, respiratory, renal, endocrine, and reproductive functions.",
        "Identify common pathophysiological conditions affecting each organ system.",
        "Correlate structural and functional abnormalities with disease symptoms.",
        "Equip students with foundational knowledge for interpreting disease processes and planning rational pharmacotherapy."
    ],
    "source_pages": {"scheme": "34", "detailed": "41-43", "units": "42-43", "cos": "41", "books": "43", "experiments": ""},
    "notes": ["Card (p.41) prints: Course Type 'Core'; Credit 4; Hours Per Week (L-T-P): L 4, T --, P --; Max. Hours 60; Maximum Marks line 'SE ESE 100 40 60'. Unit I body starts on the card page (p.41) after COs."],
    "print_quirks": ["Unit III prints 'Renin Angitensin Aldosterone System' ('Angitensin' kept as printed)."],
    "needs_review": False
})

# ---------------- BP204T ----------------
S.append({
    "subject_name": "Pharmaceutical Organic Chemistry",
    "subject_name_print": "Pharmaceutical Organic Chemistry (Theory)",
    "primary_code": "BP204T", "all_codes": ["BP204T"], "is_lab": False,
    "scheme": scheme("4", "", "", "4", "20", "20", "40", "60", "100",
        "BP204T | Pharmaceutical Organic Chemistry (Theory) | 4 | 20 | 20 | 1 Hr | 40 | 60 | 3 Hr | 100 | 4"),
    "placement": {"semesters": [2], "branches_note": ""},
    "has_detailed_syllabus": True, "prerequisites": "",
    "units": {
        "unit1": J("Aliphatic Saturated Hydrocarbons",
            "Alkanes",
            "Clemmensen reduction, Wolff Kishner reduction",
            "Chemical reactions of alkanes",
            "Mechanism of free radical substitution (halogenation)",
            "Pharmaceutical applications of alkanes: Liquid paraffin, soft paraffin, hard paraffin",
            "Cycloalkanes",
            "Coulson Moffitt modification",
            "Sachse Mohr theory"),
        "unit2": J("Aliphatic Unsaturated Hydrocarbons",
            "- Alkenes",
            "Methods of preparation:",
            "o Dehydration of alcohols",
            "o Dehydrohalogenation of alkyl halides",
            "o Dehalogenation of vicinal dihalides",
            "o Wittig reaction",
            "Chemical reactions of alkenes",
            "Mechanism of electrophilic addition reactions",
            "- Ozonolysis",
            "Conjugated Dienes",
            "Stability of conjugated dienes",
            "Mechanism of Diels Alder reaction",
            "Electrophilic and free radical addition reactions",
            "1,2- and 1,4-addition reactions"),
        "unit3": J("Alkyl Halides",
            "Nucleophilic substitution reactions: SN1 and SN2",
            "o Mechanism, kinetics, substrate structure, solvent effect, stereochemistry",
            "Elimination reactions: E1 and E2",
            "o Mechanism, kinetics, substrate structure, solvent effect, stereochemistry",
            "Comparison of substitution vs elimination reactions"),
        "unit4": J(": Benzene and Its Derivatives",
            "- IUPAC nomenclature of mono- and di-substituted benzene derivatives",
            "Structure of benzene",
            "Molecular orbital picture and resonance",
            "Electrophilic aromatic substitution reactions:",
            "o Nitration",
            "o Halogenation",
            "o Friedel Crafts alkylation and its limitations",
            "o Friedel Crafts acylation",
            "o Sulphonation and desulphonation",
            "Effect of substituents on reactivity and orientation"),
        "unit5": J("Carbonyl Compounds - Aldehydes and Ketones",
            "Preparation and properties of carbonyl compounds",
            "Nucleophilic addition reactions",
            "Aldol condensation and crossed aldol condensation",
            "Cannizzaro and crossed Cannizzaro reactions",
            "Benzoin and Perkin condensation",
            "Oxidation and reduction reactions",
            "Pharmaceutical applications of carbonyl compounds: Chloral, Paraldehyde, Ketoprofen")
    },
    "lectures_per_unit": "12 per unit (printed under 'No. of Lectures' for each of units I-V)",
    "co_count": 5,
    "co_texts": [
        "Describe the chemical reactions and mechanisms of aliphatic saturated hydrocarbons.",
        "Explain the reactions and mechanisms of aliphatic unsaturated hydrocarbons.",
        "Understand nucleophilic substitution and elimination reactions of alkyl halides.",
        "Explain electrophilic aromatic substitution reactions and the effect of substituents.",
        "Apply knowledge of carbonyl compounds and reaction mechanisms in pharmaceutical chemistry."
    ],
    "co_kls": [],
    "textbooks": [
        "Morrison, R.T., Boyd, R.N. and Bhattacharjee, S.K., Organic Chemistry. Pearson Education India.",
        "Finar, I.L., Organic Chemistry, Vol. I. Pearson Books.",
        "Bahl, B.S. and Bahl, A., Textbook of Organic Chemistry. S. Chand & Company.",
        "Furniss, B.S., . ."
    ],
    "reference_books": [],
    "experiments": [],
    "objectives": [
        "Develop a clear understanding of the chemistry of saturated hydrocarbons.",
        "Study the chemistry and reactions of unsaturated hydrocarbons.",
        "Understand the chemistry and reaction mechanisms of alkyl halides.",
        "Explain the chemistry of aromatic hydrocarbons and their derivatives.",
        "Provide an understanding of carbonyl compounds and fundamental organic reaction mechanisms relevant to pharmaceuticals."
    ],
    "source_pages": {"scheme": "34", "detailed": "44-46", "units": "45-46", "cos": "44", "books": "46", "experiments": ""},
    "notes": ["Card (p.44) prints: Course Type 'Core'; Credit 4; Hours Per Week (L-T-P): L 4, T --, P --; Max. Hours 60; Maximum Marks line 'SE ESE 100 40 60'."],
    "print_quirks": [
        "Unit I prints blank gaps between 'Alkanes' and 'Clemmensen reduction, Wolff Kishner reduction', and between 'Cycloalkanes' and 'Coulson Moffitt modification' — lines may be missing from print; kept as printed.",
        "Unit IV title prints with a leading colon: ': Benzene and Its Derivatives' — kept as printed.",
        "Units II/IV print stray dash bullets ('- Alkenes', '- Ozonolysis', '- IUPAC nomenclature ...') — kept as printed.",
        "Ref 4 prints 'Furniss, B.S., . .' — book title and publisher not printed; kept as printed."
    ],
    "needs_review": False
})

# ---------------- BP205T ----------------
S.append({
    "subject_name": "Pharmacognosy and Phytochemistry",
    "subject_name_print": "Pharmacognosy and Phytochemistry (Theory)",
    "primary_code": "BP205T", "all_codes": ["BP205T"], "is_lab": False,
    "scheme": scheme("4", "", "", "4", "20", "20", "40", "60", "100",
        "BP205T | Pharmacognosy and Phytochemistry (Theory) | 4 | 20 | 20 | 1 Hr | 40 | 60 | 3 Hr | 100 | 4"),
    "placement": {"semesters": [2], "branches_note": ""},
    "has_detailed_syllabus": True, "prerequisites": "",
    "units": {
        "unit1": J("Metabolic Pathways and Biogenetic Studies",
            "Brief study of basic metabolic pathways and biosynthesis of secondary metabolites including:",
            "Shikimic acid pathway",
            "Acetate pathway",
            "Amino acid pathways",
            "Utilization of radioactive isotopes in biogenetic studies.",
            "Introduction to pathway prediction tools and modern genetic tools such as CRISPR/Cas9."),
        "unit2": J("Primary Metabolites",
            "General classification and identification tests",
            "Pharmacognostic study (biological source, distribution, identifying characters, chemical constituents, specific tests, therapeutic uses, and commercial applications) of:",
            "Carbohydrates: Acacia, Agar, Tragacanth, Honey",
            "Proteins and Enzymes: Gelatin, Casein",
            "Proteolytic enzymes: Papain, Bromelain, Serratiopeptidase, Urokinase, Streptokinase, Pepsin",
            "Lipids (Waxes, Fats, Fixed Oils): Castor oil, Olive oil, Cocoa butter, Wool fat, Beeswax"),
        "unit3": J("Secondary Metabolites",
            "General classification and identification tests",
            "Pharmacognostic study (biological source, distribution, cultivation of underlined drugs, identifying characters, chemical constituents, specific tests, therapeutic uses, and commercial applications) of:",
            "Alkaloids: Vinca, Rauwolfia, Opium",
            "Volatile Oils: Lemongrass, Clove, Cinnamon, Fennel",
            "Tannins: Myrobalans, Catechu, Pomegranate",
            "Resins: Guggul, Asafoetida",
            "Glycosides: Senna, Liquorice, Digitalis",
            "Phenylpropanoids and Flavonoids: Green Tea, Ginkgo, Flax seed",
            "Iridoids, Other Terpenoids and Naphthoquinones: Gentian, Artemisia"),
        "unit4": J("Extraction Methods for Medicinal Plants",
            "Conventional Methods of Extraction:",
            "Infusion", "Decoction", "Digestion", "Maceration", "Percolation", "Reflux",
            "Distillation", "Soxhlet extraction", "Successive solvent extraction",
            "Modern Methods of Extraction:",
            "Supercritical fluid extraction",
            "Microwave-assisted extraction",
            "Ultrasonic-assisted extraction",
            "Enzyme-assisted extraction",
            "Pressurized liquid extraction"),
        "unit5": J("Overview of Isolation, Identification and Characterization Techniques",
            "Separation and Isolation Techniques:",
            "Planar chromatography",
            "Column chromatography",
            "Preparative TLC",
            "Flash chromatography",
            "Identification Techniques:",
            "Phytochemical tests",
            "Chromatographic techniques",
            "Spectroscopic techniques",
            "Fingerprinting of medicinal plants using TLC/HPTLC.",
            "Types and significance of markers (phytochemical reference standards).",
            "Screening and analysis of major metabolites:",
            "Alkaloids", "Glycosides", "Saponins", "Tannins", "Resins", "Flavonoids", "Phenolics", "Steroids")
    },
    "lectures_per_unit": "varies (printed): I=10, II=12, III=12, IV=12, V=14",
    "co_count": 5,
    "co_texts": [
        "Describe biosynthetic pathways and genetic tools involved in phytoconstituent production.",
        "Classify and explain drugs containing primary and secondary metabolites.",
        "Apply traditional and modern extraction and isolation methods.",
        "Explain qualitative and quantitative analysis of plant metabolites.",
        "Evaluate identity, purity, and quality of herbal raw materials."
    ],
    "co_kls": [],
    "textbooks": [
        "Dewick, P.M., Medicinal Natural Products: A Biosynthetic Approach. John Wiley & Sons.",
        "Evans, W.C., . W.B. Saunders & Co., London."
    ],
    "reference_books": [],
    "experiments": [],
    "objectives": [
        "Understand major metabolic pathways and the biogenetic origin of primary and secondary phytoconstituents, including the use of modern tools for pathway studies.",
        "Study and interpret the pharmacognostic features of crude drugs containing primary metabolites such as carbohydrates, proteins/enzymes, and lipids.",
        "Study and interpret the pharmacognostic features of crude drugs containing secondary metabolites such as alkaloids, glycosides, tannins, resins, volatile oils, flavonoids, phenolics, and terpenoids.",
        "Impart knowledge of conventional and modern extraction techniques and enable selection of appropriate extraction methods.",
        "Develop competency in isolation, identification, characterization, and quality evaluation of medicinal plants and botanicals."
    ],
    "source_pages": {"scheme": "34", "detailed": "47-50", "units": "48-50", "cos": "47", "books": "50", "experiments": ""},
    "notes": ["Card (p.47) prints: Course Type 'Core'; Credit 4; Hours Per Week (L-T-P): L 4, T --, P --; Max. Hours 60; Maximum Marks line 'SE ESE 100 40 60'."],
    "print_quirks": [
        "Ref 2 prints 'Evans, W.C., . W.B. Saunders & Co., London.' — book title not printed; kept as printed.",
        "Unit V heading and its '14' hours print at the foot of p.48; the unit body ('Separation and Isolation Techniques: ...') continues on p.50 with no unit label there."
    ],
    "needs_review": False
})

# ---------------- BP206T ----------------
S.append({
    "subject_name": "Physical Pharmaceutics",
    "subject_name_print": "Physical Pharmaceutics (Theory)",
    "primary_code": "BP206T", "all_codes": ["BP206T"], "is_lab": False,
    "scheme": scheme("3", "", "", "3", "15", "15", "30", "45", "75",
        "BP206T | Physical Pharmaceutics (Theory) | 3 | 15 | 15 | 1 Hr | 30 | 45 | 2 Hr | 75 | 3"),
    "placement": {"semesters": [2], "branches_note": ""},
    "has_detailed_syllabus": True, "prerequisites": "",
    "units": {
        "unit1": J("Solubility distribution phenomenon & buffers",
            "Solubility expression, Solute solvent interactions, Solubility of liquid and liquids, Solubility of solids and liquids, Solubility of Gas in Liquids, Rao Solubility, Effect of pH on solubility, Partition Coefficient Measurement and significance, Critical Solution Temperature and Applications.",
            "Introduction to buffers, Buffers in pharmaceutical and biological system, pH determination methos (Electrometry and colorimetry). Buffer equation / Factor influencing the pH of buffer solutions, Factor influencing Buffer capacity, General procedure for preparing buffers, Indicators."),
        "unit2": J("Interfacial phenomenon",
            "Liquid interface: Surface and interfacial tension, surface free energy, Measurement of surface and interfacial tension, Spreading coefficient, surface active agent, HLB, detergency, types of monolayers at liquid surface.",
            "Adsorption at solid interface, Liquid Interface (contact angle, activated charcoal and Wetting). Adsorption of surface-active agents. Electric properties of interface / Electric double layer, Nernst and zeta potential effect of electrolytes"),
        "unit3": J("Colloidal and Coarse Dispersion",
            "Colloidal dispersions: Types of colloidal dispersions (Lyophobic, Lyophilic, Association colloids), Optical properties of colloids, Kinetic properties of colloids, Electrical properties of colloids, Size and shape of colloidal systems, Stability of colloidal system (peptization and protective action), Application of Colloidal System.",
            "Coarse Dispersions: Suspensions, stokes law (Theory of sedimentation), Effect of Brownian movement / Sedimentation of flocculated particles, sedimentation parameters. Flocculation and controlled structure flocculation. Theories of emulsification and stabilization (DLVO Theory, Monomolecular adsorption, Multimolecular adsorption, Film formation, Solid particle adsorption). Physical instabilities of emulsions (creaming, coalescence and breaking, and phase inversion)."),
        "unit4": J("Rheological studies",
            "Newtonian systems and non-Newtonian systems. Thixotropy measurement / Bulges and spurs. Negative thixotropy, Determination of rheological properties (Viscometers / single and multi-point). Viscoelasticity, psycho-rheology. Applications of rheology in pharm"),
        "unit5": J("Micromeritics",
            "Particle size and size distribution, Particle Shape and Surface area: Methods for determination and significance. Flow properties of powders: determination, significance and methods of enhancement. Advanced flow properties of powers (Powder flow tester).")
    },
    "lectures_per_unit": "varies (printed): I=9, II=8, III=12, IV=8, V=8",
    "co_count": 5,
    "co_texts": [
        "Explain and interpret the fundamental principles governing pharmaceutical manufacturing processes and unit operations.",
        "Analyze physicochemical properties of drugs and excipients and correlate them with formulation stability, quality, and performance.",
        "Apply concepts of interfacial phenomena, colloids, and dispersions in the design and evaluation of pharmaceutical dosage forms.",
        "Evaluate and optimize pharmaceutical processes by controlling variables related to rheology, micromeritics, and dispersion systems.",
        "Demonstrate foundational competency required for advanced studies in formulation development, industrial pharmacy, and pharmaceutical research."
    ],
    "co_kls": [],
    "textbooks": [
        "Sinko, P.J., Martin's Physical Pharmacy and Pharmaceutical Sciences.",
        "Allen, L.V. and McPherson, T.B., Ansel's Pharmaceutical Dosage Forms and Drug Delivery Systems.",
        "Adejare, A., Remington: The Science and Practice of Pharmacy.",
        "Aulton, M.E. and Taylor, K.M.G., Aulton Pharmaceutics: The Design and Manufacture of Medicines. Elsevier.",
        "Lachman, L. and Libbermann, H.A., The Theory and Practice of Industrial Pharmacy.",
        "Mendham, J., Denney, R.C., Barnes, J.D. and Thomas, M.J.K., Vogel's Textbook of 6. Quantitative Chemical Analysis.",
        "Myers, D., Surfaces, Interfaces, and Colloids: Principles and Applications.",
        "Ladisch, M.R., Rheology of Fluid and Semisolid Foods. Springer."
    ],
    "reference_books": [],
    "experiments": [],
    "objectives": [
        "Provide a comprehensive understanding of the theory and principles of pharmaceutical processes and unit operations involved in drug manufacturing.",
        "Impart knowledge of physicochemical phenomena such as solubility, dissolution, interfacial phenomena, rheology, and micromeritics relevant to dosage form design.",
        "Develop understanding of colloidal and coarse dispersions, including suspensions and emulsions, and their pharmaceutical applications.",
        "Familiarize students with rheological and micromeritic properties of powders and dispersions and their role in formulation development and evaluation.",
        "Build a strong foundation for formulation development, process optimization, and quality control of pharmaceutical dosage forms."
    ],
    "source_pages": {"scheme": "34", "detailed": "51-53", "units": "52-53", "cos": "51", "books": "53", "experiments": ""},
    "notes": ["Card (p.51) prints: Course Type 'Core'; Credit 3; Hours Per Week (L-T-P): L 3, T --, P --; Max. Hours 45; Maximum Marks line 'SE ESE 75 30 45'."],
    "print_quirks": [
        "Unit I prints 'Rao Solubility' (a line-wrap fragment 'Rao' preceding 'Solubility'), 'Solubility of liquid and liquids', and 'methos' for methods — kept as printed.",
        "Unit IV ends 'Applications of rheology in pharm' (word truncated in print); also prints 'psycho-rheology' — kept as printed.",
        "Unit V prints 'Advanced flow properties of powers' ('powers' kept as printed).",
        "Ref 5 author prints 'Libbermann' — kept as printed.",
        "Ref 6 numbering glitch: 'Vogel's Textbook of' and '6. Quantitative Chemical Analysis.' split across lines — joined here with the '6.' inline as printed.",
        "Refs 7-8 (Myers; Ladisch) print without serial numbers after ref 6 — kept as printed entries."
    ],
    "needs_review": False
})

# ---------------- BP207P ----------------
S.append({
    "subject_name": "Biochemistry (Practical)",
    "subject_name_print": "Biochemistry (Practical)",
    "primary_code": "BP207P", "all_codes": ["BP207P"], "is_lab": True,
    "scheme": scheme("", "", "3", "1", "10", "10", "20", "30", "50",
        "BP207P | Biochemistry (Practical) | 3 | 10 | 10 | 3 Hr | 20 | 30 | 3 Hr | 50 | 1"),
    "placement": {"semesters": [2], "branches_note": ""},
    "has_detailed_syllabus": True, "prerequisites": "",
    "units": {},
    "lectures_per_unit": "",
    "co_count": 5,
    "co_texts": [
        "Identify proteins and carbohydrates using qualitative biochemical tests and explain their physiological relevance.",
        "Detect normal and abnormal constituents in urine and interpret their diagnostic significance.",
        "Estimate and interpret levels of glucose, cholesterol, urea, creatinine, uric acid, and serum proteins, and correlate results with clinical conditions.",
        "Demonstrate enzyme substrate reactions and evaluate the effect of temperature and substrate concentration on enzymatic activity.",
        "Analyze, record, and report biochemical results accurately and relate practical findings to theoretical knowledge and clinical application."
    ],
    "co_kls": [],
    "textbooks": [
        "Plummer, D. T. An Introduction to Practical Biochemistry. McGraw-Hill, New York.",
        "Wilson, K., and Walker, J. Principles and Techniques of Biochemistry and Molecular Biology. Cambridge University Press.",
        "Varley, H., Gowenlock, A. H., Bell, M., and Bell, J. L. Biochemistry. Heinemann Medical Books.",
        "Burtis, C. A., Ashwood, E. R., and Bruns, D. E. Tietz Textbook of Clinical Chemistry and Molecular Diagnostics. Elsevier.",
        "Rodwell, V. W., Bender, D. A., Botham, K. M., Kennelly, P. J., and Weil, P. A. McGraw-Hill.",
        "Freifelder, D. Essential Molecular Biology: A Practical Approach. Oxford University Press."
    ],
    "reference_books": [],
    "experiments": [
        "1. Identification tests for proteins (Albumin and Casein).",
        "2. Qualitative analysis of carbohydrates* (Glucose, Fructose, Lactose, Sucrose, and Starch).",
        "3. Qualitative analysis of urine for normal and abnormal constituents.",
        "4. Estimation of blood glucose.",
        "5. Estimation of total cholesterol and HDL cholesterol.",
        "6. Estimation of urea, creatinine, and uric acid in serum.",
        "7. Estimation of serum total protein and albumin.",
        "8. Study of enzymatic hydrolysis of starch.",
        "9. Study of the effect of temperature on salivary amylase activity.",
        "10. Study of the effect of substrate concentration on salivary amylase activity.",
        "11.",
        "12. Estimation of serum bilirubin (total and direct bilirubin).",
        "13. Estimation of glycogen content",
        "14. Estimation of SGOT and SGPT"
    ],
    "objectives": [
        "To develop skills to identify and differentiate carbohydrates and proteins through classical qualitative biochemical tests.",
        "To apply biochemical techniques for analysis of pathological conditions using urine and blood samples.",
        "To perform estimations of clinically important biomolecules such as glucose, cholesterol, urea, creatinine, uric acid, and proteins in biological fluids.",
        "To demonstrate enzymatic activity and study factors affecting enzyme function, including substrate concentration and temperature.",
        "To interpret biochemical results and correlate them with clinical conditions such as diabetes, renal dysfunction, and lipid disorders."
    ],
    "source_pages": {"scheme": "34", "detailed": "54-55", "units": "", "cos": "54", "books": "55", "experiments": "55"},
    "notes": ["Card (p.54) prints: Course Type 'Core'; Credit 1; Hours Per Week (L-T-P): L --, T --, P 3; Max. Hours 45; Maximum Marks line 'SE ESE 50 20 30'. List header prints 'List of practical (Minimum 12experiments must be performed)'."],
    "print_quirks": [
        "List header prints 'Minimum 12experiments must be performed' (missing space) — kept as printed.",
        "Experiment item 11 prints the number only, with no text — kept as printed.",
        "Ref 3 prints the author list, a blank gap, then 'Biochemistry. Heinemann Medical Books.' (leading title words not printed); Ref 5 prints the author list then 'McGraw-Hill.' with no title — kept as printed."
    ],
    "needs_review": False
})

# ---------------- BP208P ----------------
S.append({
    "subject_name": "Human Anatomy, Physiology and Pathophysiology II (Practical)",
    "subject_name_print": "Human Anatomy, Physiology and Pathophysiology II (Practical)",
    "primary_code": "BP208P", "all_codes": ["BP208P"], "is_lab": True,
    "scheme": scheme("", "", "3", "1", "10", "10", "20", "30", "50",
        "BP208P | Human Anatomy, Physiology and Pathophysiology II (Practical) | 3 | 10 | 10 | 3 Hr | 20 | 30 | 3 Hr | 50 | 1"),
    "placement": {"semesters": [2], "branches_note": ""},
    "has_detailed_syllabus": True, "prerequisites": "",
    "units": {},
    "lectures_per_unit": "",
    "co_count": 5,
    "co_texts": [
        "Explain the gross morphology, structures, and functions of various organs and organ systems of the human body.",
        "Demonstrate basic emergency response procedures such as cardiopulmonary resuscitation (CPR).",
        "Describe the etiology and pathogenesis of selected disease states.",
        "Identify signs and symptoms, risk factors, diagnostic methods, prevention, treatment strategies, and complications of diseases.",
        "Understand coordinated working patterns of different organs of each system and perform experiments related to special senses and nervous system."
    ],
    "co_kls": [],
    "textbooks": [
        "Wilson, K. J. W., and Waugh, A. Anatomy and Physiology in Health and Illness. Churchill Livingstone, New York.",
        "Best, C. H., and Taylor, N. B. The Physiological Basis of Medical Practice. Williams & Wilkins, Baltimore.",
        "Guyton, A. C., and Hall, J. E. Textbook of Medical Physiology. Elsevier / W.B. Saunders, Philadelphia.",
        "Tortora, G. J., and Grabowski, S. R. Principles of Anatomy and Physiology. John Wiley & Sons.",
        "Brunton, L., Chabner, B., and Knollmann, B. Pharmacological Basis of Therapeutics. McGraw-Hill, New York.",
        "Colledge, N. R., Walker, B. R., and Ralston, S. H. of Medicine. Churchill Livingstone, London."
    ],
    "reference_books": [],
    "experiments": [
        "1. Study of nervous system using specimens and models.",
        "2. Study of respiratory system using models.",
        "3. Study of gastrointestinal system using models.",
        "4. Study of reproductive system using models.",
        "5. Demonstration of general neurological examination.",
        "6. Demonstration of function of olfactory nerve.",
        "7. Examination of different types of taste.",
        "8. Demonstration of visual acuity.",
        "9. Demonstration of reflex activity.",
        "10. Recording of body temperature.",
        "11. Determination of tidal volume and vital capacity.",
        "12. Recording of body mass index (BMI).",
        "13. Study of family planning devices and pregnancy diagnosis tests.",
        "14. Understanding pathophysiology of IBD, peptic ulcer, jaundice, hepatitis, typhoid, asthma, tuberculosis, diabetes, and thyroid disorders through case files / case reports.",
        "15. Hands-on training in cardiopulmonary resuscitation (CPR)."
    ],
    "objectives": [
        "Provide foundational knowledge of the structure and functions of major organ systems of the human body.",
        "Develop understanding of physiological mechanisms responsible for maintenance of homeostasis.",
        "Explain the pathophysiology of diseases affecting different organ systems.",
        "E",
        "Build a strong base for clinical learning through the study of functional and structural changes in disease states."
    ],
    "source_pages": {"scheme": "34", "detailed": "56-57", "units": "", "cos": "56", "books": "57", "experiments": "57"},
    "notes": ["Card (p.56) prints: Course Type 'Core'; Credit 1; Hours Per Week (L-T-P): L --, T --, P 3; Max. Hours 45; Maximum Marks line 'SE ESE 50 20 30'.", "Experiment list preamble printed before item 1: 'Practical HAPP allows the verification of physiological processes discussed in theory classes through experiments on living tissues, simulated videos, models, and charts.' List header prints '(Minimum of 12 experiments must be performed)'."],
    "print_quirks": [
        "Objective 4 prints only '4. E' (truncated in print) — kept as printed.",
        "Ref 5 prints the author list, a blank gap, then 'Pharmacological Basis of Therapeutics. McGraw-Hill, New York.' (leading title word(s) not printed); Ref 6 prints the author list, a blank gap, then 'of Medicine. Churchill Livingstone, London.' (leading title words not printed) — kept as printed."
    ],
    "needs_review": False
})

# ---------------- BP209P ----------------
S.append({
    "subject_name": "Pharmaceutical Organic Chemistry (Practical)",
    "subject_name_print": "Pharmaceutical Organic Chemistry (Practical)",
    "primary_code": "BP209P", "all_codes": ["BP209P"], "is_lab": True,
    "scheme": scheme("", "", "3", "1", "10", "10", "20", "30", "50",
        "BP209P | Pharmaceutical Organic Chemistry (Practical) | 3 | 10 | 10 | 3 Hr | 20 | 30 | 3 Hr | 50 | 1"),
    "placement": {"semesters": [2], "branches_note": ""},
    "has_detailed_syllabus": True, "prerequisites": "",
    "units": {},
    "lectures_per_unit": "",
    "co_count": 5,
    "co_texts": [
        "Recall and outline the preliminary qualitative tests used for identifying water-insoluble and immiscible organic compounds.",
        "Understand the synthesis methods for preparing simple organic compounds and their derivatives.",
        "Apply crystallization techniques to purify organic compounds effectively.",
        "Analyze experimentally to detect elements and functional groups to identify unknown organic compounds.",
        "Interpret and analyze organic compounds through systematic qualitative analysis to confirm their chemical nature."
    ],
    "co_kls": [],
    "textbooks": [
        "Furniss, B. S., Hannaford, A. J., Smith, P. W. G. and Tatchell, A. R. of Practical Organic Chemistry. Longman Scientific & Technical, London.",
        "Mann, F. G. and Saunders, B. C. Practical Organic Chemistry. Pearson Education.",
        "Shriner, R. L., Hermann, C. K. F., Morrill, T. C., Curtin, D. Y. and Fuson, R. C. The Systematic Identification of Organic Compounds. John Wiley & Sons.",
        "Vogel, A. I. Elementary Practical Organic Chemistry. Longman Group Ltd.",
        "Pavia, D. L., Lampman, G. M., Kriz, G. S. and Engel, R. Introduction to Organic Laboratory Techniques. Cengage Learning."
    ],
    "reference_books": [],
    "experiments": [
        "1. Systematic qualitative analysis of minimum of five water-insoluble or water-immiscible unknown organic compounds from different chemical classes:",
        "a. Preliminary tests: Color, odour, Solubility tests, test for aromaticity, test for saturation/unsaturation etc.",
        "c. Determination of Functional group tests such as phenols, amides, amines, carboxylic acids, aldehydes and ketones, alcohols, esters, aromatic and halogenated hydrocarbons and nitro compounds.",
        "d. Preparation of the derivatives and confirmation of the unknown organic compound by melting point / boiling point.",
        "2. Building Molecular Models: Students will use ball-and-stick models to create structures of molecules and understand their shapes and bonding.",
        "3. Crystallization Method Students will learn how to purify three organic compounds using the crystallization technique."
    ],
    "objectives": [
        "Understand and follow essential laboratory safety protocols for handling chemicals, glassware, and equipment.",
        "Identify and analyze organic compounds through their physical properties and functional group reactivity.",
        "Apply ball-and-stick molecular models to visualize and interpret the structure of organic compounds.",
        "Perform purification techniques such as crystallization to isolate and refine organic substances.",
        "Synthesize simple organic compounds and their derivatives using standard laboratory methods."
    ],
    "source_pages": {"scheme": "34", "detailed": "58-59", "units": "", "cos": "58", "books": "59", "experiments": "59"},
    "notes": ["Card (p.58) prints: Course Type 'Core'; Credit 1; Hours Per Week (L-T-P): L --, T --, P 3; Max. Hours 45; Maximum Marks line 'SE ESE 50 20 30'. List header prints '(Minimum 12 experiments to be performed)'."],
    "print_quirks": [
        "Experiment 1 sub-items print a., c., d. — sub-item b. is not printed (gap on p.59) — kept as printed.",
        "Ref 1 prints the author list, a blank gap, then 'of Practical Organic Chemistry. Longman Scientific & Technical, London.' (leading title words not printed) — kept as printed."
    ],
    "needs_review": False
})

# ---------------- BP210P ----------------
S.append({
    "subject_name": "Pharmacognosy and Phytochemistry (Practical)",
    "subject_name_print": "Pharmacognosy and Phytochemistry (Practical)",
    "primary_code": "BP210P", "all_codes": ["BP210P"], "is_lab": True,
    "scheme": scheme("", "", "3", "1", "10", "10", "20", "30", "50",
        "BP210P | Pharmacognosy and Phytochemistry (Practical) | 3 | 10 | 10 | 3 Hr | 20 | 30 | 3 Hr | 50 | 1"),
    "placement": {"semesters": [2], "branches_note": ""},
    "has_detailed_syllabus": True, "prerequisites": "",
    "units": {},
    "lectures_per_unit": "",
    "co_count": 5,
    "co_texts": [
        "Identify unorganized crude drugs using specific chemical tests.",
        "Analyze organized crude drugs through microscopy and powder analysis.",
        "Select and perform appropriate extraction methods for herbal drugs.",
        "Isolate and characterize phytoconstituents using laboratory techniques and TLC.",
        "Assess and compare the quality and purity of herbal raw materials with official standards."
    ],
    "co_kls": [],
    "textbooks": [
        "Trease, G. E. and Evans, W. C. Pharmacognosy. Elsevier.",
        "Harborne, J. B. Phytochemical Methods: A Guide to Modern Techniques of Plant Analysis. Springer.",
        "Wallis, T. E. Textbook of Pharmacognosy. CBS Publishers & Distributors, New Delhi.",
        "Tyler, V. E., Brady, L. R. and Robbers, J. E. Pharmacognosy. Lea & Febiger."
    ],
    "reference_books": [],
    "experiments": [
        "1. Chemical tests for identification of Agar, Acacia, Tragacanth, Honey.",
        "2. Chemical tests for identification of Castor oil, Olive oil, Wool fat, Beeswax.",
        "3. Chemical tests for identification of Asafoetida, Catechu, Aloe.",
        "4. Transverse section and powder microscopy of a vinca leaf.",
        "5. Transverse section and powder microscopy of a cinnamon bark.",
        "6. Transverse section and powder microscopy of a fennel fruit.",
        "7. Transverse section and powder microscopy of a clove flower bud.",
        "8. Transverse section and powder microscopy of a Tulsi stem.",
        "9. Transverse section and powder microscopy of a Liquorice roots.",
        "10. Study of effect on different extraction techniques on yield of crude extract (maceration, decoction, soxhlation).",
        "11. Isolation of volatile oil and it s TLC.",
        "12. Isolation of caffeine from tea.",
        "13. Isolation of Hesperidin from lemon peel.",
        "14. Isolation of Glycyrhizin from liquorice roots.",
        "15. Isolation of Pectin from orange peel.",
        "16. Experiential learning-based experiment involving evaluation and comparison of field/market collected herbal raw materials with Pharmacopoeial standards."
    ],
    "objectives": [
        "Perform chemical tests for the identification of gums, resins, oils, fats, waxes, and unorganized drugs.",
        "Examine crude drugs using transverse section and powder microscopy for correct identification.",
        "Apply suitable extraction techniques and study their effect on yield of crude extracts.",
        "Isolate and identify important phytoconstituents and volatile oils using standard procedures.",
        "Evaluate herbal raw materials collected from field/market sources as per Pharmacopoeial standards."
    ],
    "source_pages": {"scheme": "34", "detailed": "60-61", "units": "", "cos": "60", "books": "61", "experiments": "61"},
    "notes": ["Card (p.60) prints: Course Type 'Core'; Credit 1; Hours Per Week (L-T-P): L --, T --, P 3; Max. Hours 45; Maximum Marks line 'SE ESE 50 20 30'. List header prints '(Minimum 12 experiments must be performed)'."],
    "print_quirks": [
        "Experiment 11 prints 'Isolation of volatile oil and it s TLC.' ('it s' kept as printed).",
        "Experiment 14 prints 'Glycyrhizin' (for Glycyrrhizin) — kept as printed."
    ],
    "needs_review": False
})

# ---------------- BP211P ----------------
S.append({
    "subject_name": "Physical Pharmaceutics (Practical)",
    "subject_name_print": "Physical Pharmaceutics (Practical)",
    "primary_code": "BP211P", "all_codes": ["BP211P"], "is_lab": True,
    "scheme": scheme("", "", "3", "1", "10", "10", "20", "30", "50",
        "BP211P | Physical Pharmaceutics (Practical) | 3 | 10 | 10 | 3 Hr | 20 | 30 | 3 Hr | 50 | 1"),
    "placement": {"semesters": [2], "branches_note": ""},
    "has_detailed_syllabus": True, "prerequisites": "",
    "units": {},
    "lectures_per_unit": "",
    "co_count": 5,
    "co_texts": [
        "Demonstrate practical knowledge of principles and procedures involved in measuring surface tension, viscosity, density, and related physical properties using standard laboratory apparatus.",
        "Determine and interpret surfactant-related parameters such as CMC and HLB and explain their significance in formulation stability and performance.",
        "Conduct experiments and analyze results related to sedimentation volume and evaluate the influence of type and concentration of suspending agents on dispersion stability.",
        "Evaluate micromeritic and flow properties of powders by determining particle size repose, true density, and porosity, and interpret the effect of glidants.",
        "Perform and assess experiments on solubility, partition coefficient, critical solution temperature, adsorption studies, and buffer capacity, and apply findings to formulation decisions."
    ],
    "co_kls": [],
    "textbooks": [
        "Sinko, P. J. Lippincott Williams & Wilkins.",
        "Aulton, M. E. and Taylor, K. M. G. Manufacture of Medicines. Elsevier.",
        "Lachman, L., Lieberman, H. A. and Kanig, J. L. The Theory and Practice of Industrial Pharmacy. CBS Publishers & Distributors.",
        "Allen, L. V., Popovich, N. G. and Ansel, H. C. and Drug Delivery Systems. Lippincott Williams & Wilkins.",
        "Cooper, S. J. and Gunn, C. CBS Publishers & Distributors."
    ],
    "reference_books": [],
    "experiments": [
        "1. Determination of surface tension of given liquids by drop count method and drop weight method.",
        "2. Determination of critical micellar concentration (CMC) of surfactants.",
        "3. viscometer.",
        "4. Determination of HLB value of a surfactant.",
        "5. Calculation of isotonicity by different methods (Sodium Chloride Equivalent Method).",
        "6. Determination of particle size and particle size distribution using sieving method.",
        "7. Determination of particle size and particle size distribution using microscopic method.",
        "8. Determination of densities and derived properties of powders (bulk density, tapped",
        "9. Determination of angle of repose and influence of glidants on angle of repose.",
        "10. Determination of solubility of a drug at different pH/buffer systems at room temperature.",
        "11. Determination of partition coefficient of a drug in n-octanol and water system.",
        "12. Determination of partition coefficient of a drug in benzene and water system.",
        "13. Determination of critical solution temperature and composition of phenol water system.",
        "14. Determination of specific surface area of charcoal by adsorption of acetic acid on activated charcoal.",
        "15. Determination of buffer capacity at various stages of titration of a weak acid against a strong base and determination of pKa."
    ],
    "objectives": [
        "Introduce basic laboratory techniques for determining physicochemical properties such as surface tension, viscosity, and density in pharmaceutical systems.",
        "Develop understanding of interfacial phenomena and surfactant behavior, including micelles, critical micellar concentration (CMC), and HLB in formulation design.",
        "Train students in evaluating disperse systems through sedimentation studies and the effect of suspending agents.",
        "Provide practical experience in powder characterization, including particle size distribution, density, flow properties, porosity, and the role of glidants.",
        "Develop skills in determining solubility, partition coefficient, buffer capacity, and related equilibria relevant to drug formulation."
    ],
    "source_pages": {"scheme": "34", "detailed": "62-63", "units": "", "cos": "62", "books": "63", "experiments": "63"},
    "notes": ["Card (p.62) prints: Course Type 'Core'; Credit 1; Hours Per Week (L-T-P): L --, T --, P 3; Max. Hours 45; Maximum Marks line 'SE ESE 50 20 30'. List header prints '(Minimum 12 experiments must be performed)'. Note printed after item 15: 'Compare the values of various physicochemical properties with marketed formulations wherever possible.' (kept here, not as an experiment)."],
    "print_quirks": [
        "Experiment 3 prints only '3.' followed by 'viscometer.' — leading words of the item not printed (gap on p.63) — kept as printed.",
        "Experiment 8 prints '(bulk density, tapped' with the closing words not printed (line-break gap) — kept as printed.",
        "CO4 prints 'determining particle size' then a gap then 'repose' (words in between, e.g. distribution/angle of, not printed) — kept as printed.",
        "Refs 1, 2, 4, 5 print the author list, a blank gap, then only publisher/title-fragment text ('Sinko, P. J. Lippincott Williams & Wilkins.', 'Aulton ... Manufacture of Medicines. Elsevier.', 'Allen ... and Drug Delivery Systems. ...', 'Cooper, S. J. and Gunn, C. CBS Publishers & Distributors.') — leading title words not printed; kept as printed."
    ],
    "needs_review": False
})

NSR = [
    {
        "row_kind": "semester_summary",
        "payload": {
            "semester": 2,
            "semester_print": "Semester II",
            "scheme_row_print": "Total | 37 | 160 | 160 | 24 Hr | 320 | 480 | 32.5 Hr | 800 | 26",
            "totals": {"hours_per_week_lp_total": "37", "continuous_mode_marks_total": "160",
                       "internal_total": "160", "sessional_duration_total": "24 Hr",
                       "end_semester_marks_total": "320", "end_semester_total": "480",
                       "ese_duration_total": "32.5 Hr", "total_marks": "800", "credit_points_total": "26"},
            "footnote_print": ["* Only one elective course shall be selected",
                               "The syllabi for elective subjects are given in the APPENDIX"]
        },
        "source_pages": "34",
        "notes": ["Totals cover the 12 printed rows (BP201T-BP211P plus the BP212P SEC* elective slot); credit sum 26 includes the elective slot's credit 1."]
    },
    {
        "row_kind": "elective_pool",
        "payload": {
            "codes": ["BP212P"],
            "group_print": "SEC",
            "members": ["Communication Skills",
                        "Mental Well-Being, Stress & Conflict Management",
                        "Fundamentals of Computer Operations"],
            "member_labels_print": ["BP212P SEC1", "BP212P SEC2", "BP212P SEC3"],
            "semesters": [2],
            "scheme_row_print": "BP212P | SEC* – Elective 1 (Practical) | 2 | 10 | 10 | 3 Hr | 20 | 30 | 3 Hr | 50 | 1",
            "slot_card_print": "Credit 1; Hours Per Week (L-T-P): L --, T --, P 2; Max. Hours 30; Maximum Marks line 'SE ESE 50 20 30'",
            "footnote_print": ["* Only 1 elective course shall be selected",
                               "The syllabi for elective subjects are given in the APPENDIX"]
        },
        "source_pages": "34, 64",
        "notes": ["choose-one group; member cards may appear in the elective section (segment f)",
                  "p.64 prints THREE alternatives (SEC1/SEC2/SEC3) though the scheme row says 'SEC* – Elective 1'; only names print on p.64 — no member syllabi invented here."]
    }
]

def flush(path, doc):
    with open(path, 'w') as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)

if not os.path.exists(OUT):
    flush(OUT, HDR)
    print("header written")

# append subjects one at a time (load/append/dump after every subject)
for s in S:
    d = json.load(open(OUT))
    d["subjects"].append(s)
    flush(OUT, d)
    print("appended", s["primary_code"], "subjects:", len(d["subjects"]))

for r in NSR:
    d = json.load(open(OUT))
    d["non_subject_rows"].append(r)
    flush(OUT, d)
    print("appended nsr", r["row_kind"])

d = json.load(open(OUT))
print("FINAL subjects:", len(d["subjects"]), "nsr:", len(d["non_subject_rows"]))
print("codes:", [s["primary_code"] for s in d["subjects"]])
