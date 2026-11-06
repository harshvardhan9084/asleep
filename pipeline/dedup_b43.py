#!/usr/bin/env python3
"""dedup_b43.py — post-repair draft hygiene (B43).

1) DEDUP: repair_b43.py round-1 had a tuple-index bug (it[1]=code_print passed
   as code_norm -> replace search never matched -> append path) leaving stale
   empty rows next to good ones. For each normalized primary code keep the
   RICHEST row (units desc, then name/objs/exps presence), drop the rest —
   decision logged per row.
2) NO-UNIT EVIDENCE FLAGS (recorded classes, B08/B19/B29/B42):
   objectives_only_no_units_printed (+objectives_print captured from print),
   scheme_row_only_detailed_syllabus_not_printed (scheme-row anchored names),
   lab_course_no_units_numbered_topic_list (experiments already present).
3) doc-07 elective-slot rows (no codes printed) -> non_subject_rows.
"""
import json, os, re

BASE = "/home/z/my-project/work/pipeline_v2"
DRAFTS = f"{BASE}/drafts"
PARSED = f"{BASE}/parsed"


def ncode(c):
    return re.sub(r"[^A-Z0-9]", "", (c or "").upper())


def richness(s):
    return (len(s.get("units") or {}), bool((s.get("name") or "").strip()),
            len(s.get("objectives_print") or []), len(s.get("experiments") or []),
            len(s.get("cos") or []))


def dedup(draft, stem):
    groups = {}
    for i, s in enumerate(draft["subjects"]):
        cs = {ncode(c) for c in (s.get("codes") or []) if ncode(c)}
        if not cs:
            continue
        key = tuple(sorted(cs))
        groups.setdefault(key, []).append((i, s))
    dropped = []
    for key, rows in groups.items():
        if len(rows) == 1:
            continue
        rows_sorted = sorted(rows, key=lambda t: richness(t[1]), reverse=True)
        keep = rows_sorted[0]
        for idx, s in rows_sorted[1:]:
            dropped.append((key[0], (s.get("name") or "")[:30], len(s.get("units") or {})))
            draft["subjects"][idx] = None
    if dropped:
        draft["subjects"] = [s for s in draft["subjects"] if s is not None]
    return dropped


def flag(draft, code_norm, flagname, quirk=None, objectives=None):
    for s in draft["subjects"]:
        cs = {ncode(c) for c in (s.get("codes") or [])}
        if code_norm in cs:
            fl = s.setdefault("flags", [])
            if flagname not in fl:
                fl.append(flagname)
            if objectives is not None and objectives and not s.get("objectives_print"):
                s["objectives_print"] = objectives
            if quirk:
                s.setdefault("quirks", []).append(quirk)
            return True
    return False


def capture_objectives(stem, pat):
    ft = open(f"{PARSED}/{stem}.fulltext.txt").read()
    m = re.search(pat, ft, re.S)
    if not m:
        return []
    raw = m.group(1)
    objs = [x.strip() for x in re.split(r"\s*\d+\.\s*", raw) if x.strip()]
    return objs[:10]


