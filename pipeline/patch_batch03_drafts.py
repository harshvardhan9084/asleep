#!/usr/bin/env python3
"""patch_batch03_drafts.py — B03 evidence-recorded draft patches (protocol
step 5: fix drafts with recorded reasoning; zero-guess; print evidence kept).

P1 (08, G3): the document prints TWO distinct mandatory internships — BP411I
    (Sem-IV scheme table) and BP612I (Sem-VI scheme table) — both headed
    "Internship (Mandatory)". (subject_name, course_name) must be unique
    (RULES §5 G3): disambiguate with the printed semester context of each
    scheme table; quirk records the print basis.
P2 (08, verify exemption): header-only / printed-blank / misprinted-detail
    subjects get the honest no-detail flags; evidence already in quirks.
P3 (10, verify exemption): training/report/project subjects print no unit
    detail (old-era BP format; evidence in quirks) → no_detailed flag.
P4 (10, brain clause): heading-vs-scheme code misprints — scheme table is the
    slot identity; misprinted heading code moves to the misprint narrative:
    BP408P(heading)/BP409P(scheme) for Pharmacognosy-I (Practical);
    P609P(heading)/BP609P(scheme) for Herbal Drug Technology (Practical).
P5 (03, verify exemption): BVA251 Sports and Yoga prints only a scheme row +
    "*Non-credit Course" footnote in the 2025-26 doc → no_detailed flag.
"""
import json, os

BASE = "/home/z/my-project/work/pipeline_v2/drafts"


def load(stem):
    return json.load(open(f"{BASE}/{stem}.draft.json"))


def save(stem, d):
    with open(f"{BASE}/{stem}.draft.json", "w") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def add_flag(s, flag):
    if flag not in (s.get("flags") or []):
        s.setdefault("flags", []).append(flag)


def add_quirk(s, q):
    if q not in (s.get("quirks") or []):
        s.setdefault("quirks", []).append(q)


def by_code(d, code):
    return [s for s in d["subjects"] if code in [c.split()[0] for c in (s.get("codes") or [])]]


# ---- 08 ----
d = load("08_bpharm_scheme-syllabus_2026-27")
n_changed = 0
for s in d["subjects"]:
    codes = [c.split()[0] for c in (s.get("codes") or [])]
    if "BP411I" in codes:
        s["name"] = "Internship (Mandatory) (Semester IV)"
        add_quirk(s, "[patch-P1] name qualified with printed semester context: the Sem-IV scheme table (pdf p.117-118) lists BP411I 'Internship (Mandatory)'; the heading itself prints only 'Internship (Mandatory)' - qualifier added to keep (name,course) unique under G3 (BP612I is the distinct Sem-VI internship)")
        add_flag(s, "header_only")
        add_quirk(s, "[patch-P2] no detail printed anywhere in the document: the scheme row prints 'Refer Section 22 of the ordinance' (print evidence recorded)")
        n_changed += 1
    elif "BP612I" in codes:
        s["name"] = "Internship (Mandatory) (Semester VI)"
        add_quirk(s, "[patch-P1] name qualified with printed semester context: the Sem-VI scheme table (pdf p.144) lists BP612I 'Internship (Mandatory)'; qualifier added to keep (name,course) unique under G3")
        add_flag(s, "header_only")
        add_quirk(s, "[patch-P2] no detail printed anywhere in the document: the scheme row prints 'Refer Section 22 of the ordinance' (print evidence recorded)")
        n_changed += 1
    elif "BP710RP" in codes:
        add_flag(s, "header_only")
        n_changed += 1
    elif "BP609P" in codes:
        add_flag(s, "no_practical_list_printed")
        n_changed += 1
    elif "BP611P" in codes and "Professional Skills" in s.get("name", ""):
        add_flag(s, "no_practical_list_printed")
        n_changed += 1
save("08_bpharm_scheme-syllabus_2026-27", d)
print(f"PATCH|08|changed={n_changed}")

# ---- 10 ----
d = load("10_bpharm_y1-4_syllabus_2019-20")
n_changed = 0
for s in d["subjects"]:
    codes = [c.upper() for c in (s.get("codes") or [])]
    nm = s.get("name", "").upper()
    if any(c in codes for c in ("BP111P", "BP509P", "BP610P", "BP706PS", "BP707P", "BP815PW", "BP816P")) and \
       any(t in nm for t in ("COMMUNIUCATION", "HOSPITAL TRAINING", "INDUSTRIAL TRAINING",
                             "PRACTICE SCHOOL", "PROJECT WORK", "INDUSTRIAL TOUR")):
        add_flag(s, "no_detailed_syllabus_printed")
        add_quirk(s, "[patch-P3] verifier exemption flag: the document prints no unit-level detail for this training/report subject (old-era BP format; print check recorded in existing quirks)")
        n_changed += 1
    elif "BP408P" in codes and "PHARMACOGNOSY" in nm:
        s["codes"] = ["BP409P"]
        add_quirk(s, "[patch-P4] primary code set to the scheme-table slot print BP409P ('Pharmacognosy I - Practical', Sem-IV scheme table, frag1 pdf p.5); the detail heading misprints 'BP408P.' (already owned by PHARMACOLOGY-I (Practical) whose scheme row and heading both print BP408P) - heading misprint recorded here; evidence: scheme table + both headings, brain clause")
        n_changed += 1
    elif "P609P" in codes:
        s["codes"] = ["BP609P"]
        add_quirk(s, "[patch-P4] primary code set to the scheme-table slot print BP609P ('Herbal Drug Technology - Practical', Sem-VI scheme table, frag1 pdf p.7); the detail heading misprints 'P609P.' (initial B missing, span-verified by the fragment subagent) - heading misprint recorded here; brain clause")
        n_changed += 1
save("10_bpharm_y1-4_syllabus_2019-20", d)
print(f"PATCH|10|changed={n_changed}")

# ---- 03 ----
d = load("03_bca_y1_syllabus_2025-26")
n_changed = 0
for s in d["subjects"]:
    if "BVA251" in [c.upper() for c in (s.get("codes") or [])]:
        add_flag(s, "no_detailed_syllabus_printed")
        add_quirk(s, "[patch-P5] verifier exemption flag: the 2025-26 doc prints only the scheme row 'BVA251 Sports and Yoga* 0 0 3 100 0' + '*Non-credit Course' footnote for this subject (BCA Ist Year scheme page, pdf p.3); no unit-level detail printed")
        n_changed += 1
save("03_bca_y1_syllabus_2025-26", d)
print(f"PATCH|03|changed={n_changed}")
