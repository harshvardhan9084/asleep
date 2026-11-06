#!/usr/bin/env python3
"""repair_b44.py — B44 draft repairs per the recorded remedy classes.

Classes exercised (all recorded in prior manifests):
  * B43 empty-name/zero-unit class: mercury REX via detail-page slices for
    theory rows whose extraction returned empty; print-anchor fallback.
  * B43 junk prompt-echo class: doc 07's prompt-echo row dropped.
  * B43 codeless elective-slot class: doc 07 'Elective 1*/2*/3*' scheme slot
    rows moved to non_subject_rows with verbatim prints + locators.
  * B43 doc-05/07 name-only association class: doc 04 KMLS151 'IT SKILLS
    LAB-1' associated via three agreeing orderings (scheme row order, footer
    code-list order, detail-page order).
  * B29 objectives-only / B17+ CO-only / B29 notes-only no-unit classes:
    evidence flags + verbatim objectives/notes transcribed from the text layer.
  * GAP false-positive remedy (v10 class): doc 05 'SCRM 187' book-TOC page
    reference recorded as printed non-subject evidence.
"""
import json, os, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

PARSEDD = "/home/z/my-project/work/pipeline_v2/parsed"
DRAFTSD = "/home/z/my-project/work/pipeline_v2/drafts"
INVD = "/home/z/my-project/work/pipeline_v2/inv"

# ---- page slices: (stem, code_label, page_start) — end = next detail page in inv
REX = [
    ("01_mba_healthcare-hospital_s2_syllabus_2022-23", "KMHC 208 : Digital Health Care and E-Commerce", 17),
    ("02_mba_healthcare-hospital_syllabus_2022-23", "KMHC 106 : Human Anatomy, Physiology and Medical Terminology", 13),
    ("03_mba_logistics-scm_y1_syllabus-rev_2024-25", "BMLS 102 : Managerial Economics", 7),
    ("03_mba_logistics-scm_y1_syllabus-rev_2024-25", "BMLS 104 : Business Statistics and Analytics", 11),
    ("03_mba_logistics-scm_y1_syllabus-rev_2024-25", "BMLS 151 : IT Skills -1", 20),
    ("03_mba_logistics-scm_y1_syllabus-rev_2024-25", "BMLS 204 : Financial Management and Corporate Finance", 31),
    ("05_mba_logistics-scm_y2_syllabus_2025-26", "BMLS 402 : Risks Management in Supply Chain and Logistics", 21),
    ("05_mba_logistics-scm_y2_syllabus_2025-26", "KVE 401 : Universal Human Values and Professional Ethics", 19),
    ("07_mba_syllabus_2013-14", "NMBA 016 : Marketing Management", 15),
    ("07_mba_syllabus_2013-14", "NMBA MK 01 : Consumer Behaviour & Customer Loyalty", 37),
    ("07_mba_syllabus_2013-14", "NMBA MK 03 : Retailing & Distribution Management", 39),
    ("08_mba_syllabus_2017-18", "RMB 302 : International Business Management", 11),
    ("10_mba_tourism-mgmt_syllabus-rev-aicte_2018-19", "KMT 101 : MANAGEMENT CONCEPT & INDIAN ETHOS", 3),
    ("10_mba_tourism-mgmt_syllabus-rev-aicte_2018-19", "KMT 106 : MARKETING MANAGEMENT – I", 14),
    ("10_mba_tourism-mgmt_syllabus-rev-aicte_2018-19", "KMT 108 : COMPUTER APPLICATIONS IN MANAGEMENT", 19),
    ("10_mba_tourism-mgmt_syllabus-rev-aicte_2018-19", "KMT 204 : FINANCIAL MANAGEMENT & CORPORATE FINANCE", 29),
]

# code token used to locate the draft row
CODE2ROW = {
    "01_mba_healthcare-hospital_s2_syllabus_2022-23": {"KMHC 208": "KMHC208"},
    "02_mba_healthcare-hospital_syllabus_2022-23": {"KMHC 106": "KMHC106"},
    "03_mba_logistics-scm_y1_syllabus-rev_2024-25": {"BMLS 102": "BMLS102", "BMLS 104": "BMLS104",
        "BMLS 151": "BMLS151", "BMLS 204": "BMLS204"},
    "05_mba_logistics-scm_y2_syllabus_2025-26": {"BMLS 402": "BMLS402", "KVE 401": "KVE401"},
    "07_mba_syllabus_2013-14": {"NMBA 016": "NMBA016", "NMBA MK 01": "NMBAMK01", "NMBA MK 03": "NMBAMK03"},
    "08_mba_syllabus_2017-18": {"RMB 302": "RMB302"},
    "10_mba_tourism-mgmt_syllabus-rev-aicte_2018-19": {"KMT 101": "KMT101", "KMT 106": "KMT106",
        "KMT 108": "KMT108", "KMT 204": "KMT204"},
}


