#!/usr/bin/env python3
"""b36_scheme_resume2.py — code-keyed rebuild of the plastic doc's 8 scheme-only
rows. The previous resume mispaired rows by order and let one row echo the
prompt template. This version: pairs by normalized code token, drops non-code
echo rows, and ALWAYS keeps the verbatim name from the original inventory
placeholders (the scheme table prints these names)."""
import json, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

P = "/home/z/my-project/work/pipeline_v2/drafts/09_btech_plastic_y4_syllabus_2025-26.draft.json"
parsed_dir = "/home/z/my-project/work/pipeline_v2/parsed"
stem = "09_btech_plastic_y4_syllabus_2025-26"

rec = json.load(open(f"{parsed_dir}/{stem}.json"))
fulltext = open(f"{parsed_dir}/{stem}.fulltext.txt").read()
d = json.load(open(P))

VERBATIM_NAMES = {  # from the doc's scheme tables (Sem VII p.2 / Sem VIII p.3), verbatim
    "BOEP**1": None, "BOEP**2": None, "BOEP**3": None,
}
bad = [s for s in d["subjects"] if "extraction_failed_scheme_batch" in (s.get("flags") or [])]
subs = [{"class": "scheme_only", "code_print": (s.get("codes") or [""])[0],
         "name_print": s.get("name_print", ""), "page": "?"} for s in bad]
rows = me.extract_scheme_batch(fulltext, d["session"], d["course"], subs)


def code_key(code_str):
    """normalize a code print to a match key"""
    c = (code_str or "").upper().replace(" ", "")
    if "BOEP" in c:
        return "BOEP"
    m = re.match(r"([A-Z]{2,4})(\d{3})", c)
    return (m.group(1) + m.group(2)) if m else c


# drop rows that echo the prompt template (no real code token) and index by code
by_code = {}
for c, obj in rows:
    toks = obj.get("codes") or [c]
    key = code_key(toks[0] if toks else c)
    if key and re.match(r"^[A-Z]{2,6}", key) and key not in ("CODES",):
        by_code.setdefault(key, obj)

print("returned keys:", sorted(by_code))
new_subjects = []
for s in d["subjects"]:
    if "extraction_failed_scheme_batch" not in (s.get("flags") or []):
        new_subjects.append(s)
        continue
    key = code_key((s.get("codes") or [""])[0])
    obj = by_code.get(key) or {}
    name_print = s.get("name_print", "") or obj.get("name_print", "")
    codes = s.get("codes") or []
    entry = {
        "name": name_print,
        "name_print": name_print,
        "codes": codes,
        "semester": obj.get("semester"),
        "ltp": obj.get("ltp") or {},
        "credit": obj.get("credit"),
        "marks": obj.get("marks") or {},
        "subject_type": obj.get("subject_type") or "",
        "units": {},
        "cos": obj.get("cos") or [],
        "textbooks": [], "reference_books": [], "experiments": [],
        "objectives_print": [], "prerequisites": "",
        "quirks": list(dict.fromkeys((obj.get("quirks") or []) + [
            "scheme table row only (pp.2-3): detailed syllabus not printed in this document "
            "(recorded B23/B25/B27 zero-GAP class — flagged subject candidate for the ladder)"])),
        "flags": list(dict.fromkeys((obj.get("flags") or []) + [
            "scheme_row_only_detailed_syllabus_not_printed"])),
    }
    if "BOEP" in (codes[0] if codes else ""):
        entry["flags"].append("alternative_pair_row")
        entry["quirks"].append("code cell prints the Open-Elective pool slot 'BOEP**' (Open Elective-II/III/IV, "
                               "Offline/MOOCs learning mode) — pool print, not a specific code (k_era_pool class)")
    new_subjects.append(entry)

d["subjects"] = new_subjects
d["flags"] = [f for f in d.get("flags", []) if not str(f).startswith("scheme_batch_failed")]
json.dump(d, open(P, "w"), indent=1, ensure_ascii=False)
for s in d["subjects"]:
    print(s.get("name", "")[:42], "| codes:", s.get("codes"), "| units:", len(s.get("units") or {}),
          "| flags:", (s.get("flags") or [])[:1])
