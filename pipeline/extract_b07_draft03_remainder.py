#!/usr/bin/env python3
"""extract_b07_draft03_remainder.py — main-agent extraction of the remaining
subjects for draft 03 (btech_ag_y2_scheme-syllabus_2017-18) after 3 failed
subagent attempts (2x max-turns, 1x resume). Programmatic line-range slicing
from the parse fulltext guarantees byte-exact verbatim transcription.

Adds: 8 detailed subjects (RAG401/402/403, RAG451-454, RME408) + 8 scheme_only
slot subjects (RVE301/RAS302, RAS402/RVE401, RME101*, RCE151*, RME201*, RCE251*,
ROE030-039 pool, ROE040-049 pool) + non_subject_rows + doc-level quirks/flags.
"""
import json

DRAFT = "/home/z/my-project/work/pipeline_v2/drafts/03_btech_ag_y2_scheme-syllabus_2017-18.draft.json"
FT = "/home/z/my-project/work/pipeline_v2/parsed/03_btech_ag_y2_scheme-syllabus_2017-18.fulltext.txt"

lines = open(FT, encoding="utf-8").read().split("\n")  # 0-based; file line N = lines[N-1]


def seg(a, b):
    """Join fulltext lines a..b (1-based inclusive), stripping line edges,
    joining wraps with a single space (line-wrap flatten policy of this draft)."""
    return " ".join(ln.strip() for ln in lines[a - 1:b] if ln.strip())


def numbered(a, b):
    """Parse 'N. text' item lists with wrapped continuations into [{'no':N,'text':...}]."""
    import re
    items, cur = [], None
    for ln in lines[a - 1:b]:
        t = ln.strip()
        if not t:
            continue
        m = re.match(r"^(\d+)\.\s*(.*)$", t)
        if m:
            if cur:
                items.append(cur)
            cur = {"no": int(m.group(1)), m.group(0).split(":", 1)[0][:4].strip() and "exp": m.group(2)}
            cur = {"no": int(m.group(1)), "exp": m.group(2)}
        elif cur is not None:
            cur["exp"] = (cur["exp"] + " " + t).strip()
    if cur:
        items.append(cur)
    return items


def numbered_books(a, b):
    import re
    items, cur = [], None
    for ln in lines[a - 1:b]:
        t = ln.strip()
        if not t:
            continue
        m = re.match(r"^(\d+)\.\s*(.*)$", t)
        if m:
            if cur:
                items.append(cur)
            cur = {"no": int(m.group(1)), "book": m.group(2)}
        elif cur is not None:
            cur["book"] = (cur["book"] + " " + t).strip()
    if cur:
        items.append(cur)
    return items


TH = {"sessional_ct": 20, "sessional_ta": 10, "sessional_total": 30, "ese_te_pe": 70, "total": 100}
LB = {"sessional_ct": 30, "sessional_ta": 20, "sessional_total": 50, "ese_te_pe": 50, "total": 100}

