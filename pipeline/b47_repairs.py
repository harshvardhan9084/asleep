#!/usr/bin/env python3
"""b47_repairs.py — recorded-class repairs for B47 drafts (B43/B44/B46 classes):
 - REX: re-extract failed detail rows from their detail-page slices (B44 16-REX class)
 - print-anchored scheme rows: name restored from the doc's own scheme print
 - prompt-echo junk row dropped (B46 echo-junk class)
 - codeless Elective-I slot rows -> non_subject_rows with verbatim pool list (B46 BMI011 class)
 - no-code print subject kept with codes=[] + no_code_print evidence flag (B46 doc-10 class)
"""
import json, os, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as E

PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"


def load(stem):
    return json.load(open(f"{DRAFTS}/{stem}.draft.json"))


def save(d):
    json.dump(d, open(f"{DRAFTS}/{d['stem']}.draft.json", "w"), indent=1, ensure_ascii=False)


def pages(stem):
    t = open(f"{PARSED}/{stem}.fulltext.txt", encoding="utf-8").read()
    parts = re.split(r"===== PAGE (\d+) =====", t)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def lst(s, k):
    v = s.get(k)
    if isinstance(v, list):
        return v
    if v is None:
        nl = []
    else:
        nl = [str(v)]
    s[k] = nl
    return nl


def rex(stem, code, name, page, session, course):
    """re-extract one detail subject from its page slice; returns subject obj"""
    pg = pages(stem)
    nxt = next((q for q in sorted(pg) if q > page), None)
    sl = "\n\n".join(pg[n] for n in sorted(pg) if n >= page and (nxt is None or n < nxt))
    meta = {"file": stem + ".pdf"}
    sub = {"class": "detail", "code_print": code, "name_print": name, "page": page}
    _, obj = E.extract_one(stem + ".pdf", sl, meta, sub, session, course)
    obj.setdefault("name", obj.get("name_print", ""))
    obj.setdefault("codes", [re.sub(r"[^A-Za-z0-9*]", "", c) for c in [code] if c])
    lst(obj,"quirks").append("targeted REX from detail-page slice p.%d after empty/failed first extraction (B44 16-REX class)" % page)
    lst(obj,"flags")
    return obj


