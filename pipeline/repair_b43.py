#!/usr/bin/env python3
"""repair_b43.py — B43 empty-name/zero-unit repairs (recorded B42 classes).

Class 1 (B42: extractor empty name_print, G3 blank-name): print-anchored names
  from scheme rows / menus / detail headers, evidence kept in quirks.
Class 2 (B42 name-before-code + B39/B41 deterministic-inv): API re-extraction
  for rows whose detail pages exist but extracted empty — via mercury_engine.
Class 3 (junk row): model echoed the prompt ('codes exactly as printed...') in
  doc 04 — dropped, recorded.
No guessing: every anchored name cites the printed locator in its quirk.
"""
import json, os, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

BASE = "/home/z/my-project/work/pipeline_v2"
PARSED = f"{BASE}/parsed"
DRAFTS = f"{BASE}/drafts"

# ---------- non-API repairs first ----------
def anchor(draft, code_norm, name, name_print, evidence, extra=None):
    hit = False
    for s in draft["subjects"]:
        cs = {re.sub(r"[^A-Z0-9]", "", (c or "").upper()) for c in (s.get("codes") or [])}
        if code_norm in cs:
            s["name"] = name
            s["name_print"] = name_print
            s.setdefault("quirks", []).append("print-anchored name (B42 empty-name class): " + evidence)
            if extra:
                s.update(extra)
            hit = True
            break
    if not hit:
        print("ANCHOR-MISS", code_norm)
    return hit


def drop_junk(draft):
    kept = []
    dropped = []
    for s in draft["subjects"]:
        cs = " ".join((s.get("codes") or [])).lower()
        nm = (s.get("name") or "").strip()
        if ("codes exactly as printed" in cs) or (not nm and not (s.get("units")) and "scheme_row_only" in (s.get("flags") or [])):
            dropped.append(sorted(cs))
            continue
        kept.append(s)
    draft["subjects"] = kept
    return dropped


jobs_anchor = [
    ("01_mba_business-analytics_y1_syllabus_2020-21", "KMBA205",
     "Operations Management", "OPERATIONS MANAGEMENT",
     "scheme row p.3 prints '5 KMBA205 OPERATIONS MANAGEMENT 3 1 0 30 20 0 50 100 0 150 3'; no detail page in this doc"),
    ("02_mba_business-analytics_y1_syllabus_2024-25", "BMBA252",
     "Analytics Project using R / Python", "Analytics Project using R / Python",
     "scheme row prints '8 BMBA252 Analytics Project using R / Python 0 0 3 0 0 30 30 0 70 100 2'; no detail page in this doc"),
    ("04_mba_business-analytics_y2_syllabus_2025-26", "BMBAHR03",
     "Performance and Reward Management", "BMBA HR03 Performance and Reward Management",
     "specialization menu p.5 prints 'BMBA HR03 Performance and Reward Management' (IV Semester list); no detail page in this doc"),
    ("04_mba_business-analytics_y2_syllabus_2025-26", "BMBAOM05",
     "Project & Sourcing Management", "BMBA OM05 Project & Sourcing Management",
     "specialization menu p.5 prints 'BMBA OM05 Project & Sourcing Management' (IV Semester list); no detail page in this doc"),
]

# doc 05 KMBN252: anchor + capture the printed objectives block verbatim
def repair_05(draft):
    ft = open(f"{PARSED}/05_mba_common_y1_syllabus_2020-21.fulltext.txt").read()
    m = re.search(r"MINI PROJECT -2 Course Credit: 2 Seminar by students Objective – (.{0,700}?)MBA Revised CURRICULUM", ft, re.S)
    objs = []
    if m:
        raw = m.group(1)
        objs = [x.strip() for x in re.split(r"\s*\d+\.\s*", raw) if x.strip()]
    ev = ("detail p.37 header prints 'MINI PROJECT -2 Course Credit: 2 Seminar by students Objective -…'; the printed "
          "code KMBN252 appears only in the p.3 footer code list (KMBN201 KMBN207 KMBN208 KMBN251 KMBN252) — association "
          "by three agreeing orderings (footer list order, scheme-row order '10 MINI PROJECT -2', detail-page order) "
          "corroborated by sibling 2024-25 doc 06 which prints 'BMB 252 MINI PROJECT -2' explicitly (recorded "
          "name-before-code/footer-list class)")
    ok = anchor(draft, "KMBN252", "Mini Project -2", "MINI PROJECT -2", ev,
                extra={"objectives_print": objs, "flags": (["objectives_only_no_units_printed"] if objs else [])})
    for s in draft["subjects"]:
        cs = {re.sub(r"[^A-Z0-9]", "", (c or "").upper()) for c in (s.get("codes") or [])}
        if "KMBN252" in cs:
            s.setdefault("quirks", []).append("project row: unit text not printed in this doc (recorded no-unit class)")
    return ok