subjects = [
    {
        "name": "FARM MACHINERY AND EQUIPMENT-I", "name_print": "FARM MACHINERY AND EQUIPMENT-I",
        "codes": ["RAG401"], "semester": 4, "ltp": {"l": 3, "t": 0, "p": 0}, "credit": 3,
        "marks": dict(TH), "subject_type": "core",
        "units": {"1": seg(667, 669), "2": seg(672, 677), "3": seg(680, 688), "4": seg(691, 692)},
        "textbooks": numbered_books(695, 700),
        "quirks": ["Only Units I-IV printed (p.12); no Unit-V anywhere in the document.",
                   "Printed typos kept verbatim: 'comprasion', 'owenering', 'machinries' (Unit-IV); 'seed-bed preparation .' spacing and 'Machinery  used' double space (Unit-II); 'machines.Tillage' missing space (Unit-II); 'Working of  seed drills' double space (Unit-III).",
                   "Books printed under heading 'Suggested Reading:' (p.12); book 5 wraps 'Saroj / Publication, Allahabad,' with trailing comma as printed."],
        "flags": [],
    },
    {
        "name": "POST HARVEST ENGG. OF CEREALS, PULSES & OIL SEEDS",
        "name_print": "POST HARVEST ENGG. OF CEREALS, PULSES & OIL SEEDS",
        "codes": ["RAG402"], "semester": 4, "ltp": {"l": 3, "t": 0, "p": 0}, "credit": 3,
        "marks": dict(TH), "subject_type": "core",
        "units": {"1": seg(714, 720), "2": seg(723, 731), "3": seg(734, 738), "4": seg(741, 746)},
        "textbooks": numbered_books(750, 758) + numbered_books(762, 767),
        "quirks": ["Heading spans two printed lines: 'RAG402: POST HARVEST ENGG. OF CEREALS, PULSES & OIL / SEEDS' (p.13).",
                   "Printed artifacts kept verbatim: ', And  Size reduction machinery:' capital-And with double space (Unit-I); curly apostrophes in \"Bond's law, Kick's law, Rittinger's law\"; 'stabilization of rice bran., Extrusion cooking' punctuation (Unit-IV).",
                   "Books span pp.13-14 (1-5 then 6-8 after the page break); 'Publishing house Pvt. Ltd.' lowercase 'house' (book 3) verbatim."],
        "flags": [],
    },
    {
        "name": "WATERSHED HYDROLOGY, SOIL & WATER CONSERVATION ENGINEERING",
        "name_print": "WATERSHED HYDROLOGY, SOIL & WATER CONSERVATION ENGINEERING",
        "codes": ["RAG403"], "semester": 4, "ltp": {"l": 3, "t": 1, "p": 0}, "credit": 4,
        "marks": dict(TH), "subject_type": "core",
        "units": {"1": seg(778, 784), "2": seg(787, 792), "3": seg(795, 801), "4": seg(804, 808), "5": seg(811, 815)},
        "textbooks": numbered_books(818, 821) + numbered_books(825, 839),
        "quirks": ["Sem-IV scheme row wraps the subject name into the L-T-P cell in the text layer: 'Watershed Hydrology, Soil & / Water Conservation Engineering 3-1-0' (p.3) — table cells are separate in print.",
                   "Subscript-style tokens kept verbatim: 'KE>25 and EI30 methods' (Unit-III).",
                   "Books span pp.15-16; 'Kalyani     Publishers' multiple internal spaces (book 8) verbatim; 'Cook's method' curly apostrophe (Unit-I, lab item 8)."],
        "flags": [],
    },
    {
        "name": "FARM MACHINERY AND EQUIPMENT-I LAB", "name_print": "FARM MACHINERY AND EQUIPMENT-I LAB",
        "codes": ["RAG451"], "semester": 4, "ltp": {"l": 0, "t": 0, "p": 2}, "credit": 1,
        "marks": dict(LB), "subject_type": "lab",
        "experiments": numbered(849, 859),
        "quirks": ["Lab experiments list printed p.17; no units, COs or books printed for this lab.",
                   "Printed typos kept verbatim: 'Problems on machinery management' capital-P mid-item (item 2)."],
        "flags": [],
    },
    {
        "name": "POST HARVEST ENGG. OF CEREALS, PULSES & OIL SEEDS LAB",
        "name_print": "POST HARVEST ENGG. OF CEREALS, PULSES & OIL SEEDS LAB",
        "codes": ["RAG452"], "semester": 4, "ltp": {"l": 0, "t": 0, "p": 2}, "credit": 1,
        "marks": dict(LB), "subject_type": "lab",
        "experiments": numbered(865, 880),
        "quirks": ["Heading spans two printed lines: 'RAG452: POST HARVEST ENGG. OF CEREALS, PULSES & OIL / SEEDS LAB' (p.17).",
                   "Trailing commas printed verbatim on items 2,3,6,7,8,10,11,12,13; 'equipments' plural verbatim (items 4,10,11,12)."],
        "flags": [],
    },
    {
        "name": "WATERSHED HYDROLOGY LAB", "name_print": "WATERSHED HYDROLOGY LAB",
        "codes": ["RAG453"], "semester": 4, "ltp": {"l": 0, "t": 0, "p": 2}, "credit": 1,
        "marks": dict(LB), "subject_type": "lab",
        "experiments": numbered(884, 893),
        "quirks": ["Lab prints near-duplicate items 2/3: 'Design of rain gauge network. Exercise on intensity - frequency - duration curves.' then 'Exercise on intensity-frequency-duration curves' (dash-spacing variants) — both kept verbatim (p.17).",
                   "Item 6 wraps 'missing data, test / for consistency' (p.17); item 8 ends 'rational / formula.'"],
        "flags": [],
    },
    {
        "name": "SOIL & WATER CONSERVATION ENGINEERING LAB", "name_print": "SOIL & WATER CONSERVATION ENGINEERING LAB",
        "codes": ["RAG454"], "semester": 4, "ltp": {"l": 0, "t": 0, "p": 2}, "credit": 1,
        "marks": dict(LB), "subject_type": "lab",
        "experiments": numbered(901, 907),
        "quirks": ["Lab experiments list printed p.18; no units, COs or books printed for this lab."],
        "flags": [],
    },
    {
        "name": "THEORY OF MACHINE AND MACHINE DESIGN", "name_print": "THEORY OF MACHINE AND MACHINE DESIGN",
        "codes": ["RME408"], "semester": 4, "ltp": {"l": 3, "t": 0, "p": 0}, "credit": 3,
        "marks": dict(TH), "subject_type": "core",
        "units": {"1": seg(626, 630), "2": seg(633, 636), "3": seg(639, 642), "4": seg(645, 649)},
        "textbooks": numbered_books(652, 657),
        "quirks": ["Detail heading prints 'THEORY OF MACHINE AND MACHINE DESIGN' (p.11) vs scheme row 'Theory of Machines & Machine Design' (p.3) — name variance; both forms preserved.",
                   "Unit-I opens without a sentence break: 'Introduction to machine and design Principle of design, Phases of design, design considerations.' — kept verbatim.",
                   "Only Units I-IV printed (p.11); no Unit-V anywhere in the document.",
                   "Book 1 wraps '12/4 / Asaf Ali Road' (p.11); book 3 'Bhandari V B. Machine Design Tata McGraw Hill' missing comma verbatim."],
        "flags": [],
    },
]

