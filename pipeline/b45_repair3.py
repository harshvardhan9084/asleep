#!/usr/bin/env python3
"""b45_repair3.py — final small repairs:
  - doc 07: dedup identical NONCREDIT pair
  - doc 08: MBAMK02 '. (III Semester)' name cleanup
  - objectives-only evidence flags (recorded B44 class) for 6 zero-unit rows
  - doc 01: verbatim print-typo quirk on 'Comprehaensive Viva'
"""
import json

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"


def load(stem):
    return json.load(open(f"{DRAFTS}/{stem}.draft.json"))


def save(stem, d):
    json.dump(d, open(f"{DRAFTS}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)


# 1. doc 07 dedup
stem = "07_mba_y1_model-curriculum_2018-19"
d = load(stem)
nc = [s for s in d["subjects"] if (s.get("codes") or [""])[0].upper() == "NONCREDIT"]
if len(nc) == 2:
    d["subjects"] = [s for s in d["subjects"] if s not in nc[1:]]
    d["subjects"][-1].setdefault("quirks", []).append(
        "scheme prints this non-credit row once (p.2); the model returned it twice — single row kept (B44 dedup class)")
    save(stem, d)
    print("DOC07 dedup ->", len(d["subjects"]))
else:
    print("DOC07 NONCREDIT count:", len(nc), "- no dedup")

# 2. doc 08 MBAMK02
stem = "08_mba_y1_scheme_2008-09"
d = load(stem)
for s in d["subjects"]:
    if (s.get("name") or "").startswith("Marketing Research."):
        s.setdefault("quirks", []).append(
            "scheme prints 'Marketing Research. (III Semester)'; name cleaned, verbatim kept in name_print (B44 dots class)")
        s["name_print"] = s.get("name_print") or s["name"]
        s["name"] = "Marketing Research"
        save(stem, d)
        print("DOC08 MBAMK02 cleaned")
        break

# 3. objectives-only evidence flags
OBJ_FLAG = "objectives_only_no_units_printed"
OBJ_QUIRK = ("detailed page prints course objectives / course outcomes / evaluation criteria only; "
             "no unit-wise syllabus is printed for this subject in this document (RULES §6: print is "
             "authoritative; recorded B44 objectives-only class)")
for stem, codes in [
    ("02_mba_tourism-mgmt_syllabus_2017-18", ["RMT351", "RMT451"]),
    ("05_mba_travel-tourism_y1_syllabus_2020-21", ["KMTT251", "KMTT252"]),
    ("06_mba_travel-tourism_y2_syllabus_2021-22", ["KMTT-307", "KMTT408"]),
]:
    d = load(stem)
    for s in d["subjects"]:
        if any(c.replace("-", "") in codes for c in (s.get("codes") or [])):
            if OBJ_FLAG not in (s.get("flags") or []):
                s.setdefault("flags", []).append(OBJ_FLAG)
                s.setdefault("quirks", []).append(OBJ_QUIRK)
                print("FLAG", stem[:2], s.get("codes"))
    save(stem, d)

# 4. doc 01 viva typo quirk
stem = "01_mba_tourism-mgmt_syllabus_2016-17"
d = load(stem)
for s in d["subjects"]:
    if (s.get("name") or "").startswith("Comprehaensive"):
        s.setdefault("quirks", []).append("title printed with typo 'Comprehaensive' — verbatim p.2 print kept (RULES §6)")
        save(stem, d)
        print("DOC01 viva quirk added")
        break