def pages_of_file(stem):
    t = open(f"{PARSEDD}/{stem}.fulltext.txt").read()
    parts = re.split(r"===== PAGE (\d+) =====", t)
    P = {}
    for i in range(1, len(parts) - 1, 2):
        P[int(parts[i])] = parts[i + 1]
    return t, P


def slice_end(stem, start):
    inv = json.load(open(f"{INVD}/{stem}.inv.json"))
    dps = sorted({int(s.get("page") or 0) for s in inv if s.get("class") == "detail" and int(s.get("page") or 0) > start})
    return dps[0] if dps else start + 2


def find_row(draft, code):
    for i, s in enumerate(draft["subjects"]):
        cs = [re.sub(r"[^A-Za-z0-9]", "", c).upper() for c in (s.get("codes") or [])]
        if code.upper() in cs:
            return i
    return -1


def rex(stem, label, pstart, session, course):
    t, P = pages_of_file(stem)
    pend = slice_end(stem, pstart)
    txt = "\n\n".join(P[p] for p in sorted(P) if pstart <= p < pend)
    code = label.split(" :")[0]
    meta = {"file": stem + ".pdf"}
    prompt = me.EXTRACT % (label.split(": ", 1)[-1], code, pstart, session, course,
                           label.split(": ", 1)[-1], code, txt)
    out = me.chat([{"role": "system", "content": me.SYS},
                   {"role": "user", "content": prompt}], max_tokens=8000)
    if isinstance(out, list):
        out = next((x for x in out if isinstance(x, dict)), {})
    return out, pstart, pend


