#!/usr/bin/env python3
"""b49_assemble_d01.py — assemble the doc-01 draft (CHE y4 2016-17 scanned print)
from the three page-image transcription parts (B49-D01-A/B/C subagents).

Classes applied (recorded precedents):
- elective_slot codeless rows -> non_subject_rows (B48 doc-01 class)
- notes-only practical/project/seminar/training rows -> flag notes_only_no_units_printed (B47/B48 class)
- scheme_row_only flag dropped where detail units arrived
- book-list tails recorded as non_syllabus_page parts get attached to their subject
"""
import json, re

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
PARTS = [f"{DRAFTS}/b49_d01_part{p}.json" for p in "ABC"]
OUT = f"{DRAFTS}/01_btech_che_y4_syllabus.draft.json"

def ncode(c):
    return re.sub(r"[^A-Z0-9]", "", (c or "").upper())

def _parse_books(text):
    """Parse a numbered book-list print blob into [{"no":n,"book":...}] entries."""
    out = []
    cur = None
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(\d{1,2})[\.\)]\s*(.+)$", line)
        if m and len(m.group(2)) > 4:
            if cur:
                out.append(cur)
            cur = {"no": int(m.group(1)), "book": m.group(2).strip()}
        elif cur:
            cur["book"] = (cur["book"] + " " + line).strip()
    if cur:
        out.append(cur)
    return out

def norm_name(s):
    nm = s.get("name_print") or s.get("name") or ""
    nm = re.sub(r"^[A-Z]{2,4}[\s\-]?[0-9]{2,3}[A-Z]?\s*:?\s*", "", nm)
    nm = re.sub(r"\s*\(\d\s*:\s*\d\s*:\s*\d\)\s*$", "", nm)
    return nm.strip()

parts = [json.load(open(p)) for p in PARTS]
by_key, order = {}, []

SEM7 = {"NCH701","NCH702","NCH751","NCH752","NCH753","NGP701","NCH016","NCH017","NCH018","NCH021","NCH022","NCH023"}
SEM8 = {"NCH801","NCH802","NCH851","NCH852","NGP801","NCH031","NCH032","NCH033"}
TYPE = {
    "NCH701":"core","NCH702":"core","NCH801":"core","NCH802":"core",
    "NCH751":"lab","NCH752":"training","NCH753":"project","NCH851":"seminar","NCH852":"project",
    "NGP701":"gp","NGP801":"gp",
    "NCH016":"open-elective","NCH017":"open-elective","NCH018":"open-elective",
    "NCH021":"departmental-elective","NCH022":"departmental-elective","NCH023":"departmental-elective",
    "NCH031":"departmental-elective","NCH032":"departmental-elective","NCH033":"departmental-elective",
}

def key_of(s):
    for c in (s.get("codes") or []):
        k = ncode(c)
        if k:
            return k
    return "N:" + re.sub(r"\W+", "", (s.get("name_print") or "")).upper()

def put(s, source):
    k = key_of(s)
    if k not in by_key:
        by_key[k] = {"sources": []}
        order.append(k)
    by_key[k]["sources"].append(source)
    cur = by_key[k]
    # units: prefer the part with more units
    nu = s.get("units") or {}
    cu = cur.get("units") or {}
    if len(nu) > len(cu):
        cur["units"] = nu
    elif nu and nu != cu:
        # merge missing unit keys, keep longer text on conflicts
        m = dict(cu)
        for u, t in nu.items():
            if u not in m or len(str(t)) > len(str(m[u])):
                m[u] = t
        cur["units"] = m
    # books / experiments / cos: union by length
    for fld in ("textbooks", "reference_books", "experiments", "cos", "objectives_print"):
        if s.get(fld) and len(s.get(fld) or []) > len(cur.get(fld) or []):
            cur[fld] = s[fld]
    # scheme metadata (ltp/credit/marks) only from part A scheme rows (page==1)
    if s.get("page") == 1 and source is parts[0]:
        for fld in ("ltp", "credit", "marks"):
            if s.get(fld) not in (None, "", {}) and cur.get(fld) in (None, "", {}):
                cur[fld] = s[fld]
        if s.get("codes_print") and not cur.get("codes_print"):
            cur["codes_print"] = s["codes_print"]
        if s.get("scheme_name_print") and not cur.get("scheme_name_print"):
            cur["scheme_name_print"] = s["scheme_name_print"]
    # name_print: prefer detail header (page>1)
    if s.get("page", 1) > 1 or cur.get("page", 1) == 1:
        cur.setdefault("name_print", norm_name(s)) if not cur.get("name_print") else None
    # flags union
    fl = set(cur.get("flags") or []) | set(s.get("flags") or [])
    cur["flags"] = sorted(fl)
    # quirks union
    qs = list(cur.get("quirks") or [])
    for q in (s.get("quirks") or []):
        if q not in qs:
            qs.append(q)
    cur["quirks"] = qs
    # codes union
    cs = list(cur.get("codes") or [])
    for c in (s.get("codes") or []):
        if c not in cs:
            cs.append(c)
    cur["codes"] = cs
    if s.get("description_print") and not cur.get("description_print"):
        cur["description_print"] = s["description_print"]
    cur.setdefault("pages", set()).add(str(s.get("page")))

