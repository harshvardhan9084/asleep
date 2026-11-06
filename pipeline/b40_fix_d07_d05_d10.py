#!/usr/bin/env python3
"""b40_fix_d07_d05_d10.py — targeted verify remedies for batch 40.

d07: NEC-042/NIC-044 + NEC-044/NIC-045 printed with FULL detail (p.20/p.21) in
     the 2016-17 corroborating copy — the initial inventory missed them (GAP:
     NEC042,NEC044,NIC044,NIC045). Extract via mercury-3 (detail slices) and
     append; the merge ladder converges them on doc 06's rows via Tier-0 code
     identity (same session, same course).
d05: KVE 301/401 + RVE 301/401 print ONLY as PREREQUISITE lines of the
     Human-Values-family electives (p.3 ROE070 header, p.21 ROE088/ROE080
     region, p.32 ROE087 region) — HISTORY-ONLY-CODE-MENTION class: fill the
     rows' prerequisites verbatim AND record the mentions in non_subject_rows
     (v10 B06 remedy path; the GAP scan reads non_subject_rows).
d10: VISION FOR HUMANE SOCIETY book 14 'Slow is Beautiful, Cecile Andrews' —
     the publisher URL '(http://www.newsociety.com/Books/S/Slow-is- Beautiful)'
     prints AFTER the p.16→p.17 page junction (off-page fragment, RULES §6);
     quirk the junction so the book-containment WARN is evidence-recorded.
"""
import json, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
q = json.load(open("/home/z/my-project/work/pipeline_v2/queue.json"))


def qentry(basename):
    for e in q["entries"]:
        if e["rel"].endswith("/" + basename):
            return e
    return {}


def page_slice(fulltext, p_from, p_to=None):
    PAGES = me.pages_of(fulltext)
    return "\n\n".join(t for p, t in PAGES if p >= p_from and (p_to is None or p < p_to))


# ---------- d07: two paired-elective detail extractions ----------
stem = "07_btech_y4_syllabus_2016-17_2"
P = f"{DRAFTS}/{stem}.draft.json"
draft = json.load(open(P))
fulltext = open(f"{PARSED}/{stem}.fulltext.txt").read()
e = qentry("btech_y4_syllabus_2016-17_2.pdf")
session, course = e.get("session", ""), e.get("course", "BTech")
pdf_name = json.load(open(f"{PARSED}/{stem}.json")).get("meta", {}).get("file", "x.pdf")

jobs = [
    {"class": "detail", "code_print": "NEC 042/NIC-044",
     "name_print": "DIGITAL SYSTEM DESIGN USING VHDL", "page": 20},
    {"class": "detail", "code_print": "NEC 044/NIC-045",
     "name_print": "ADVANCED DISPLAY TECHNOLOGIES & SYSTEMS", "page": 21},
]
have = {c for s in draft["subjects"] for c in (s.get("codes") or [])}
for sub in jobs:
    norm = sub["code_print"].replace(" ", "")
    if any(norm.replace("-", "") in c.replace("-", "") for c in have):
        print(f"d07|skip {sub['code_print']} (codes already in draft)")
        continue
    slice_txt = page_slice(fulltext, sub["page"], sub["page"] + 2)
    code, obj = me.extract_one(pdf_name, slice_txt, {}, sub, session, course)
    if obj.get("scheme_row_only"):
        obj.pop("scheme_row_only", None)
        obj["flags"] = [f for f in (obj.get("flags") or []) if "scheme_row_only" not in f]
        obj["quirks"] = [x for x in (obj.get("quirks") or []) if "scheme table row only" not in x]
    obj["units"] = me.units_dict(obj.get("units"))
    obj.setdefault("name", obj.get("name_print", ""))
    obj.setdefault("codes", [c.replace(" ", "") for c in sub["code_print"].split("/")])
    obj.setdefault("quirks", []).append(
        "paired-cell code print '%s' (Elective-III list p.11 + detail header p.%s); "
        "detail extracted from the corroborating 2016-17 copy (b40_fix_d07)" % (sub["code_print"], sub["page"]))
    obj.setdefault("flags", [])
    draft["subjects"].append(obj)
    json.dump(draft, open(P, "w"), indent=1, ensure_ascii=False)
    print(f"d07|SUBJ {sub['code_print']} | {obj.get('name','')[:40]} | units: {list((obj.get('units') or {}).keys())} "
          f"| containment: { {k: round(me.contained(v, fulltext), 2) for k, v in (obj.get('units') or {}).items()} }")
