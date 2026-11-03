#!/usr/bin/env python3
"""patch_batch06_drafts.py — B06 verify-phase draft repairs, every edit
evidence-backed (RULES §4 brain clause + §6 visible-print authority).

01  6 scheme-row/MOOC-table rows get SCHEME-ROW-ONLY flags
    (fulltext: RAE753 'Industrial Training 0-0-3' scheme row p.~3; RAE084/
    RAE089 'Sub.Code | MOOC Subject Name' table — no detailed syllabus
    printed anywhere in the 30-page doc).
04  (a) 'Introduction to AI and Prompt Engineering' unit5 was a 69,010-char
        concatenation bug (p.5 scheme rows + everything through p.53); rebuilt
        verbatim from the p.53 print ('5. Prompt Engineering ... career
        advantage.'), assignments table captured into assignments_print.
    (b) ALL units: printed weightage-column cells ('20%') that the text layer
        interleaves mid-prose are moved out of the unit text into
        weightage_print {unit: [tokens]} (B05 unit-cell-furniture precedent;
        page-image evidence p.16: '20%' sits in its own right-hand column).
    (c) General Proficiency (AGP151/251): SoP-only rows -> scheme-only flags.
05  evaluation-scheme-only doc: all 22 rows carry codes/L-T-P/marks only ->
    scheme-only flags (3-page doc, no unit detail printed anywhere).
06  8 lab/practical rows print NO codes anywhere (scheme tables print combined
    theory rows 'KAS101/KAS102 ... P=3' that cover both practicals) ->
    LAB-NO-CODE-PRINTED flags with partner evidence (zero-guess: no codes
    invented).
10  doc quirk: Physics/Mechanical/PPP/BEE/Electronics Lab 'Group A/B' labels
    print on their own line; drafts join label+experiment ('Group A: To study
    ...') -> verify WARN class, print faithful (fulltext lines 753-763/787-855).
"""
import json, re

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
PARSED = "/home/z/my-project/work/pipeline_v2/parsed"


def load(stem):
    return json.load(open(f"{DRAFTS}/{stem}.draft.json"))


