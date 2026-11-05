#!/usr/bin/env python3
"""b36_scheme_resume.py — resume the failed scheme-only batch extraction for the
plastic y4 2025-26 draft (the 429-exhausted call left placeholder subjects).
Replaces each placeholder (flag extraction_failed_scheme_batch) with the real
verbatim scheme-row object from Mercury-3 (single consolidated call, 429-aware)."""
import json, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

P = "/home/z/my-project/work/pipeline_v2/drafts/09_btech_plastic_y4_syllabus_2025-26.draft.json"
parsed_dir = "/home/z/my-project/work/pipeline_v2/parsed"
stem = "09_btech_plastic_y4_syllabus_2025-26"

rec = json.load(open(f"{parsed_dir}/{stem}.json"))
meta = rec.get("meta", rec)
fulltext = open(f"{parsed_dir}/{stem}.fulltext.txt").read()
d = json.load(open(P))

# rebuild the inventory list for the placeholder subjects (from the doc's scheme
# table, verbatim prints preserved in the placeholders' name/codes)
bad = [s for s in d["subjects"] if "extraction_failed_scheme_batch" in (s.get("flags") or [])]
print("placeholders:", len(bad))
subs = [{"class": "scheme_only", "code_print": (s.get("codes") or [""])[0],
         "name_print": s.get("name_print", ""), "page": "?"} for s in bad]
code = me.extract_scheme_batch(fulltext, d["session"], d["course"], subs)

new_subjects, bi = [], 0
for s in d["subjects"]:
    if "extraction_failed_scheme_batch" in (s.get("flags") or []) and bi < len(code):
        c, obj = code[bi]; bi += 1
        obj.setdefault("name", obj.get("name_print", ""))
        obj.setdefault("codes", [c] if c else [])
        obj.setdefault("quirks", [])
        obj.setdefault("flags", [])
        new_subjects.append(obj)
    else:
        new_subjects.append(s)
d["subjects"] = new_subjects
if f"scheme_batch_failed" in str(d.get("flags")):
    d["flags"] = [f for f in d["flags"] if not str(f).startswith("scheme_batch_failed")]
json.dump(d, open(P, "w"), indent=1, ensure_ascii=False)
for s in d["subjects"]:
    print(s.get("name", "")[:38], "| codes:", s.get("codes"), "| flags:", (s.get("flags") or [])[:1])
