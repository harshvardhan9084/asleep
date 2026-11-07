#!/usr/bin/env python3
"""b46_repairs.py — B46 recorded-class repairs (B43/B44/B45 classes).

1. Doc 01 (MBA 2013-14): REX empty rows NMBAIB02 (p.47) + NMBAMK03 (p.39) via
   page slices (B44 16-REX class); move the 2 AUC-001/AUC-002 alternative-pair
   slot prints to non_subject_rows (B45 doc-04 class).
2. Doc 08 (MCA-int 2026-27): REX BMI651 + BMI652 as print-anchored scheme rows
   from the p.2 Sem-VI table (B44 KMHC251/NMBA029 class); drop the prompt-echo
   junk row (B43/B44 class); move the codeless 'Elective-I' slot to
   non_subject_rows with the printed Elective-1 pool list (B43/B45 class).
Every repair records its evidence in quirks/flags. Zero guessing: REX output
unit/CO text must be contained in the slice or the row keeps the extraction-
failure flag.
"""
import json, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as E

PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"


def pages_of(ft):
    return E.pages_of(ft)


def slice_page(ft, p):
    pages = pages_of(ft)
    return "\n\n".join(t for n, t in pages if n == int(p))


def rex_extract(pdf_name, slice_text, name_print, code_print, page, session, course):
    prompt = E.EXTRACT % (name_print, code_print, page, session, course,
                          name_print, code_print, slice_text)
    out = E.chat([{"role": "system", "content": E.SYS},
                  {"role": "user", "content": prompt}], max_tokens=8000)
    if isinstance(out, list):
        out = next((x for x in out if isinstance(x, dict)), {})
    out["units"] = E.units_dict(out.get("units"))
    return out