def save(stem, d):
    json.dump(d, open(f"{DRAFTS}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)


def add_quirk(d, text):
    qs = d.setdefault("quirks", [])
    if not any(str(q) == text for q in qs):
        qs.append(text)


def main():
    # ---------- 01 ----------
    d = load("01_btech_ae_y4_syllabus-cbcs_2019-20")
    n = 0
    for s in d["subjects"]:
        if not s.get("units") and not s.get("experiments"):
            fl = s.setdefault("flags", [])
            f = "SCHEME-ROW-ONLY-DETAILED-SYLLABUS-NOT-PRINTED"
            if f not in fl:
                fl.append(f)
                n += 1
    d.setdefault("quirks", [])
    add_quirk(d,
        "PATCH B06: 6 rows (RAE753 Industrial Training, RAE754 Project-1, RAE851 Seminar, "
        "RAE852 Project-2, RAE084 Aircraft Propulsion MOOC row, RAE089 UAV MOOC row) carry no "
        "detailed syllabus anywhere in the 30-page doc — scheme-table / 'Sub.Code | MOOC Subject "
        "Name' table prints only; flags added (visible print is complete).")
    save("01_btech_ae_y4_syllabus-cbcs_2019-20", d)
    print(f"01: flagged {n} scheme-only rows")

    # ---------- 04 ----------
    d = load("04_btech_ag_course-structure_2026-27")
    ai = [s for s in d["subjects"] if s["name"] == "Introduction to AI and Prompt Engineering"][0]
    pages = [pg["text"] for pg in json.load(open(f"{PARSED}/04_btech_ag_course-structure_2026-27.json"))["pages"]]
    p53 = pages[52]
    i0 = p53.find("5. \nPrompt Engineering")
    if i0 < 0:
        i0 = p53.find("Prompt Engineering")
    m_end = re.search(r"significant\s+career\s+advantage\.", p53)
    assert i0 >= 0 and m_end, "p.53 slice anchors not found"
    i1 = m_end.end()
    unit5 = re.sub(r"\s+", " ", p53[i0:i1]).strip()
    ai["units"]["5"] = unit5
    # assignments table (p.53 tail + p.54 head), verbatim slice
    ia = p53.find("Suggested Assignments")
    asg53 = p53[ia:] if ia >= 0 else ""
    p54 = pages[53]
    ib = p54.find("academic-integrity concern.")
    asg54 = p54[:ib + len("academic-integrity concern.")] if ib >= 0 else ""
    ai["assignments_print"] = re.sub(r"\s+", " ", asg53 + "\n" + asg54).strip()
    ai.setdefault("flags", []).append("UNIT5-REBUILT-FROM-P53-PRINT")
    # (b) weightage cells out of all unit prose
    wtot = 0
    for s in d["subjects"]:
        wp = {}
        for uk, ut in sorted((s.get("units") or {}).items()):
            toks = re.findall(r"\d{1,2}%", ut)
            if toks:
                wp[uk] = toks
                s["units"][uk] = re.sub(r"\s*\d{1,2}%\s*", " ", ut)
                wtot += len(toks)
        if wp:
            s["weightage_print"] = wp
    add_quirk(d,
        "PATCH B06: printed weightage-column cells ('20%' etc.) that the raw text layer interleaves "
        "into unit prose mid-sentence were moved to weightage_print (page-image evidence p.16: the "
        "'20%' cell prints in its own right-hand table column; B05 unit-cell-furniture precedent); "
        f"{wtot} tokens relocated across the doc.")
    add_quirk(d,
        "PATCH B06: 'Introduction to AI and Prompt Engineering' unit5 was a 69,010-char concatenation "
        "bug (p.5 scheme rows + everything through p.53); rebuilt verbatim from the p.53 print; the "
        "printed 'Suggested Assignments / Practice Tasks' table (p.53-54) captured in assignments_print.")
    gp = [s for s in d["subjects"] if s["name"] == "General Proficiency"]
    for s in gp:
        fl = s.setdefault("flags", [])
        for f in ("SCHEME-ROW-ONLY-DETAILED-SYLLABUS-NOT-PRINTED", "SOP-ONLY-PRINTED-PP97-99-NO-UNITS"):
            if f not in fl:
                fl.append(f)
    save("04_btech_ag_course-structure_2026-27", d)
    print(f"04: unit5 rebuilt ({len(unit5)} chars), assignments_print {len(ai['assignments_print'])} chars, "
          f"{wtot} weightage tokens relocated, GP flagged")

    # ---------- 05 ----------
    d = load("05_btech_ag_evaluation-scheme_2008-09")
    n = 0
    for s in d["subjects"]:
        fl = s.setdefault("flags", [])
        for f in ("EVALUATION-SCHEME-ONLY-DOC", "SCHEME-ROW-ONLY-DETAILED-SYLLABUS-NOT-PRINTED"):
            if f not in fl:
                fl.append(f)
                n += 1
    add_quirk(d,
        "PATCH B06: 3-page evaluation-scheme-only doc — every row prints code/name/L-T-P/marks only; "
        "no unit detail exists anywhere in the doc (zero-guess kept rows scheme-only).")
    save("05_btech_ag_evaluation-scheme_2008-09", d)
    print(f"05: flagged {n} rows scheme-only")

    # ---------- 06 ----------
    d = load("06_btech_ag_syllabus-aicte_2018-19")
    n = 0
    for s in d["subjects"]:
        if not s.get("codes"):
            fl = s.setdefault("flags", [])
            f = "LAB-NO-CODE-PRINTED-COMBINED-SCHEME-ROW"
            if f not in fl:
                fl.append(f)
                n += 1
            s["no_code_evidence"] = ("scheme tables print combined theory rows only "
                                     "('KAS101/KAS102 Physics/Chemistry ... P=3' covers both practicals); "
                                     "no lab code printed anywhere in the doc")
    add_quirk(d,
        "PATCH B06: 8 lab/practical rows print NO codes in this AICTE-model doc — scheme tables combine "
        "theory+practical periods into single rows without separate lab codes; flags + per-row evidence "
        "added (zero-guess: no codes invented; merge adjudicates via partner-row notes).")
    save("06_btech_ag_syllabus-aicte_2018-19", d)
    print(f"06: flagged {n} no-code lab rows")

    # ---------- 10 ----------
    d = load("10_btech_ag_y1_model-curriculum_2020-21")
    add_quirk(d,
        "PATCH B06: Physics/Mechanical-Workshop/PPS/BEE/Electronics Lab experiment lists print the "
        "'Group A'/'Group B' (or 'Part A/B', shop names) label on its own line before numbered "
        "experiments; drafts join label+experiment ('Group A: To study ...'), so the needle is not "
        "contiguous in the text layer (fulltext lines 753-763, 787-855) — verify WARN class, print "
        "faithful, no edit.")
    save("10_btech_ag_y1_model-curriculum_2020-21", d)
    print("10: group-label quirk recorded")


if __name__ == "__main__":
    main()