slot_note = ("Detail syllabus not printed anywhere in this document for either alternative "
             "(scheme-table row only); the pair's L-T-P/marks/credit print on the combined slot row.")
subjects += [
    {
        "name": "Universal Human Values  & Professional Ethics/ Environment & Ecology",
        "name_print": "Universal Human Values  & Professional Ethics/ Environment & Ecology",
        "codes": ["RVE301", "RAS302"], "semester": 3,
        "marks": dict(TH), "subject_type": "value-added",
        "scheme_line_print": "2. RVE301/ RAS302 Universal Human Values  & Professional Ethics/ Environment & Ecology | L-T-P 3-0-0 | ESE 70 | CT 20 | TA 10 | Total 100 | Credit 3 (p.2, 2nd Year III-SEMESTER scheme table)",
        "quirks": ["Scheme print carries double space 'Universal Human Values  &' (p.2).",
                   "Alternative-slot row: student takes either RVE301 or RAS302. " + slot_note],
        "flags": ["scheme_only", "alternative_pair_row", "detailed_syllabus_not_printed"],
    },
    {
        "name": "Environment & Ecology/ Universal Human Values  & Professional Ethics",
        "name_print": "Environment & Ecology/ Universal Human Values  & Professional Ethics",
        "codes": ["RAS402", "RVE401"], "semester": 4,
        "marks": dict(TH), "subject_type": "value-added",
        "scheme_line_print": "2. RAS402/ RVE401 Environment & Ecology/ Universal Human Values  & Professional Ethics | L-T-P 3-0-0 | ESE 70 | CT 20 | TA 10 | Total 100 | Credit 3 (p.3, 2nd Year IV-SEMESTER scheme table)",
        "quirks": ["Sem-IV mirror of the sem-III RVE301/RAS302 alternative slot. " + slot_note],
        "flags": ["scheme_only", "alternative_pair_row", "detailed_syllabus_not_printed"],
    },
    {
        "name": "Elements of Mechanical Engineering*", "name_print": "Elements of Mechanical Engineering*",
        "codes": ["RME101*"], "semester": 3, "ltp": {"l": 3, "t": 1, "p": 0},
        "marks": {"sessional_ct": 20, "sessional_ta": 10, "sessional_total": 30, "ese_te_pe": 70, "total": 100},
        "subject_type": "core",
        "scheme_line_print": "11. RME101* Elements of Mechanical Engineering* | L-T-P 3-1-0 | ESE 70 | CT 20 | TA 10 | Total 100* | Credit -- (p.2)",
        "quirks": ["Lateral-entry row (B.Sc.-stream students): credit cell prints '--' and Total prints '100*' (p.2).",
                   slot_note],
        "flags": ["scheme_only", "lateral_entry", "detailed_syllabus_not_printed"],
    },
    {
        "name": "Computer Aided Engineering Graphics*", "name_print": "Computer Aided Engineering Graphics*",
        "codes": ["RCE151*"], "semester": 3, "ltp": {"l": 0, "t": 0, "p": 3},
        "marks": {"sessional_ct": 30, "sessional_ta": 20, "sessional_total": 50, "ese_te_pe": 50, "total": 100},
        "subject_type": "core",
        "scheme_line_print": "12. RCE151* Computer Aided Engineering Graphics* | L-T-P 0-0-3 | ESE 50 | CT 30 | TA 20 | Total 100* | Credit -- (p.2)",
        "quirks": ["Lateral-entry row: credit '--', Total '100*' (p.2).", slot_note],
        "flags": ["scheme_only", "lateral_entry", "detailed_syllabus_not_printed"],
    },
    {
        "name": "Elements of Mechanical Engineering*", "name_print": "Elements of Mechanical Engineering*",
        "codes": ["RME201*"], "semester": 4, "ltp": {"l": 3, "t": 1, "p": 0},
        "marks": {"sessional_ct": 20, "sessional_ta": 10, "sessional_total": 30, "ese_te_pe": 70, "total": 100},
        "subject_type": "core",
        "scheme_line_print": "11. RME201* Elements of Mechanical Engineering* | L-T-P 3-1-0 | ESE 70 | CT 20 | TA 10 | Total 100* | Credit -- (p.3)",
        "quirks": ["Sem-IV lateral-entry mirror of RME101*: credit '--', Total '100*' (p.3).", slot_note],
        "flags": ["scheme_only", "lateral_entry", "detailed_syllabus_not_printed"],
    },
    {
        "name": "Computer Aided Engineering Graphics*", "name_print": "Computer Aided Engineering Graphics*",
        "codes": ["RCE251*"], "semester": 4, "ltp": {"l": 0, "t": 0, "p": 3},
        "marks": {"sessional_ct": 30, "sessional_ta": 20, "sessional_total": 50, "ese_te_pe": 50, "total": 100},
        "subject_type": "core",
        "scheme_line_print": "12. RCE251* Computer Aided Engineering Graphics* | L-T-P 0-0-3 | ESE 50 | CT 30 | TA 20 | Total 100* | Credit -- (p.3)",
        "quirks": ["Sem-IV lateral-entry mirror of RCE151*: credit '--', Total '100*' (p.3).", slot_note],
        "flags": ["scheme_only", "lateral_entry", "detailed_syllabus_not_printed"],
    },
    {
        "name": "Science Based Open Elective", "name_print": "Science Based Open Elective",
        "codes": [f"ROE0{n}" for n in range(30, 40)], "semester": 3,
        "subject_type": "open-elective",
        "scheme_line_print": "1. ROE030 to 039/ RAS304 Science Based Open Elective/ Engineering Mathematics-III | L-T-P 3-1-0 | ESE 70 | CT 20 | TA 10 | Total 100 | Credit 4 (p.2)",
        "quirks": ["Pool slot: ten sem-III Science-Based-Open-Elective codes ROE030-ROE039; the printed a-j pool list (p.2, identical on p.3) names each code pair ROE03x/ROE04x.",
                   "Alternative-slot row with RAS304 Engineering Mathematics-III (extracted separately as a detailed subject); L-T-P/marks/credit print on the combined row and may describe either alternative — zero-guess: not copied onto this pool row."],
        "flags": ["scheme_only", "elective_pool_slot", "detailed_syllabus_not_printed"],
    },
    {
        "name": "Science Based Open Elective", "name_print": "Science Based Open Elective",
        "codes": [f"ROE0{n}" for n in range(40, 50)], "semester": 4,
        "subject_type": "open-elective",
        "scheme_line_print": "1. RAS404/ ROE040 to 049 Mathematics-III/ Science Based Open Elective | L-T-P 3-1-0 | ESE 70 | CT 20 | TA 10 | Total 100 | Credit 4 (p.3)",
        "quirks": ["Sem-IV mirror pool of ROE040-ROE049; same a-j printed pool list (p.3).",
                   "Alternative-slot row with RAS404 (extracted within the detailed Engineering Mathematics-III subject)."],
        "flags": ["scheme_only", "elective_pool_slot", "detailed_syllabus_not_printed"],
    },
]