def main():
    out = []

    # --- doc 07: BMC105 REX (empty name, units=0) ---
    stem = "07_mca_y1_syllabus_2024-25"
    d = load(stem)
    for i, s in enumerate(d["subjects"]):
        if [c for c in s.get("codes", []) if "BMC105" in c.upper()]:
            obj = rex(stem, "BMC105", "Computer Organization & Architecture", 10,
                      d["session"], d["course"])
            d["subjects"][i] = obj
            out.append(f"{stem}: BMC105 REX units={len(obj.get('units') or {})} name={obj.get('name','')[:40]}")
            break
    save(d)

    # --- doc 10: KCA041 REX (empty name) ---
    stem = "10_mca_y2_syllabus_2021-22"
    d = load(stem)
    for i, s in enumerate(d["subjects"]):
        if [c for c in s.get("codes", []) if "KCA041" in c.upper()]:
            obj = rex(stem, "KCA041", "Blockchain Architecture", 40,
                      d["session"], d["course"])
            d["subjects"][i] = obj
            out.append(f"{stem}: KCA041 REX units={len(obj.get('units') or {})} name={obj.get('name','')[:40]}")
            break
    save(d)

    # --- doc 04: print-anchored scheme names + Elective-I -> non_subject_rows ---
    stem = "04_mca_y1_scheme-syllabus_2009-10"
    d = load(stem)
    names = {"GP301": "General Proficiency", "MCA411": "Management Information Systems",
             "MCA452": "Mini Project"}
    keep = []
    for s in d["subjects"]:
        c0 = (s.get("codes") or [""])[0].upper()
        if c0 in names and not (s.get("name") or "").strip():
            nm = names[c0]
            s["name"] = nm
            s["name_print"] = nm
            lst(s,"quirks").append(
                "scheme-row-only print restored from the doc's own p.2 scheme table after "
                "empty scheme-batch extraction (print-anchored scheme row class)")
        elif c0 in ("ELECTIVEI", "ELECTIVE-I"):
            d.setdefault("non_subject_rows", []).append({
                "kind": "elective_slot",
                "print": ("Elective-I (MCAE11 Compiler Design, MCAE12 Client Server Computing, "
                          "MCAE13 Data Warehousing & Mining, MCAE14 Cryptography & Network Security, "
                          "MCAE15 Theory of Automata & Formal Languages, MCAE16 Distributed system)"),
                "locator": "p.2 List of Elective-I (verbatim pool print)"})
            d.setdefault("quirks", []).append(
                "codeless Elective-I slot moved to non_subject_rows with the printed pool list kept "
                "verbatim (B46 BMI011 codeless-slot class)")
            out.append(f"{stem}: Elective-I slot -> non_subject_rows")
            continue
        keep.append(s)
    d["subjects"] = keep
    save(d)
    out.append(f"{stem}: scheme names restored x3")

    # --- doc 05: RCA152/RHU001 print-anchored; echo-junk row dropped; Cyber Security no-code flag ---
    stem = "05_mca_y1_scheme_2016-17"
    d = load(stem)
    fix = {"RCA152": "Programming Lab", "RHU001": "Human Values & Professional Ethics"}
    keep = []
    for s in d["subjects"]:
        c0 = (s.get("codes") or [""])[0].upper()
        nm = (s.get("name") or "").strip()
        if c0 == "RCA152" and not nm:
            s["name"] = fix["RCA152"]; s["name_print"] = fix["RCA152"]
            lst(s,"quirks").append(
                "scheme-row-only print restored from the doc's own scheme table after empty "
                "scheme-batch extraction (print-anchored scheme row class)")
        elif c0 == "RHU001" and re.search(r"verbatim", nm):
            s["name"] = fix["RHU001"]; s["name_print"] = fix["RHU001"]
            lst(s,"quirks").append(
                "echo-junk scheme-batch row replaced with the print-anchored scheme row "
                "'RHU001 Human Values & Professional Ethics' (B46 echo-junk class)")
        elif re.search(r"codes exactly as printed", c0) and re.search(r"verbatim", nm):
            d.setdefault("quirks", []).append(
                "one prompt-echo junk scheme row (name 'verbatim') dropped — all 5 scheme rows "
                "(RCA151/152, RHU001, RCA251/252) already present (B46 echo-junk drop class)")
            out.append(f"{stem}: echo-junk row dropped")
            continue
        elif not c0 and nm.lower() == "cyber security":
            lst(s,"flags").append("no_code_print")
            lst(s,"quirks").append(
                "detail printed without any course code (p.19 'Semester II / Cyber Security'); "
                "the scheme table carries no audit row for it; codes left empty — no-code evidence "
                "class (B46 doc-10)")
            out.append(f"{stem}: Cyber Security flagged no_code_print")
        keep.append(s)
    d["subjects"] = keep
    save(d)
    out.append(f"{stem}: RCA152/RHU001 restored")

    # --- doc 09: codeless Elective-I slot -> non_subject_rows ---
    stem = "09_mca_y2_syllabus_2014-15"
    d = load(stem)
    keep = []
    for s in d["subjects"]:
        c0 = (s.get("codes") or [""])[0].upper()
        nm = (s.get("name") or "").strip()
        if not c0 and nm.lower() == "elective-i":
            d.setdefault("non_subject_rows", []).append({
                "kind": "elective_slot",
                "print": ("Elective-I (NMCAE11 Compiler Design, NMCAE12 Client Server Computing, "
                          "NMCAE13 Data Warehousing & Mining, NMCAE14 Advanced Computer Architecture, "
                          "NMCAE15 Distributed System)"),
                "locator": "scheme table Elective-I slot (verbatim pool print; all 5 pool members "
                           "have full detail pages in-doc and enter as real subjects)"})
            d.setdefault("quirks", []).append(
                "codeless Elective-I slot moved to non_subject_rows with the printed pool list kept "
                "verbatim (B46 BMI011 codeless-slot class)")
            out.append(f"{stem}: Elective-I slot -> non_subject_rows")
            continue
        keep.append(s)
    d["subjects"] = keep
    save(d)

    for line in out:
        print("REPAIR|" + line)


if __name__ == "__main__":
    main()
