#!/usr/bin/env python3
"""B03 draft patches (evidence-recorded, deterministic):

1. scheme_only_print flags on subjects whose documents print ONLY a scheme row
   for them (probe: scripts/pipeline_v2/probe_b03_nounits.py — fulltext shows
   each code solely inside evaluation-scheme tables; no units/COs/practice
   lists printed anywhere in the doc):
   - 04 BVA451 Sports and Yoga-II (BCA y2 2025-26; scheme row + non-credit footnote)
   - 05 BBC552 Mini Project Lab / BBC651 Startup-Entrepreneurial Assessment /
     BBC652 Project (BCA y3 2026-27; draft quirks already record
     "No course outcomes, units, experiments or suggested readings are printed")
   - 09 BOP-245P Pharmaceutical Jurisprudence Project (2013-14; scheme row only;
     narrative paragraph already preserved in objectives_print)
   - 10 BP509P/BP610P/BP706PS/BP707P/BP815PW/BP816P (2019-20; all six appear
     only in evaluation-scheme tables)
2. draft 10 BP111P COMMUNIUCATION SKILLS (Practical): the card prints an
   unnumbered 'Course content:' module list (no Unit-I..V structure). The
   subagent captured it verbatim in the extension field content_raw_print and
   the books in textbooks, but left spec units empty — merge reads only spec
   fields, so the content is re-channeled VERBATIM into units["1"] with a
   structure quirk. Content slice: 'Course content:' up to 'Recommended Books:'
   (books stay in textbooks; tail after books = journals/margins, dropped from
   units but the raw card print remains in the draft's content_raw_print).
"""
import json

P = "/home/z/my-project/work/pipeline_v2"


def load(stem):
    return json.load(open(f"{P}/drafts/{stem}.draft.json"))


def save(stem, d):
    json.dump(d, open(f"{P}/drafts/{stem}.draft.json", "w"), ensure_ascii=False, indent=1)


def add_flag(d, code, flag):
    hits = [s for s in d["subjects"] if code in [c.replace(" ", "") for c in s.get("codes", [])]]
    assert len(hits) == 1, f"{code}: expected 1 subject, got {len(hits)}"
    s = hits[0]
    if flag not in s.get("flags", []):
        s.setdefault("flags", []).append(flag)
    return s


# 1) scheme-only flags
d4 = load("04_bca_y2_syllabus_2025-26")
add_flag(d4, "BVA451", "scheme_only_print")
save("04_bca_y2_syllabus_2025-26", d4)

d5 = load("05_bca_y3_syllabus_2026-27")
for c in ("BBC552", "BBC651", "BBC652"):
    add_flag(d5, c, "scheme_only_print")
save("05_bca_y3_syllabus_2026-27", d5)

d9 = load("09_bpharm_y1-2_syllabus_2013-14")
add_flag(d9, "BOP-245P", "scheme_only_print")
save("09_bpharm_y1-2_syllabus_2013-14", d9)

d10 = load("10_bpharm_y1-4_syllabus_2019-20")
for c in ("BP509P", "BP610P", "BP706PS", "BP707P", "BP815PW", "BP816P"):
    add_flag(d10, c, "scheme_only_print")

# 2) BP111P course content -> units["1"]
s = add_flag(d10, "BP111P", "flat_course_content_no_unit_structure")
raw = s.get("content_raw_print") or ""
i0 = raw.find("Course content:")
i1 = raw.find("Recommended Books:")
assert i0 >= 0 and i1 > i0, "BP111P content slice markers not found"
content = raw[i0:i1].strip()
assert len(content) > 300, f"BP111P content unexpectedly short: {len(content)}"
s["units"] = {"1": content}
q = ("Practical card prints 'Course content:' as an unnumbered module list "
     "(no Unit-I..V structure printed); stored verbatim as unit1 to preserve "
     "content within the fixed unit1-5 schema. Books printed on the same card "
     "are captured in textbooks; superscript edition tokens print as split "
     "lines ('2 nd Edition') — joined, artifact kept as printed evidence.")
if q not in s.get("quirks", []):
    s.setdefault("quirks", []).append(q)
save("10_bpharm_y1-4_syllabus_2019-20", d10)

print("PATCH-OK: 04(+1 flag), 05(+3), 09(+1), 10(+6 flags, BP111P units->1 verbatim content block)")
