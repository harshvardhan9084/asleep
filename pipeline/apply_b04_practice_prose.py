#!/usr/bin/env python3
"""B04 verify remedy: 06's practice/training subjects print course content as
PROSE (no Unit-I..V headings) and 10's project subject likewise. Precedent:
B03's BVA251 'Sports and Yoga' (Part A/B keyed as units 1/2). Transcribe the
printed prose verbatim into units["1"], flag + quirk the structure. Zero-guess:
no unit headings invented, prose kept verbatim."""
import json

D6 = "/home/z/my-project/work/pipeline_v2/drafts/batch04_run/06_bpharm_y1-4_syllabus_2019-20.draft.json"
D10 = "/home/z/my-project/work/pipeline_v2/drafts/batch04_run/10_bpharm_y2_scheme-syllabus_2017-18_2.draft.json"

PROSE6 = {
 "HOSPITAL TRAINING-I": ("Training of students at a hospital establishment for a minimum duration of 45 days. The hospital training shall include: First aid (wound dressing, artificial respiration etc.), different routes of injection, study of patient observation charts, prescriptions and dispensing, simple diagnostic reports, etc.\nMay be performed at the end of the 4th semester.", "BP509P"),
 "REPORT ON INDUSTRIAL TRAINING": ("Training of students at an industrial establishment or an approved research laboratory. The industrial training shall include: in case of industry- different sections and subsections of the industry, an idea about the functioning of the industry, product range of the industry and various approvals of the industry; in case of research laboratory- different departments of the laboratory, an idea about the interdisciplinary coordination, contribution of the laboratory to the society and various approvals of the laboratory. A proper report of the same shall be submitted by the students, which shall be subsequently evaluated to assess the impact of the visit.\nMay be performed at the end of the 5th semester.", "BP610P"),
 "PRACTICE SCHOOL": ("150 Hours\nCourse content:\nEvery candidate shall undergo practice school for a period of 150 hours evenly distributed throughout the semester. The student shall opt any one of the domains. Every student shall submit a printed report (in triplicate) on the practice school he/she attended (not more than 25 pages).\nDomains (anyone to be opted): Phytomedicine; Formulation development; Quality control and quality assurance; Drug design and process chemistry; Pharmaceutical software; Artificial intelligence; 3D printing; Nutraceuticals; Cosmeceuticals; Alternative medicine.", "BP706PS"),
 "HOSPITAL TRAINING-II": ("Training of students at a hospital establishment for a minimum duration of 45 days. The hospital training shall include: First aid (wound dressing, artificial respiration etc.), different routes of injection, study of patient observation charts, prescriptions and dispensing, simple diagnostic reports etc.\nMay be performed at the end of the 6th semester.", "BP707P"),
 "PROJECT WORK (On Elective)": ("All the students shall undertake a project under the supervision of a teacher and submit a report. The area of the project shall directly relate any one of the elective subjects opted by the student in semester VIII.  The project shall be carried out in group not exceeding 5 in number. The project report shall be submitted in triplicate (typed & bound copy not less than 25 pages).", "BP815PW"),
 "REPORT ON INDUSTRIAL TOUR": ("Visit of students to an industrial establishment or an approved research laboratory. The industrial visit shall include: in case of industry- visit to different sections and subsections of the industry, an idea about the functioning of the industry, product range of the industry and various approvals of the industry; in case of research laboratory-visit to different departments of the laboratory, an idea about the interdisciplinary coordination, contribution of the laboratory to the society and various approvals of the laboratory. A proper report of the same shall be submitted by the students, which shall be subsequently evaluated to assess the impact of the visit.", "BP816P"),
}

PROSE10 = {
 "Pharmaceutical Jurisprudence Project (Case studies)": "Project work on Pharmaceutical Jurisprudence (case studies) as printed in this document; theory/practical pair kept separate (RULES §3).",
}

def main():
    d = json.load(open(D6))
    for s in d["subjects"]:
        if s.get("name") in PROSE6 and not (s.get("units") or s.get("experiments")):
            prose, code = PROSE6[s["name"]]
            s["units"] = {"1": prose}
            s.setdefault("flags", []).append(
                "experiments_only_no_units (practice/training subject: printed course content is PROSE with no Unit-I..V headings; prose keyed verbatim as unit 1 per B03 BVA251 precedent)")
            s.setdefault("quirks", []).append(
                f"no unit headings printed for {code}; course-content prose transcribed verbatim from the 2019-20 doc (zero-guess: no unit structure invented)")
            print("PATCH6|", s["name"], code)
        if s.get("name") == "PRACTICE SCHOOL" and not s.get("textbooks"):
            s["textbooks"] = [
                {"no": 1, "book": "Trease and Evans Pharmacognosy by W. C. Evans, 16th edition, W.B. Sounders & Co., London."},
                {"no": 2, "book": "Quality Control of Herbal Drugs: An Approach to Evaluation of Botanicals by Mukherjee, P. W., Business Horizons Publishers, New Delhi, India, 2002."},
                {"no": 3, "book": "Current Concepts in Drug Design by T. Durai and Ananda Kumar, BSP Books."},
                {"no": 4, "book": "An Introduction to Medicinal Chemistry by Patrick Graham, L., Oxford University Press."},
                {"no": 5, "book": "Introduction to the Principles of Drug Design by Smith H.J., Williams H, Wright Boston."},
                {"no": 6, "book": "Industrial Microbiology by Prescott and Dunn, 4th edition, CBS Publishers & Distributors, Delhi."},
                {"no": 7, "book": "Molecular Biotechnology: Principles and Applications of Recombinant DNA by B.R. Glick and J.J. Pasternak: ASM Press Washington, D.C."},
                {"no": 8, "book": "Harry\u2019s Cosmetology by Wilkinson, Moore, Seventh Edition."},
                {"no": 9, "book": "Poucher\u2019s Perfumes, Cosmetic and Soaps by Poucher W.A., Butler, H., Springer India Pvt. Ltd, New Delhi."}]
            print("PATCH6-books| PRACTICE SCHOOL (9 books verbatim)")
    json.dump(d, open(D6, "w"), indent=1, ensure_ascii=False)
    d = json.load(open(D10))
    for s in d["subjects"]:
        if s.get("name") in PROSE10 and not (s.get("units") or s.get("experiments")):
            s["flags"].append("scheme-only (project/case-study subject: no unit-level syllabus printed in this document)")
            print("PATCH10|", s["name"])
    json.dump(d, open(D10, "w"), indent=1, ensure_ascii=False)

if __name__ == "__main__":
    main()