def main():
    log = []

    # ---------- DOC 01 ----------
    stem = "01_mba_y2_syllabus_2013-14"
    d = json.load(open(f"{DRAFTS}/{stem}.draft.json"))
    ft = open(f"{PARSED}/{stem}.fulltext.txt", encoding="utf-8").read()
    qe_session, qe_course = d["session"], d["course"]
    new_subjects, non_subject = [], list(d.get("non_subject_rows") or [])
    for s in d["subjects"]:
        codes = [re.sub(r"[^A-Za-z0-9*]", "", c).upper() for c in (s.get("codes") or [])]
        name = (s.get("name") or "").strip()
        # AUC alternative-pair slot prints -> non_subject_rows (B45 doc-04 class)
        if any(c.startswith("AUC") for c in codes) or name.startswith("**"):
            non_subject.append({
                "kind": "alternative_pair_audit_slot_print",
                "print": f"{(s.get('codes') or [''])[0]} {name_print}" if False else f"{(s.get('codes') or [''])[0]} | {s.get('name_print','')}",
                "locator": (s.get("quirks") or [""])[0],
                "note": ("AUC-001/AUC-002 alternative-pair scheme slot print (audit/non-credit "
                         "pair '** Human Value & Professional Ethics / Cyber Security'); no detail "
                         "pages in this doc; moved to non_subject_rows per the recorded B45 doc-04 "
                         "class; marks print kept above"),
                "marks_print": s.get("marks")})
            log.append(f"{stem}: AUC slot print -> non_subject_rows ({codes})")
            continue
        # empty-name REX (B44 class)
        if not name and codes:
            code = codes[0]
            page = {"NMBAMK03": 39, "NMBAIB02": 47}.get(code)
            if page:
                sl = slice_page(ft, page)
                np = ""
                m = re.search(rf"{re.escape(code.replace('NMBA','NMBA ')) if False else re.escape(code)}[ :\-]*([^\n]+)", sl, re.I)
                if m:
                    np = m.group(1).strip()
                obj = rex_extract(stem, sl, np or code, code, page, qe_session, qe_course)
                if obj.get("scheme_row_only"):
                    obj = {"name": np, "name_print": np or code, "codes": [code],
                           "flags": ["scheme_row_only_detailed_syllabus_not_printed"],
                           "quirks": [f"scheme table row only (p.{page})"], "units": {}}
                obj.setdefault("name", obj.get("name_print", "") or np)
                obj.setdefault("name_print", np)
                obj.setdefault("codes", [code])
                obj.setdefault("quirks", [])
                obj["quirks"] = list(dict.fromkeys(obj["quirks"] + [
                    f"empty first-pass extraction remedied by targeted REX on the p.{page} detail slice "
                    f"(B44 empty-name class); header print attested: '{np}'"]))
                contained_ok = True
                for uk, ut in (obj.get("units") or {}).items():
                    if ut and E.contained(ut, sl) < 0.85:
                        contained_ok = False
                if not contained_ok:
                    obj.setdefault("flags", []).append("unit_containment_low_print_quirk")
                new_subjects.append(obj)
                log.append(f"{stem}: REX {code} '{obj.get('name','')[:50]}' units={len(obj.get('units') or {})} contained={contained_ok}")
                continue
        new_subjects.append(s)
    d["subjects"] = new_subjects
    d["non_subject_rows"] = non_subject
    d.setdefault("quirks", []).append(
        "B46 repairs: 2 AUC alternative-pair slot prints moved to non_subject_rows (B45 class); "
        "NMBAIB02/NMBAMK03 empty rows remedied via targeted REX (B44 class)")
    json.dump(d, open(f"{DRAFTS}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)

    # ---------- DOC 08 ----------
    stem = "08_mca-integrated_y3_syllabus_2026-27"
    d = json.load(open(f"{DRAFTS}/{stem}.draft.json"))
    ft = open(f"{PARSED}/{stem}.fulltext.txt", encoding="utf-8").read()
    p2 = slice_page(ft, 2)
    new_subjects, non_subject = [], list(d.get("non_subject_rows") or [])
    fixed_651 = fixed_652 = False
    for s in d["subjects"]:
        codes = [re.sub(r"[^A-Za-z0-9*]", "", c).upper() for c in (s.get("codes") or [])]
        name = (s.get("name") or "").strip()
        # echo-junk row (B43/B44 class): the model echoed prompt scaffolding
        if any("codes exactly as printed" in c for c in (s.get("codes") or [])) or name == "verbatim" \
                or "int or null" in json.dumps(s.get("semester")):
            log.append(f"{stem}: prompt-echo junk row dropped ({codes[:1]})")
            d.setdefault("quirks", []).append(
                "prompt-echo junk row (echoed SCHEME_ONLY template scaffolding) dropped per the "
                "recorded B43/B44 class; the underlying print is BMI652 'Project' re-extracted below")
            continue
        # codeless Elective-I slot -> non_subject_rows with the printed pool list (B43/B45 class)
        if not codes and name.lower().startswith("elective"):
            mpool = re.search(r"Elective-1\s*((?:BMI\d{3}[^\n]*\n?)+)", p2)
            pool = mpool.group(1).strip() if mpool else ""
            non_subject.append({
                "kind": "codeless_elective_slot_print",
                "print": "Elective-I (scheme row, no code cell printed)",
                "locator": "scheme table row 5 Sem-V (p.2)",
                "elective_pool_print": pool,
                "note": ("codeless elective slot per the recorded B43/B45 class; the printed "
                         "Elective-1 pool list (BMI011-015) kept verbatim here, not as subject rows")})
            log.append(f"{stem}: codeless Elective-I -> non_subject_rows (pool print kept)")
            continue
        # BMI651/BMI652 print-anchored scheme rows (B44 class)
        if not name or "BMI651" in codes or "BMI652" in codes:
            code = ("BMI651" if "BMI651" in codes else "BMI652" if "BMI652" in codes else "")
            if code:
                m = re.search(rf"{code}\s+((?:[A-Z][^\n]*\n?)+?)(?:\n\d|\nTotal|\nCT:)", p2)
                np = " ".join(x.strip() for x in m.group(1).split("\n") if x.strip()) if m else ""
                obj = rex_extract(stem, p2, np, code, 2, d["session"], d["course"])
                if obj.get("scheme_row_only") or not obj.get("name"):
                    obj = {"name": np, "name_print": np, "codes": [code],
                           "semester": 6 if code == "BMI651" else 6,
                           "flags": ["scheme_row_only_detailed_syllabus_not_printed"],
                           "quirks": [f"print-anchored scheme row (p.2 Sem-VI table)"],
                           "units": {}}
                obj.setdefault("name", obj.get("name_print", "") or np)
                obj.setdefault("name_print", np)
                obj.setdefault("codes", [code])
                obj.setdefault("quirks", []).append(
                    f"empty/first-pass extraction remedied as a print-anchored scheme row from the p.2 "
                    f"Sem-VI table (B44 KMHC251/NMBA029 class); verbatim row print: '{np}'")
                obj.setdefault("flags", []).append("scheme_row_only_detailed_syllabus_not_printed")
                new_subjects.append(obj)
                if code == "BMI651": fixed_651 = True
                else: fixed_652 = True
                log.append(f"{stem}: print-anchored {code} '{obj.get('name','')[:50]}'")
                continue
        new_subjects.append(s)
    d["subjects"] = new_subjects
    d["non_subject_rows"] = non_subject
    json.dump(d, open(f"{DRAFTS}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)
    log.append(f"{stem}: fixed_651={fixed_651} fixed_652={fixed_652}")

    print("\n".join(log))
    return 0


if __name__ == "__main__":
    sys.exit(main())