POOL_LIST = ("Science Based Open Electives: a. ROE030/ROE040 Manufacturing Process "
             "b. ROE031/ROE041 Introduction to soft computing c. ROE032/ROE042 Nano Science "
             "d. ROE033/ROE043 Laser System and Application e. ROE034/ROE044 Space Science "
             "f. ROE035/ROE045 Polymer Science & Technology g. ROE036/ROE046 Nuclear Science "
             "h. ROE037/ROE047 Material Science i. ROE038/ROE048 Discrete Mathematics "
             "j. ROE039/ROE049 Applied Linear Algebra")
LATERAL_NOTE = ("*B.Tech. IInd year lateral entry students belonging to B.Sc. Stream, shall clear "
                "the subjects RCE151/RCE251 and RME101/201 of the first year Engineering Programme "
                "along with the second year subjects.")

nsr = [
    {"kind": "cover", "print": seg(3, 11), "locator": "p.1"},
    {"kind": "scheme_table_header", "print": "2nd Year III-SEMESTER — S.No. Subject Code | Subject Name | L-T-P | ESE | Marks Sessional (CT/TA) | Total | Credit (12 rows)", "locator": "p.2"},
    {"kind": "scheme_table_header", "print": "2nd Year IV-SEMESTER — S.No. Subject Code | Subject Name | L-T-P | ESE | Marks Sessional Total (CT/TA) | Credit (12 rows)", "locator": "p.3"},
    {"kind": "scheme_total", "print": "Total 1000 24", "locator": "p.2 (III-SEMESTER table)"},
    {"kind": "scheme_total", "print": "Total 1000 24", "locator": "p.3 (IV-SEMESTER table)"},
    {"kind": "legend", "print": "CT: Class Test TA: Teacher Assessment L/T/P: Lecture/ Tutorial/ Practical", "locator": "p.2 and p.3 (identical)"},
    {"kind": "eligibility_note", "print": LATERAL_NOTE, "locator": "p.2 and p.3 (footnote, printed twice)"},
    {"kind": "elective_pool", "print": POOL_LIST, "locator": "p.2 and p.3 (identical list printed twice)"},
]