def main():
    q = json.load(open("/home/z/my-project/work/pipeline_v2/queue.json"))
    qmeta = {}
    for e in q["entries"]:
        qmeta[os.path.basename(e["rel"])] = e

    # ---------- 1. REX pass ----------
    for stem, label, pstart in REX:
        dp = json.load(open(f"{DRAFTSD}/{stem}.draft.json"))
        code = CODE2ROW[stem][label.split(" :")[0]]
        idx = find_row(dp, code)
        if idx < 0:
            print(f"REX-SKIP|{stem}|{code}|row not found"); continue
        row = dp["subjects"][idx]
        if row.get("units") and row.get("name"):
            print(f"REX-SKIP|{stem}|{code}|already complete"); continue
        session, course = dp.get("session", ""), dp.get("course", "")
        try:
            out, ps, pe = rex(stem, label, pstart, session, course)
        except Exception as e:  # noqa: BLE001 — one retry, then print-anchor
            print(f"REX-ERR|{stem}|{code}|{repr(e)[:100]}")
            try:
                out, ps, pe = rex(stem, label, pstart, session, course)
            except Exception as e2:  # noqa: BLE001
                print(f"REX-FAIL2|{stem}|{code}|{repr(e2)[:100]}")
                continue
        # validate: at least a name or units
        name = (out.get("name") or "").strip() or (out.get("name_print") or "").strip()
        if not name:
            # print-anchor from the slice head: "CODE : NAME" or "CODE\nNAME"
            _, P = pages_of_file(stem)
            head = P[ps][:300]
            m = re.search(re.escape(code.split()[0]) + r"[^A-Za-z0-9]*[0-9]+\s*[:\-]?\s*\n?\s*([A-Za-z& ,\.\-'\u2013]{4,70})", head)
            name = m.group(1).strip().rstrip('.') if m else ""
            if name:
                out["name_print"] = out.get("name_print") or name
                out.setdefault("quirks", []).append("name print-anchored from detail header (model returned empty)")
        out["name"] = name or row.get("name", "")
        out["name_print"] = (out.get("name_print") or row.get("name_print") or "").strip()
        codes = [re.sub(r"[^A-Za-z0-9]", "", c) for c in (out.get("codes") or []) if str(c).strip()]
        if code not in [c.upper() for c in codes]:
            codes.append(code)
        out["codes"] = codes
        out.setdefault("quirks", []).append(
            f"repair_b44 REX: subject re-extracted from detail slice pp.{ps}-{pe} via the "
            f"mercury-3 pool (recorded B43 empty-name/zero-unit class)")
        # merge: keep prior row's identity fields, replace content fields
        merged = dict(row)
        for k, v in out.items():
            if k in ("units", "cos", "textbooks", "reference_books", "experiments",
                     "objectives_print", "marks", "ltp", "credit", "semester",
                     "subject_type", "prerequisites", "name", "name_print", "codes"):
                if v not in (None, [], {}):
                    merged[k] = v
        dp["subjects"][idx] = merged
        json.dump(dp, open(f"{DRAFTSD}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)
        u = len(merged.get("units") or {})
        print(f"REX-OK|{stem}|{code}|name={merged.get('name','')[:44]!r}|units={u}")

    # ---------- 2. print-anchored patches ----------
    def add_flag(row, flag, quirk):
        fl = row.setdefault("flags", [])
        if flag not in fl:
            fl.append(flag)
        qs = row.setdefault("quirks", [])
        if quirk not in qs:
            qs.append(quirk)

    # doc 01 KMHC252 Mini Project — prose note p.19 (no units/COs/objectives by print)
    stem = "01_mba_healthcare-hospital_s2_syllabus_2022-23"
    dp = json.load(open(f"{DRAFTSD}/{stem}.draft.json"))
    _, P = pages_of_file(stem)
    i = find_row(dp, "KMHC252")
    if i >= 0 and not dp["subjects"][i].get("units"):
        row = dp["subjects"][i]
        row["name"] = row["name"] or "Mini Project"
        row.setdefault("quirks", []).append(
            "repair_b44: detail p.19 prints a project DESCRIPTION NOTE only (hospital study report "
            "topics + assessment by faculty guide and external examiner) — no unit theory, no CO "
            "table, no numbered experiments printed (RULES §6 visible print)")
        add_flag(row, "practical_turns_notes_only_no_units_printed",
                 "repair_b44: notes-only no-unit print (B29 recorded class)")
        json.dump(dp, open(f"{DRAFTSD}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)
        print(f"PATCH|{stem}|KMHC252|notes-only")

    # doc 04 KMLS151 IT SKILLS LAB-1 (three-ordering association) + KMLS206 scheme-only
    stem = "04_mba_logistics-scm_y1_syllabus_2020-21"
    dp = json.load(open(f"{DRAFTSD}/{stem}.draft.json"))
    i = find_row(dp, "KMLS151")
    if i >= 0:
        row = dp["subjects"][i]
        row["name"] = "IT Skills Lab -1"
        row["name_print"] = "IT SKILLS LAB-1"
        obj = ("Course Objectives (p.18 print): 1. To provide knowledge about the functioning of "
               "spreadsheet software and its advanced features for business data analysis.")
        row.setdefault("objectives_print", [obj])
        add_flag(row, "objectives_only_no_units_printed",
                 "repair_b44: lab detail p.18 prints Course Objectives only — no unit theory, no "
                 "numbered experiment list (RULES §6 print)")
        row.setdefault("quirks", []).append(
            "repair_b44: code KMLS151 not printed on the detail page (name-only print, B43 doc-05/07 "
            "class) — associated via three agreeing orderings: scheme p.3 row order (row 8 'IT Skills "
            "Lab -1'), footer code list p.3 (KMLS101 KMLS105 KMLS106 KMLS151 KMLS152), detail-page "
            "order (p.18 IT SKILLS LAB-1, p.20 MINI PROJECT -1); corroborated by sibling-session "
            "2024-25 book printing BMLS151 IT Skills -1")
        print(f"PATCH|{stem}|KMLS151|objectives-only + association")
    i = find_row(dp, "KMLS206")
    if i >= 0 and not dp["subjects"][i].get("units"):
        row = dp["subjects"][i]
        row["name"] = row["name"] or "Quantitative Techniques for Managers"
        row["name_print"] = row["name_print"] or "Quantitative Techniques for Managers"
        add_flag(row, "scheme_row_only_detailed_syllabus_not_printed",
                 "repair_b44: code KMLS206 prints ONLY in the scheme table (p.4 row 6, 'Quantitative "
                 "Techniques for Managers' 3-1-0 30/20/50/100/150); no detail page in this document "
                 "(recorded B23/B25/B27 zero-GAP class)")
        print(f"PATCH|{stem}|KMLS206|scheme-row-only")
    json.dump(dp, open(f"{DRAFTSD}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)

    # doc 04 KMLS152/KMLS252 mini projects — objectives printed on name-only details
    stem = "04_mba_logistics-scm_y1_syllabus_2020-21"
    dp = json.load(open(f"{DRAFTSD}/{stem}.draft.json"))
    for code, pg, nm in (("KMLS152", 20, "MINI PROJECT -1"), ("KMLS252", 36, "MINI PROJECT -2")):
        i = find_row(dp, code)
        if i >= 0 and not dp["subjects"][i].get("units"):
            row = dp["subjects"][i]
            add_flag(row, "objectives_only_no_units_printed",
                     f"repair_b44: detail p.{pg} prints objectives + project-work prose only — no unit "
                     "theory, no numbered experiments (RULES §6 print)")
            row.setdefault("quirks", []).append(
                f"repair_b44: detail p.{pg} prints the name '{nm}' with objectives and project-work "
                "prose; the code prints only in the scheme/footer (B43 name-only association class)")
            print(f"PATCH|{stem}|{code}|objectives-only")
    json.dump(dp, open(f"{DRAFTSD}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)

    # doc 03 BMLS152/BMLS252 mini projects — objectives printed on detail pages
    stem = "03_mba_logistics-scm_y1_syllabus-rev_2024-25"
    dp = json.load(open(f"{DRAFTSD}/{stem}.draft.json"))
    for code, pg in (("BMLS152", 22), ("BMLS252", 40)):
        i = find_row(dp, code)
        if i >= 0 and not dp["subjects"][i].get("units"):
            row = dp["subjects"][i]
            add_flag(row, "objectives_only_no_units_printed",
                     f"repair_b44: detail p.{pg} prints Course Objective list + project-work prose "
                     "only — no unit theory, no numbered experiments (RULES §6 print)")
            print(f"PATCH|{stem}|{code}|objectives-only")
    json.dump(dp, open(f"{DRAFTSD}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)

    # doc 08 RMB351 Summer Training — prose notes p.6
    stem = "08_mba_syllabus_2017-18"
    dp = json.load(open(f"{DRAFTSD}/{stem}.draft.json"))
    _, P = pages_of_file(stem)
    i = find_row(dp, "RMB351")
    if i >= 0 and not dp["subjects"][i].get("units"):
        row = dp["subjects"][i]
        note = P[6]
        m = re.search(r"1\..*?(?=EVALUATION|ESE|End Semester|$)", note, re.S)
        row["notes_print"] = (m.group(0).strip()[:1200] if m else "Summer Training Project Report rules (p.6)")
        add_flag(row, "practical_turns_notes_only_no_units_printed",
                 "repair_b44: detail p.6 prints training-rule NOTES (numbered prose, on-the-job "
                 "training 6-8 weeks, live-problem analysis) — no unit theory, no CO table, no "
                 "numbered experiments (RULES §6 print)")
        print(f"PATCH|{stem}|RMB351|notes-only")
    json.dump(dp, open(f"{DRAFTSD}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)

    # doc 10 KMT209 Comprehensive Viva — prose note p.39
    stem = "10_mba_tourism-mgmt_syllabus-rev-aicte_2018-19"
    dp = json.load(open(f"{DRAFTSD}/{stem}.draft.json"))
    _, P = pages_of_file(stem)
    i = find_row(dp, "KMT209")
    if i >= 0 and not dp["subjects"][i].get("units"):
        row = dp["subjects"][i]
        row["notes_print"] = P[39].strip()[:600]
        add_flag(row, "practical_turns_notes_only_no_units_printed",
                 "repair_b44: detail p.39 prints a viva DESCRIPTION NOTE only (end-of-2nd-semester "
                 "assessment of conceptual understanding + articulation) — no unit theory, no CO "
                 "table, no numbered experiments (RULES §6 print)")
        print(f"PATCH|{stem}|KMT209|notes-only")
    json.dump(dp, open(f"{DRAFTSD}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)

    # ---------- 3. doc 07 junk row drop + elective slots -> non_subject_rows ----------
    stem = "07_mba_syllabus_2013-14"
    dp = json.load(open(f"{DRAFTSD}/{stem}.draft.json"))
    junk = [i for i, s in enumerate(dp["subjects"])
            if "codes exactly as printed" in str(s.get("codes")) or "BPE071" in str(s.get("codes"))]
    for i in sorted(junk, reverse=True):
        print(f"DROP|{stem}|junk prompt-echo row [{i}] (B43 class)")
        del dp["subjects"][i]
    moved = 0
    keep = []
    for s in dp["subjects"]:
        nm = (s.get("name") or s.get("name_print") or "").strip()
        codes = [c for c in (s.get("codes") or []) if str(c).strip()]
        if (nm.startswith("Elective ") or nm == "") and not codes and \
                s.get("flags") and any("scheme" in f for f in s.get("flags")):
            dp.setdefault("non_subject_rows", []).append({
                "kind": "elective_slot_scheme_row",
                "print": f"Specialization Group slot row — verbatim scheme cell 'Elective 1*/2*/3*' "
                         f"(codeless print); scheme table row: {nm!r}",
                "locator": "pp.4-5 (Sem III/IV STUDY AND EVALUATION SCHEME tables; "
                           "Specialization Group -1/-2 Elective 1*/2*/3* rows, marks 30/20/50/100/150)"})
            moved += 1
            continue
        keep.append(s)
    dp["subjects"] = keep
    print(f"MOVE|{stem}|{moved} codeless Elective-slot rows -> non_subject_rows (B43 class)")
    json.dump(dp, open(f"{DRAFTSD}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)

    # ---------- 4. doc 05 SCRM187 non-subject evidence ----------
    stem = "05_mba_logistics-scm_y2_syllabus_2025-26"
    dp = json.load(open(f"{DRAFTSD}/{stem}.draft.json"))
    t, P = pages_of_file(stem)
    pg = next((n for n in sorted(P) if "SCRM 187" in P[n]), None)
    if pg:
        seg = re.search(r"[^\n]*SCRM 187[^\n]*", P[pg])
        dp.setdefault("non_subject_rows", []).append({
            "kind": "book_toc_reference",
            "print": seg.group(0).strip() if seg else "Problems with integrating SCRM 187",
            "locator": f"p.{pg} — printed table-of-contents page-numbers of the Unit-II textbook "
                       "'Supply Chain Risk Management' (SCRM 187 / SCRM 190 are book page refs, not "
                       "subject codes; v10 non-subject-evidence class)"})
        print(f"PATCH|{stem}|SCRM187|book-TOC non_subject_row p.{pg}")
    json.dump(dp, open(f"{DRAFTSD}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)

    # ---------- 5. generic evidence-flag pass over remaining no-unit rows ----------
    for fn in sorted(os.listdir(DRAFTSD)):
        if not (fn.startswith(("01_mba", "02_mba", "03_mba", "04_mba", "05_mba",
                                "06_mba", "07_mba", "08_mba", "10_mba")) and fn.endswith(".draft.json")):
            continue
        stem = fn[:-len(".draft.json")]
        dp = json.load(open(f"{DRAFTSD}/{fn}"))
        chg = 0
        for s in dp["subjects"]:
            if s.get("units"):
                continue
            fl = [str(f).lower() for f in (s.get("flags") or [])]
            if any(("scheme" in f and ("only" in f or "not_printed" in f)) or
                   "co_only_no_units_printed" in f or "objectives_only_no_units_printed" in f or
                   "notes_only_no_units" in f for f in fl):
                continue
            if s.get("cos"):
                add_flag(s, "co_only_no_units_printed",
                         "repair_b44: subject prints a CO/evaluation table but no unit theory "
                         "(B17+ recorded class, RULES §6 print)")
                chg += 1
            elif s.get("objectives_print"):
                add_flag(s, "objectives_only_no_units_printed",
                         "repair_b44: subject prints objectives but no unit theory (B29 recorded class)")
                chg += 1
        if chg:
            json.dump(dp, open(f"{DRAFTSD}/{fn}", "w"), indent=1, ensure_ascii=False)
            print(f"FLAGPASS|{stem}|{chg} rows evidence-flagged")


if __name__ == "__main__":
    main()