# ---------- API re-extractions (detail pages exist) ----------
REX = [
    ("01_mba_business-analytics_y1_syllabus_2020-21", "KMBA152", "KMBA152", "Basics of Data Management with R", 20, 21),
    ("02_mba_business-analytics_y1_syllabus_2024-25", "BMBA151", "IT SKILLS-1 BMBA151", "IT Skills-1", 16, 17),
    ("02_mba_business-analytics_y1_syllabus_2024-25", "BMBA205", "BMBA 205", "Database Management System and SQL", 31, 32),
    ("03_mba_business-analytics_y2_syllabus_2021-22", "KMBA 305", "KMBA305", "Marketing Analytics", 17, 18),
    ("03_mba_business-analytics_y2_syllabus_2021-22", "KMBA404", "KMBA404", "Healthcare Analytics", 31, 32),
    ("04_mba_business-analytics_y2_syllabus_2025-26", "BMBA MK 01", "BMBAMK01", "Consumer Behaviour and Neuro Marketing", 15, 17),
    ("04_mba_business-analytics_y2_syllabus_2025-26", "BMBA MK02", "BMBAMK02", "Marketing Analytics", 18, 19),
    ("04_mba_business-analytics_y2_syllabus_2025-26", "BMBA MK03", "BMBAMK03", "Artificial Intelligence for Marketing", 20, 21),
    ("06_mba_common_y1_syllabus_2024-25", "BMB 104", "BMB104", "Business Statistics & Analytics", 10, 11),
    ("07_mba_common_y2_syllabus_2021-22", "KMBN IT05", "KMBNIT05", "Business Data Warehousing & Data Mining", 67, 68),
    ("08_mba_common_y2_syllabus_2025-26", "BMB FM 01", "BMBFM01", "Investment and Portfolio Management", 26, 27),
    ("08_mba_common_y2_syllabus_2025-26", "BMB FM 03", "BMBFM03", "Financial Credit and Risk Analysis", 30, 31),
]


def pages_of(fulltext):
    parts = re.split(r"===== PAGE (\d+) =====", fulltext)
    return [(int(parts[i]), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def main():
    # phase 1: non-API repairs
    for stem, code_norm, name, np, ev in jobs_anchor:
        P = f"{DRAFTS}/{stem}.draft.json"
        d = json.load(open(P))
        if anchor(d, code_norm, name, np, ev):
            json.dump(d, open(P, "w"), indent=1, ensure_ascii=False)
            print("ANCHORED", stem[:2], code_norm, "->", name)
    P05 = f"{DRAFTS}/05_mba_common_y1_syllabus_2020-21.draft.json"
    d05 = json.load(open(P05))
    if repair_05(d05):
        json.dump(d05, open(P05, "w"), indent=1, ensure_ascii=False)
        print("ANCHORED 05 KMBN252 -> Mini Project -2 (+objectives)")
    P04 = f"{DRAFTS}/04_mba_business-analytics_y2_syllabus_2025-26.draft.json"
    d04 = json.load(open(P04))
    dropped = drop_junk(d04)
    json.dump(d04, open(P04, "w"), indent=1, ensure_ascii=False)
    print("JUNK-DROPPED", dropped)

    # phase 2: API re-extractions, 2 workers (<=5 concurrent cap)
    lock = threading.Lock()
    def do(item):
        stem, code_print, code_norm, hint, p1, p2 = item
        rec = json.load(open(f"{PARSED}/{stem}.json"))
        meta = rec.get("meta", rec)
        draft = json.load(open(f"{DRAFTS}/{stem}.draft.json"))
        fulltext = open(f"{PARSED}/{stem}.fulltext.txt").read()
        PAGES = pages_of(fulltext)
        sl = "\n\n".join(t for p, t in PAGES if p1 <= p <= p2)
        sub = {"class": "detail", "code_print": code_print, "name_print": hint, "page": p1}
        session, course = draft.get("session", ""), draft.get("course", "MBA")
        code, obj = me.extract_one(meta.get("file", stem + ".pdf"), sl, meta, sub, session, course)
        return stem, code_norm, obj

    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(do, it): it for it in REX}
        for fut in as_completed(futs):
            it = futs[fut]
            stem, code_norm = it[0], it[1]
            try:
                _, _, obj = fut.result()
            except Exception as e:
                print("REX-FAIL", stem[:2], code_norm, repr(e)[:120])
                continue
            with lock:
                P = f"{DRAFTS}/{stem}.draft.json"
                draft = json.load(open(P))
                replaced = False
                for i, s in enumerate(draft["subjects"]):
                    cs = {re.sub(r"[^A-Z0-9]", "", (c or "").upper()) for c in (s.get("codes") or [])}
                    if code_norm in cs:
                        obj.setdefault("quirks", []).append(
                            "row repaired in-batch: prior extraction returned empty name/units; re-extracted from the "
                            "printed detail pages (B42 empty-name class remedy)")
                        draft["subjects"][i] = obj
                        replaced = True
                        break
                if not replaced:
                    obj.setdefault("codes", [re.sub(r"[^A-Za-z0-9*]", "", it[2]) if False else it[2]])
                    obj.setdefault("quirks", []).append("row appended by in-batch repair (was missing)")
                    draft["subjects"].append(obj)
                json.dump(draft, open(P, "w"), indent=1, ensure_ascii=False)
                print("REX-OK", stem[:2], code_norm, "| name:", (obj.get("name") or "")[:44],
                      "| units:", len(obj.get("units") or {}))
    print("REPAIR DONE")


if __name__ == "__main__":
    main()