for pi, part in enumerate(parts):
    for s in part["subjects"]:
        # scheme rows from part A carry a scheme name cell; stash it
        if pi == 0:
            s["scheme_name_print"] = s.get("name_print") or ""
        put(s, part)

out_subjects = []
for k in order:
    rec = by_key[k]
    src_a = rec["sources"][0] if rec["sources"] else {}
    name = rec.get("name_print") or norm_name(src_a)
    subject = {
        "name": name.title() if name.isupper() else name,
        "name_print": name,
        "codes": rec.get("codes") or [],
        "codes_print": rec.get("codes_print") or (rec.get("codes") or [""])[0],
        "semester": 7 if k in SEM7 else (8 if k in SEM8 else None),
        "ltp": rec.get("ltp"),
        "credit": rec.get("credit"),
        "marks": rec.get("marks"),
        "subject_type": TYPE.get(k, "core"),
        "units": rec.get("units") or {},
        "lectures_per_unit": None,
        "cos": rec.get("cos") or [],
        "textbooks": rec.get("textbooks") or [],
        "reference_books": rec.get("reference_books") or [],
        "experiments": rec.get("experiments") or [],
        "objectives_print": rec.get("objectives_print") or [],
        "prerequisites": "",
        "quirks": rec.get("quirks") or [],
        "flags": [f for f in (rec.get("flags") or []) if f != "scheme_row_only" or len(rec.get("units") or {}) == 0],
        "pages_covered": sorted(rec.get("pages", set())),
    }
    if rec.get("scheme_name_print") and rec.get("scheme_name_print") != name:
        subject["quirks"].append(
            f"scheme-table name cell prints '{rec['scheme_name_print']}' vs detail header '{name}' (both kept)")
    if rec.get("description_print"):
        subject["flags"] = sorted(set(subject["flags"]) | {"notes_only_no_units_printed"})
        subject["quirks"].append("no units printed on detail page; guideline/description paragraph kept verbatim in description_print (B47/B48 notes-only class)")
    out_subjects.append(subject)

# attach book tails
nsr_all, quirks = [], []
for pi, part in enumerate(parts):
    for n in part["non_subject_rows"]:
        kind = n.get("kind", "")
        pr = n.get("print", "") or ""
        loc = n.get("locator", "")
        if kind == "non_syllabus_page" and "NCH-701" in pr:
            tgt = by_key.get("NCH701")
            if tgt:
                b = _parse_books(pr)
                if b:
                    tgt["textbooks"] = (tgt.get("textbooks") or []) + b
                    tgt.setdefault("quirks", []).append(
                        f"book list tail (p.5) attached from continuation page; locator: {loc}")
                continue
        if kind == "continuation_of_previous_subject_books" and "Lees" in pr:
            tgt = by_key.get("NCH801")
            if tgt:
                b = _parse_books(pr)
                if b:
                    tgt["reference_books"] = (tgt.get("reference_books") or []) + b
                    tgt.setdefault("quirks", []).append(
                        f"reference-books tail (p.9, Lees) attached from continuation page; locator: {loc}")
                continue
        nsr_all.append({"kind": kind, "print": pr, "locator": loc})

for part in parts:
    for q in (part.get("quirks") or []):
        if q not in quirks:
            quirks.append(q)
quirks.append("text layer empty (CamScanner scan, 11 pp); all content transcribed from page images by 3 parsing subagents with per-page evidence (RULES §6: visible print authoritative)")
quirks.append("doc print carries session: 'Effective from the Session 2016-17' (p.1) — draft session set from print per §1b despite no_session_found queue dir")

draft = {
    "pdf_rel": "repo_asleep/PDFs/5-course/no_session_found/btech_che_y4_syllabus.pdf",
    "session": "2016-17",
    "course": "BTech",
    "sha16": "9ef4e84f74fad8d3",
    "stem": "01_btech_che_y4_syllabus",
    "branch_print": "B. Tech. (Chemical Engineering)",
    "subjects": out_subjects,
    "non_subject_rows": nsr_all,
    "quirks": quirks,
    "flags": ["page-image-transcription-source"],
}
json.dump(draft, open(OUT, "w"), indent=1, ensure_ascii=False)
print("ASSEMBLED|", OUT, "| subjects:", len(out_subjects), "| nsr:", len(nsr_all), "| quirks:", len(quirks))
for s in out_subjects:
    print("  ", (s["codes"] or ["-"])[0], "|", s["name_print"][:45], "| units:", len(s["units"]), "| sem:", s["semester"], "| flags:", s["flags"])
