#!/usr/bin/env python3
"""patch_b26_alt_pair.py — flag the B26 combined ALTERNATIVE-SLOT prints.

12 draft subjects print the AICTE/R-era scheme's slash-combined alternative
slots ("A / B" = take either); both named members already own registry rows
(recorded ALTERNATIVE-PAIR-SLOT class, B22/B23/B25 manifests + RESOLVE_APPEND):
the slot print is program structure, not a subject (RULES §11) — the verifier
flag alternative_pair_row triggers the recorded auto-SKIP at merge (members
keep their rows; the verbatim slot print stays in the draft's non_subject_rows
scheme tables). Evidence per subject: printed slash in the name + both member
codes printed on the row.
"""
import json

D = "/home/z/my-project/work/pipeline_v2/drafts/B26"
PATCHES = {
    "02_btech_env_y4_syllabus_2021-22": [
        ("HSMC-1#/HSMC-2# [Annexure-B(iii)]",
         "members: rural-development-administration-and-planning (KHU701) + "
         "project-management-entrepreneurship (KHU702); both own rows (B17 class)"),
        ("HSMC‐2#/HSMC‐1# [Annexure‐B(iii)]",
         "members: project-management-entrepreneurship (KHU802) + "
         "rural-development-administration-and-planning (KHU801); both own rows (B17 class)"),
    ],
    "08_btech_ft_syllabus_2018-19": [
        ("SOCIOLOGY / CYBER SECURITY",
         "members: sociology (HSMC elective) + cyber-security rows; the RAS502/RUC501 "
         "slot row sociology-cyber-security already carries the printed slot codes (B25 class)"),
        ("CYBER SECURITY/ SOCIOLOGY",
         "members: cyber-security + sociology rows; RAS602/RUC601 slot print (B25 class)"),
    ],
    "09_btech_ft_y2_model-curriculum_2019-20": [
        ("Engineering Science Course/Maths IV",
         "members: maths-iv (BAS303) + engineering-science pool (KOE031-38); AICTE-model either/or slot"),
        ("Technical Communication/Universal Human values",
         "members: technical-communication (KAS301-era) + universal-human-values rows; either/or slot"),
        ("Computer System Security/Python Programming",
         "members: computer-system-security (KNC301) + python-programming (KNC302) rows; either/or slot"),
        ("Maths IV/Engineering Science Course",
         "members: maths-iv + engineering-science pool (KOE041-48); either/or slot"),
        ("Universal Human Values/ Technical Communication",
         "members: universal-human-values + technical-communication rows; either/or slot"),
        ("Python Programming/ Computer System Security",
         "members: python-programming (KNC402) + computer-system-security (KNC401) rows; either/or slot"),
    ],
    "10_btech_ft_y2_scheme-syllabus_2017-18": [
        ("Universal Human Values & Professional Ethics/ Environment & Ecology",
         "members: universal-human-values-and-professional-ethics (RVE301) + environment-ecology (RAS302) rows"),
        ("Environment & Ecology/ Universal Human Values & Professional Ethics",
         "members: environment-ecology (RAS402) + universal-human-values-and-professional-ethics (RVE401) rows"),
    ],
}
FL = "alternative_pair_row"
n = 0
for stem, items in PATCHES.items():
    p = f"{D}/{stem}.draft.json"
    d = json.load(open(p))
    for name, ev in items:
        hits = [s for s in d["subjects"] if s.get("name", "").strip() == name]
        if len(hits) != 1:
            print(f"WARN|{stem}|{name!r}|hits={len(hits)}")
            continue
        s = hits[0]
        if FL not in (s.get("flags") or []):
            s.setdefault("flags", []).append(FL)
            s.setdefault("quirks", []).append(
                "Combined alternative-slot print (either/or, recorded ALTERNATIVE-PAIR-SLOT "
                "class B22/B23/B25): " + ev + " — patch-b26-alt-pair")
            n += 1
    with open(p, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
print(f"PATCHED|{n}")
