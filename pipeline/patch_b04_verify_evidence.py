#!/usr/bin/env python3
"""B04 step-5 closeout repairs — every edit evidence-backed:

1. draft 04 BP708T Bio-similars: units I-V re-transcribed from PAGE IMAGES
   (printed pp.265-266; text layer drops line-initial bullet words).
2. draft 04 BP411I/BP612I/BP710RP: + detailed_syllabus_not_printed token
   (print gives scheme/header rows only — fulltext-verified).
3. draft 04 BP611P: + experiments_only_no_units token (print's 'List of
   Practical (Perform any 12 Experiments)' is EMPTY, printed p.250).
4. draft 06 six training/report slots: + detailed_syllabus_not_printed
   (fulltext shows course-content paragraphs only, no unit tables).
5. draft 10 Pharmaceutical Jurisprudence Project: + detailed_syllabus_not_printed
   (quirk already documents no numbered practical list).
"""
import json, os

D = "/home/z/my-project/work/pipeline_v2/drafts"

def load(stem):
    return json.load(open(f"{D}/{stem}.draft.json"))

def save(stem, doc):
    with open(f"{D}/{stem}.draft.json", "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)

def subj(doc, code):
    for s in doc["subjects"]:
        if code in (s.get("codes") or []):
            return s
    raise KeyError(code)

BP708T_UNITS = {
    "1": "Introduction to Biosimilars, Vaccines and Macromolecules Classes: Monoclonal antibodies (mAbs), cytokines, insulin, growth factors; primary/secondary/tertiary structures. Biosimilars: Definition, rationale, types (e.g., erythropoietin, filgrastim), Vaccines: Generations (live, subunit, viral vector, mRNA); adjuvants and delivery systems. Industry landscape: Blockbuster biologics (Humira, Keytruda), Indian biosimilar market.",
    "2": "Characterization Methodologies Physicochemical: SDS-PAGE, SEC-HPLC, peptide mapping, mass spectrometry. Glycosylation analysis: N-linked glycans (HILIC, lectin arrays). Functional assays: Cell-based potency, binding ELISA, ADCC. Comparability for biosimilars: Fingerprinting (ICH Q5E).",
    "3": "Manufacturing Protocols Upstream: Cell line development (CHO, HEK), bioreactors, media optimization. Downstream: Harvesting, chromatography (affinity, ion-exchange), viral clearance. Fill-finish: Lyophilization, aseptic processing, cold chain. Process analytical technology (PAT) in biologics.",
    "4": "Quality Control and Stability Protocols Release testing: Host cell proteins (HCP), DNA, sterility, endotoxin (LAL). Stability: ICH Q5C for biologics; subvisible particles, aggregation. Immunogenicity assessment: ADA assays, neutralizing antibodies. Vaccine QC: Potency, identity, safety (animal models).",
    "5": "Regulatory Compliances and Case Studies Global: USFDA 351(k) biosimilar pathway, EMA guidelines, WHO prequalification. India: CDSCO Biosimilar Guidelines 2021, DCGI vaccine approvals. Documentation: BLA/CMC modules, PK/PD comparability studies. Case studies: COVID-19 mRNA vaccines (Pfizer), Indian trastuzumab biosimilars.",
}
BP708T_QUIRK = ("Units I-V re-transcribed from PAGE IMAGE (rendered "
                "work/pipeline_v2/drafts/_b04s04_bp708t-270.png / _b04s04_bp708t-271.png, printed pp.265-266) "
                "per RULES §6: the PDF text layer drops line-initial bullet words on these pages "
                "('-PAGE, SEC-HPLC' prints 'Physicochemical: SDS-PAGE, SEC-HPLC'; '-linked glycans' prints "
                "'N-linked glycans'; '-based potency' prints 'Cell-based potency'; '-exchange)' prints "
                "'(affinity, ion-exchange)'; '-finish' prints 'Fill-finish'; '(LAL)' line-stands for "
                "'endotoxin (LAL)'; '-19 mRNA vaccines' prints 'COVID-19 mRNA vaccines'; 'prequalification.' "
                "line-stands for 'WHO prequalification.') — visible print is authoritative.")

# ---- 1+2+3: draft 04 ----
d4 = load("04_bpharm_scheme-syllabus_2026-27")
s = subj(d4, "BP708T")
s["units"] = dict(BP708T_UNITS)
s.setdefault("quirks", [])
if BP708T_QUIRK not in s["quirks"]:
    s["quirks"].append(BP708T_QUIRK)
print("04 BP708T units re-transcribed; quirks now", len(s["quirks"]))

for code in ("BP411I", "BP612I", "BP710RP"):
    s = subj(d4, code)
    fl = s.setdefault("flags", [])
    tok = "detailed_syllabus_not_printed"
    if not any(tok in str(f) for f in fl):
        fl.append(tok)
    print(f"04 {code}: flags={fl}")

s = subj(d4, "BP611P")
fl = s.setdefault("flags", [])
if not any("experiments_only_no_units" in str(f) for f in fl):
    fl.append("experiments_only_no_units")
s.setdefault("quirks", []).append(
    "Print shows 'Detailed Syllabus / List of Practical / (Perform any 12 Experiments)' with NO experiment "
    "items printed — the printed experiment list is empty in the source document (printed p.250); the "
    "Recommended References follow immediately. Nothing to parse: zero-guess rule forbids inventing experiments.")
print("04 BP611P: flags=", fl)
save("04_bpharm_scheme-syllabus_2026-27", d4)

# ---- 4: draft 06 ----
d6 = load("06_bpharm_y1-4_syllabus_2019-20")
SIX = ["BP509P", "BP610P", "BP706PS", "BP707P", "BP815PW", "BP816P"]
for code in SIX:
    s = subj(d6, code)
    fl = s.setdefault("flags", [])
    tok = "detailed_syllabus_not_printed: print gives a course-content paragraph only (45-day hospital training / 150-hour practice school / project / tour description) — no unit or experiment breakdown printed anywhere in the 2019-20 document"
    if not any("detailed_syllabus_not_printed" in str(f) for f in fl):
        fl.append(tok)
    print(f"06 {code} {s['name']!r}: flagged")
save("06_bpharm_y1-4_syllabus_2019-20", d6)

# ---- 5: draft 10 ----
d10 = load("10_bpharm_y2_scheme-syllabus_2017-18_2")
s = subj(d10, "RPH309P")
fl = s.setdefault("flags", [])
if not any("detailed_syllabus_not_printed" in str(f) for f in fl):
    fl.append("detailed_syllabus_not_printed")
print("10 RPH309P: flags=", fl)
save("10_bpharm_y2_scheme-syllabus_2017-18_2", d10)

print("PATCH DONE")