draft["subjects"].sort(key=lambda o: (o.get("codes") or [""])[0])
json.dump(draft, open(P, "w"), indent=1, ensure_ascii=False)
print("d07|DRAFT", len(draft["subjects"]), "subjects")

# ---------- d05: prerequisite mentions ----------
stem = "05_btech_y4_open-electives_2020-21"
P = f"{DRAFTS}/{stem}.draft.json"
draft = json.load(open(P))
fulltext = open(f"{PARSED}/{stem}.fulltext.txt").read()
fixed = 0
for s in draft["subjects"]:
    code = (s.get("codes") or [""])[0]
    if code == "ROE070" and not s.get("prerequisites"):
        s["prerequisites"] = "KVE 301/401- Universal Human Values and Professional Ethics"
        s.setdefault("quirks", []).append(
            "prerequisite printed as 'KVE 301/401- Universal Human Values and Professional Ethics' (p.3 header block); "
            "KVE301/KVE401 are prerequisite mentions only — not subjects of this document "
            "(HISTORY-ONLY-CODE-MENTION class; recorded in non_subject_rows)")
        fixed += 1
    if code == "ROE087" and not s.get("prerequisites"):
        s["prerequisites"] = "RVE 301/401- Universal Human Values and Professional Ethics"
        s.setdefault("quirks", []).append(
            "prerequisite printed as 'RVE 301/401- Universal Human Values and Professional Ethics' (p.32 header block); "
            "RVE301/RVE401 are prerequisite mentions only — not subjects of this document "
            "(HISTORY-ONLY-CODE-MENTION class; recorded in non_subject_rows)")
    if code == "ROE 080" or code == "ROE080":
        if not s.get("prerequisites"):
            s["prerequisites"] = "RVE 301/401- Universal Human Values and Professional Ethics"
            s.setdefault("quirks", []).append(
                "prerequisite printed as 'RVE 301/401- Universal Human Values and Professional Ethics' (p.21 header block); "
                "RVE301/RVE401 are prerequisite mentions only — not subjects of this document "
                "(HISTORY-ONLY-CODE-MENTION class; recorded in non_subject_rows)")
            fixed += 1
nsr = draft.setdefault("non_subject_rows", [])
nsr.append({"kind": "prerequisite_mention",
            "print": "Prerequisite: KVE 301/401- Universal Human Values and Professional Ethics (ROE070 Human Values in Sankhya, Yoga and Vedanta header, p.3)",
            "locator": "p.3"})
nsr.append({"kind": "prerequisite_mention",
            "print": "Prerequisite: RVE 301/401- Universal Human Values and Professional Ethics (Human Values in Bauddha and Jain Darshan header, p.21; Human Values in Madhyasth Darshan header, p.32)",
            "locator": "p.21, p.32"})
json.dump(draft, open(P, "w"), indent=1, ensure_ascii=False)
print("d05|prerequisites filled on", fixed, "rows; non_subject_rows:", len(nsr))

# ---------- d10: book-14 page-junction quirk ----------
stem = "10_btech_y4s7_open-electives_2025-26"
P = f"{DRAFTS}/{stem}.draft.json"
draft = json.load(open(P))
for s in draft["subjects"]:
    if (s.get("codes") or [""])[0] == "BOE076":
        for b in s.get("textbooks", []):
            if "Slow is Beautiful" in b.get("book", ""):
                b["book"] = "Slow is Beautiful, Cecile Andrews"
                s.setdefault("quirks", []).append(
                    "book 14 prints as 'Slow is Beautiful, Cecile Andrews' with its publisher URL "
                    "'(http://www.newsociety.com/Books/S/Slow-is- Beautiful)' landing AFTER the p.16->p.17 "
                    "page junction (off-page fragment class, RULES §6 visible-print-authoritative); "
                    "URL recorded here, book string kept as the printed line")
                print("d10|book-14 junction quirk recorded")
json.dump(draft, open(P, "w"), indent=1, ensure_ascii=False)
