#!/usr/bin/env python3
"""repair_b43_round2.py — retry the 3 failed/weak re-extracts once; on another
API failure, fall back to print-anchored names + verbatim objectives capture
(recorded no-unit/objectives-only class). Never guesses: anchors cite prints."""
import json, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

BASE = "/home/z/my-project/work/pipeline_v2"
PARSED = f"{BASE}/parsed"
DRAFTS = f"{BASE}/drafts"

JOBS = [
    {"stem": "02_mba_business-analytics_y1_syllabus_2024-25", "code_print": "BMBA 205",
     "code_norm": "BMBA205", "hint": "Database Management System and SQL", "pages": (31, 32),
     "anchor_evidence": ("detail p.31 header prints 'DATABASE MANAGEMENT SYSTEM AND SQL BMBA 205 Course Credit: 3 "
                         "Contact Hours: 40 Course Objectives: 1. To provide a comprehensive understanding of "
                         "database management systems…' (name-before-code header)"),
     "anchor_pat": (r"DATABASE MANAGEMENT SYSTEM AND SQL\s*\n?\s*BMBA ?205(.{0,1400}?)(?:===== PAGE|\Z)")},
    {"stem": "08_mba_common_y2_syllabus_2025-26", "code_print": "BMB FM 03",
     "code_norm": "BMBFM03", "hint": "Financial Credit and Risk Analysis", "pages": (30, 31),
     "anchor_evidence": ("detail p.30 header prints 'Financial Credit and Risk Analysis BMB FM 03 Course Credit: 3 "
                         "Total Hours 40 Course Objectives: 1. To understand the fundamentals of risk management…'; "
                         "menu p.? prints 'BMB FM 03 FINANCIAL AND CREDIT RISK ANALYSIS' (both prints kept)"),
     "anchor_pat": (r"Financial Credit and Risk Analysis\s*\n?\s*BMB ?FM ?03(.{0,1400}?)(?:===== PAGE|\Z)")},
    {"stem": "04_mba_business-analytics_y2_syllabus_2025-26", "code_print": "BMBA MK 01",
     "code_norm": "BMBAMK01", "hint": "Consumer Behaviour and Neuro Marketing", "pages": (15, 17),
     "anchor_evidence": ("detail p.15 header prints 'CONSUMER BEHAVIOUR AND NEURO MARKETING BMBA MK 01 Course Credit: 3 "
                         "Total Hours: 40 Course Objectives: 1. Understand the fundamental concepts, theories, and "
                         "models of consumer behaviour…'; menu p.4 prints the same title as 'BMBMK 01' (variant print kept)"),
     "anchor_pat": (r"CONSUMER BEHAVIOUR AND NEURO MARKETING\s*\n?\s*BMBA ?MK ?01(.{0,1600}?)(?:===== PAGE|\Z)")},
]


def pages_of(fulltext):
    parts = re.split(r"===== PAGE (\d+) =====", fulltext)
    return [(int(parts[i]), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def set_obj(draft, code_norm, obj):
    for i, s in enumerate(draft["subjects"]):
        cs = {re.sub(r"[^A-Z0-9]", "", (c or "").upper()) for c in (s.get("codes") or [])}
        if code_norm in cs:
            obj.setdefault("quirks", []).append(
                "row repaired in-batch round 2: prior extraction returned empty/invalid output")
            draft["subjects"][i] = obj
            return True
    return False


def anchor_fallback(draft, job, fulltext):
    m = re.search(job["anchor_pat"], fulltext, re.S)
    objs = []
    if m:
        raw = m.group(1)
        om = re.search(r"Course Objectives?:?\s*(.*)", raw, re.S | re.I)
        if om:
            objs = [x.strip() for x in re.split(r"\s*\d+\.\s*", om.group(1)) if x.strip()][:8]
    obj = {"name": job["hint"], "name_print": job["hint"], "codes": [job["code_print"]],
           "units": {}, "objectives_print": objs, "quirks": [], "flags": []}
    if objs:
        obj["flags"].append("objectives_only_no_units_printed")
    obj.setdefault("quirks", []).append(
        "print-anchored name + objectives (B42 empty-name class remedy, second-round API fallback): " + job["anchor_evidence"])
    ok = set_obj(draft, job["code_norm"], obj)
    return ok, len(objs)


def main():
    for job in JOBS:
        P = f"{DRAFTS}/{job['stem']}.draft.json"
        draft = json.load(open(P))
        rec = json.load(open(f"{PARSED}/{job['stem']}.json"))
        meta = rec.get("meta", rec)
        fulltext = open(f"{PARSED}/{job['stem']}.fulltext.txt").read()
        PAGES = pages_of(fulltext)
        p1, p2 = job["pages"]
        sl = "\n\n".join(t for p, t in PAGES if p1 <= p <= p2)
        sub = {"class": "detail", "code_print": job["code_print"], "name_print": job["hint"], "page": p1}
        try:
            _, obj = me.extract_one(meta.get("file", job["stem"] + ".pdf"), sl, meta, sub,
                                    draft.get("session", ""), draft.get("course", "MBA"))
        except Exception as e:
            print("REX2-FAIL", job["code_norm"], repr(e)[:100], "-> print-anchor fallback")
            ok, n = anchor_fallback(draft, job, fulltext)
            json.dump(draft, open(P, "w"), indent=1, ensure_ascii=False)
            print("ANCHOR2", job["code_norm"], ok, "objectives:", n)
            continue
        nm = (obj.get("name") or "").strip()
        if not nm or not obj.get("units"):
            print("REX2-WEAK", job["code_norm"], "name:", nm[:40], "units:", len(obj.get("units") or {}), "-> anchor fallback")
            ok, n = anchor_fallback(draft, job, fulltext)
            json.dump(draft, open(P, "w"), indent=1, ensure_ascii=False)
            print("ANCHOR2", job["code_norm"], ok, "objectives:", n)
            continue
        ok = set_obj(draft, job["code_norm"], obj)
        json.dump(draft, open(P, "w"), indent=1, ensure_ascii=False)
        print("REX2-OK", job["code_norm"], "|", nm[:44], "| units:", len(obj.get("units") or {}), "| replaced:", ok)
    print("ROUND2 DONE")


if __name__ == "__main__":
    main()
