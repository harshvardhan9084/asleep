#!/usr/bin/env python3
"""patch_b21_alt_pair_flags.py — B21 draft patch: the 8 OR-slot scheme prints
that the ladder TIEs at Tier-0 (code identity across the two member rows) are
the recorded B02/B20 ALTERNATIVE-PAIR-SLOT class ("scheme alternative-slot
prints name subjects that BOTH already own rows — a slot is program structure,
not a subject; slot prints preserved verbatim in drafts' non_subject_rows").
The SKIP path requires the draft flag `alternative_pair_row` (B20 (f) class);
the subagents recorded `scheme_row_only` but not the pair flag — this patch
adds it with the printed evidence, per subject:

  04::35 Mathematics III/ Science based open Elective**  (EAS-301 + EOE-031-038)
  04::38 Science based Open Elective**/ Mathematics III  (EOE-041-048 + EAS-401)
  08::16 Science Based Open Elective/ Mathematics-III    (ROE030-039 + RAS301)
  08::17 Universal Human Values & Professional Ethics/ Environment & Ecology (RVE301 + RAS302)
  08::20 Mathematics-III/ Science Based Open Elective    (RAS401 + ROE040-049)
  08::21 Environment & Ecology/ Universal Human Values & Professional Ethics (RAS402 + RVE401)
  09::25 Sociology/Cyber Security                        (RAS502 + RUC501)
  09::27 Sociology/Cyber Security                        (RAS602 + RUC601)

Both members of every pair own published BTech rows (verified against the
B20-published CSV): mathematics-iii-partial-differential-equations-statistical-a
(BAS302, owns the EOE031-048 pool prints), mathematics-iii-science-based-open-
elective (RAS401;EAS-301), science-based-open-elective (ROE030-042),
science-based-open-elective-mathematics-iii (RAS301;EAS401),
universal-human-values-and-professional-ethics (BVE301...;RVE301;RVE401),
environment-ecology (EAS-105;RAS302;RAS402), cyber-security (BCC301...;RUC501;
RUC601), sociology-cyber-security (RAS502;RAS602). Zero-GAP holds: nothing is
lost by SKIP — the slot prints stay verbatim in the drafts' non_subject_rows
(the scheme tables) and the member rows are already first-class.
Idempotent.
"""
import json

PATCHES = [
    ("04_btech_ece_syllabus_2009-10", 35, "EAS-301 + EOE-031-038 pool",
     "mathematics-iii-partial-differential-equations-statistical-a; mathematics-iii-science-based-open-elective"),
    ("04_btech_ece_syllabus_2009-10", 38, "EOE-041-048 pool + EAS-401",
     "mathematics-iii-partial-differential-equations-statistical-a; science-based-open-elective-mathematics-iii"),
    ("08_btech_ece_y2_syllabus_2017-18", 16, "ROE030-039 pool + RAS301",
     "science-based-open-elective; science-based-open-elective-mathematics-iii"),
    ("08_btech_ece_y2_syllabus_2017-18", 17, "RVE301 + RAS302",
     "universal-human-values-and-professional-ethics; environment-ecology"),
    ("08_btech_ece_y2_syllabus_2017-18", 20, "RAS401 + ROE040-049 pool",
     "mathematics-iii-science-based-open-elective; science-based-open-elective"),
    ("08_btech_ece_y2_syllabus_2017-18", 21, "RAS402 + RVE401",
     "environment-ecology; universal-human-values-and-professional-ethics"),
    ("09_btech_ece_y3_syllabus_2018-19", 25, "RAS502 + RUC501",
     "sociology-cyber-security; cyber-security"),
    ("09_btech_ece_y3_syllabus_2018-19", 27, "RAS602 + RUC601",
     "sociology-cyber-security; cyber-security"),
]

n = 0
for stem, idx, codes, members in PATCHES:
    p = f"/home/z/my-project/work/pipeline_v2/drafts/{stem}.draft.json"
    d = json.load(open(p))
    s = d["subjects"][idx]
    fl = s.setdefault("flags", [])
    if "alternative_pair_row" not in fl:
        fl.append("alternative_pair_row")
        s.setdefault("quirks", []).append(
            f"Print-evidence class alternative_pair_row (B02/B20 ALTERNATIVE-PAIR-SLOT): the scheme row "
            f"prints an EITHER-OR slot ({codes}) naming two subjects that BOTH own published BTech rows "
            f"({members}) — a slot is program structure, not a subject (RULES §11); the slot print is "
            f"preserved verbatim in this draft's non_subject_rows (scheme tables).")
        n += 1
    json.dump(d, open(p, "w"), indent=1, ensure_ascii=False)
print(f"PATCHED|{n}")
