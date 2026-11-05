#!/usr/bin/env python3
"""b36_scheme_deterministic.py — CRON-20261105-B36: rebuild the plastic y4
2025-26 draft's 8 scheme-only subjects VERBATIM from the printed scheme tables
(pp.2-3 of the fulltext, visible print authoritative RULES §6) after the
Mercury scheme-batch calls kept 429-failing/mispairing. Zero-guess: every
number below is transcribed from the printed rows shown in the fulltext;
column ambiguities are recorded as quirks (project rows print collapsed
CT/TA/PS/TE columns)."""
import json

P = "/home/z/my-project/work/pipeline_v2/drafts/09_btech_plastic_y4_syllabus_2025-26.draft.json"
d = json.load(open(P))

COMMON_QUIRK = ("scheme table row only (pp.2-3): detailed syllabus not printed in this document "
                "(recorded B23/B25/B27 zero-GAP class — flagged subject candidate for the ladder)")
OE_QUIRK = ("code cell prints the Open-Elective pool slot 'BOEP**' (Offline/MOOCs learning mode per the "
            "Sem-VII print, MOOCs per the Sem-VIII print) — pool print, not a specific code "
            "(k_era_pool class); Open Elective-II/III/IV are three separate scheme rows sharing it")
DE_SLOT_QUIRK = ("code cell prints the slot 'BPE071 to BPE074 Departmental Elective-IV' — all four member "
                 "codes (BPE071 Polymers for Energy Storage Applications, BPE072 Biomedical Plastics, "
                 "BPE073 Conducting Polymers, BPE074 Polymer Structure and Property relationship) carry "
                 "detailed syllabi printed in this same document (individual detail rows in this draft); "
                 "the detail-area table heading spells 'Departamental Elective-IV' (printed typo, kept "
                 "verbatim per RULES §6)")
PROJ_QUIRK = ("project/assessment print: Evaluation Scheme columns print collapsed (CT/TA/PS/TE/PE), the "
              "practical-sessional 'PS' column carries the full marks; recorded verbatim")


def row(name, codes, sem, ltp, credit, marks, extra_quirks, flags):
    return {"name": name, "name_print": name, "codes": codes, "semester": sem,
            "ltp": ltp, "credit": credit, "marks": marks, "subject_type": "project" if "BPE75" in codes[0] or "BPE851" in codes[0] else ("scheme-slot" if "BPE071to" in codes[0] else "open-elective"),
            "units": {}, "cos": [], "textbooks": [], "reference_books": [], "experiments": [],
            "objectives_print": [], "prerequisites": "",
            "quirks": [COMMON_QUIRK] + extra_quirks,
            "flags": ["scheme_row_only_detailed_syllabus_not_printed"] + flags}


SCHEME_ROWS = [
    row("Departmental Elective-IV", ["BPE071toBPE074"], 7, {"l": 3, "t": 0, "p": 0}, 3,
        {"sessional_ct": 20, "sessional_ta": 10, "sessional_total": 30, "ese_te_pe": 70, "total": 100},
        [DE_SLOT_QUIRK], ["alternative_pair_row"]),
    row("Open Elective-II", ["BOEP**"], 7, {"l": 3, "t": 0, "p": 0}, 3,
        {"sessional_ct": 20, "sessional_ta": 10, "sessional_total": 30, "ese_te_pe": 70, "total": 100},
        [OE_QUIRK], ["alternative_pair_row"]),
    row("Mini Project or Internship Assessment*", ["BPE752"], 7, {"l": 0, "t": 0, "p": 4}, 2,
        {"sessional_ct": None, "sessional_ta": None, "sessional_total": None, "ese_te_pe": 100, "total": 100},
        [PROJ_QUIRK + " (BPE752 row: 0-0-4, PS=100, Total=100, Credit=2; * the Mini Project or internship "
         "(5-6 weeks) conducted during summer break after VI semester and will be assessed during VII semester)"], []),
    row("Project-I", ["BPE753"], 7, {"l": 0, "t": 0, "p": 10}, 5,
        {"sessional_ct": None, "sessional_ta": None, "sessional_total": None, "ese_te_pe": 150, "total": 150},
        [PROJ_QUIRK + " (BPE753 row: 0-0-10, PS=150, Total=150, Credit=5)"], []),
    row("Startup and Entrepreneurial Activity Assessment#", ["BPE754"], 7, {"l": 0, "t": 0, "p": 4}, 2,
        {"sessional_ct": None, "sessional_ta": None, "sessional_total": None, "ese_te_pe": 100, "total": 100},
        [PROJ_QUIRK + " (BPE754 row: 0-0-4, PS=100, Total=100, Credit=2; # the Startup and Entrepreneurial "
         "Activity Assessment will be done in 7th semester — a startup/entrepreneurship activity of at "
         "least 60 hours till 6th semester)"], []),
    row("Open Elective-III", ["BOEP**"], 8, {"l": 3, "t": 0, "p": 0}, 3,
        {"sessional_ct": 20, "sessional_ta": 10, "sessional_total": 30, "ese_te_pe": 70, "total": 100},
        [OE_QUIRK], ["alternative_pair_row"]),
    row("Open Elective-IV", ["BOEP**"], 8, {"l": 3, "t": 0, "p": 0}, 3,
        {"sessional_ct": 20, "sessional_ta": 10, "sessional_total": 30, "ese_te_pe": 70, "total": 100},
        [OE_QUIRK], ["alternative_pair_row"]),
    row("Project-II", ["BPE851"], 8, {"l": 0, "t": 0, "p": 18}, 10,
        {"sessional_ct": 100, "sessional_ta": None, "sessional_total": None, "ese_te_pe": 350, "total": 450},
        [PROJ_QUIRK + " (BPE851 row prints '100 350 450': 100 sessional (CT column), 350 TE, 450 Total, "
         "Credit=10 — column alignment of the collapsed project print recorded verbatim)"], []),
]

BAD = ("extraction_failed_scheme_batch", "scheme_row_only_detailed_syllabus_not_printed")
kept, replaced = [], 0
for s in d["subjects"]:
    fl = s.get("flags") or []
    if any(b in fl for b in BAD) or s.get("name") == "verbatim":
        replaced += 1
        continue
    kept.append(s)
assert replaced == 8, f"expected 8 scheme rows to replace, found {replaced}"
d["subjects"] = kept + SCHEME_ROWS
d["flags"] = [f for f in d.get("flags", []) if not str(f).startswith("scheme_batch_failed")]
json.dump(d, open(P, "w"), indent=1, ensure_ascii=False)
print(f"replaced {replaced} scheme rows deterministically; draft now {len(d['subjects'])} subjects:")
for s in d["subjects"]:
    print(" ", s.get("name", "")[:44], "| codes:", s.get("codes"), "| units:", len(s.get("units") or {}))