doc_quirks = [
    "RME408 detail heading prints 'THEORY OF MACHINE AND MACHINE DESIGN' vs scheme row 'Theory of Machines & Machine Design' — both forms preserved (pp.3/11).",
    "Scheme code cell prints 'REC358' for Basic Electronics Lab while its detail heading prints 'RECG358: BASIC ELECTRONICS LAB' (pp.2/10) — both carried on the subject's codes (pre-existing extraction).",
    "RAG453 lab prints near-duplicate experiment items 2/3 (dash-spacing variants) — both verbatim (p.17).",
    "Lateral-entry rows print credit '--' and Total '100*' (pp.2-3).",
    "Eligibility footnote and the Science Based Open Electives a-j list print identically TWICE (p.2 and p.3).",
    "Scheme tables label semesters '2nd Year III-SEMESTER' / '2nd Year IV-SEMESTER' (p.2/p.3).",
]

d = json.load(open(DRAFT, encoding="utf-8"))
have = {c for s in d["subjects"] for c in s.get("codes", [])}
added = []
for s in subjects:
    if have & set(s["codes"]):
        print("SKIP (code already on disk):", s["codes"])
        continue
    d["subjects"].append(s)
    added.append(s["codes"][0])
existing_nsr_kinds = {(r.get("kind"), r.get("locator")) for r in d.get("non_subject_rows", [])}
for r in nsr:
    if (r["kind"], r["locator"]) in existing_nsr_kinds:
        continue
    d.setdefault("non_subject_rows", []).append(r)
for q in doc_quirks:
    if q not in d.setdefault("quirks", []):
        d["quirks"].append(q)
for f in ["scheme_only_rows_present", "alternative_pair_slots", "lateral_entry_subjects", "elective_pool_slots"]:
    if f not in d.setdefault("flags", []):
        d["flags"].append(f)
json.dump(d, open(DRAFT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("ADDED|", added)
print("TOTAL subjects:", len(d["subjects"]), "| nsr:", len(d["non_subject_rows"]), "| quirks:", len(d["quirks"]), "| flags:", d["flags"])