def main():
    total_dropped = 0
    for f in sorted(os.listdir(DRAFTS)):
        if not f.endswith(".draft.json"):
            continue
        P = f"{DRAFTS}/{f}"
        d = json.load(open(P))
        dropped = dedup(d, f[:2])
        total_dropped += len(dropped)
        for code, nm, nu in dropped:
            print(f"DEDUP {f[:2]} drop {code} name={nm!r} units={nu}")

        # move codeless elective-slot rows to non_subject_rows (doc 07)
        moved = 0
        keep = []
        for s in d["subjects"]:
            cs = [c for c in (s.get("codes") or []) if ncode(c)]
            nm = (s.get("name") or "").strip()
            if not cs and not nm:
                d.setdefault("non_subject_rows", []).append({
                    "kind": "elective_slot_row_no_code_print",
                    "print": json.dumps({k: s.get(k) for k in ("name_print", "ltp", "credit", "marks")}, ensure_ascii=False),
                    "locator": "scheme table row prints only 'Elective-N Specialization Group-M' with NO code cell "
                               "(recorded scheme-row class; specialization subjects are carried by the menu rows)",
                    "quirks": ["moved from subjects to non_subject_rows (no code, no name printed)"]})
                moved += 1
                continue
            keep.append(s)
        if moved:
            d["subjects"] = keep
            print(f"SLOTS-MOVED {f[:2]}: {moved}")
        json.dump(d, open(P, "w"), indent=1, ensure_ascii=False)

    # ---- targeted evidence patches ----
    patches = [
        ("01_mba_business-analytics_y1_syllabus_2020-21", "KMBA205", "scheme_row_only_detailed_syllabus_not_printed",
         "no detail page in this doc; name anchored from the printed scheme row p.3 (recorded class)", None),
        ("01_mba_business-analytics_y1_syllabus_2020-21", "KMBA152", "objectives_only_no_units_printed",
         "detail p.20 prints Course Objectives only (13 items captured verbatim); no unit theory printed", None),
        ("01_mba_business-analytics_y1_syllabus_2020-21", "KMBA254", "objectives_only_no_units_printed",
         "MINI PROJECT -2 prints objectives only (2 items captured verbatim); project row (recorded no-unit class)", None),
        ("02_mba_business-analytics_y1_syllabus_2024-25", "BMBA252", "scheme_row_only_detailed_syllabus_not_printed",
         "no detail page in this doc; name anchored from the printed scheme row (recorded class)", None),
        ("02_mba_business-analytics_y1_syllabus_2024-25", "BMBA254", "objectives_only_no_units_printed",
         "MINI PROJECT prints objectives only (2 items captured verbatim); project row (recorded no-unit class)", None),
        ("03_mba_business-analytics_y2_syllabus_2021-22", "KMBA351", "lab_course_no_units_numbered_topic_list",
         "lab row prints a numbered experiment/topic list (11 items captured); no unit theory printed", None),
        ("03_mba_business-analytics_y2_syllabus_2021-22", "KMBA352", "lab_course_no_units_numbered_topic_list",
         "lab row prints a numbered experiment/topic list (15 items captured); no unit theory printed", None),
        ("05_mba_common_y1_syllabus_2020-21", "KMBN152", "objectives_only_no_units_printed",
         "MINI PROJECT -1 prints objectives only (2 items captured verbatim); project row (recorded no-unit class)", None),
        ("06_mba_common_y1_syllabus_2024-25", "BMB152", "objectives_only_no_units_printed",
         "detail p.20 'MINI PROJECT -1 BMB 152 ( Scanning of ideas for opportunities )' prints objectives only; project row", None),
        ("06_mba_common_y1_syllabus_2024-25", "BMB252", "objectives_only_no_units_printed",
         "detail p.40 'MINI PROJECT -2 BMB 252 (Business Ideas Validation & Fesibility )' prints objectives only; project row (print typo 'Fesibility' kept verbatim)", None),
    ]
    for stem, code, fl, q, _ in patches:
        P = f"{DRAFTS}/{stem}.draft.json"
        d = json.load(open(P))
        if flag(d, code, fl, q):
            json.dump(d, open(P, "w"), indent=1, ensure_ascii=False)
            print("FLAG", stem[:2], code, "->", fl)
        else:
            print("FLAG-MISS", stem[:2], code)

    # objectives capture where print shows an objectives block but draft has none
    obj_caps = [
        ("04_mba_business-analytics_y2_syllabus_2025-26", "BMBA406",
         r"RESEARCH PROJECT REPORT & VIVA VOCE\s*\n?\s*Code: ?BMBA ?406(.{0,1500}?)(?:===== PAGE|\Z)",
         "detail p.54 'RESEARCH PROJECT REPORT & VIVA VOCE Code: BMBA 406' prints objectives only; project row"),
        ("05_mba_common_y1_syllabus_2020-21", "KMBN252",
         r"MINI PROJECT -2 Course Credit: 2\s*\n?\s*Seminar by students\s*\n?\s*Objective\s*[–-]?\s*(.{0,1200}?)(?:===== PAGE|MBA Revised|\Z)",
         "detail p.37 'MINI PROJECT -2 Course Credit: 2 Seminar by students Objective -…' prints objectives only; project row"),
    ]
    for stem, code, pat, q in obj_caps:
        P = f"{DRAFTS}/{stem}.draft.json"
        d = json.load(open(P))
        objs = capture_objectives(stem, pat)
        if flag(d, code, "objectives_only_no_units_printed", q, objectives=objs):
            json.dump(d, open(P, "w"), indent=1, ensure_ascii=False)
            print("FLAG+OBJ", stem[:2], code, "objs:", len(objs))
        else:
            print("FLAG-MISS", stem[:2], code)
    print("DEDUP/PATCH DONE, dropped:", total_dropped)


if __name__ == "__main__":
    main()
