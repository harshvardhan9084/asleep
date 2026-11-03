#!/usr/bin/env python3
"""patch_bva251_units.py — B03 verify remedy (RULES §6/§7, zero-guess).

Both BCA y1 docs print BVA251 Sports and Yoga with a "Syllabus/Guidelines"
divided into "Part A: Sports/Games" and "Part B: Yoga" — there are NO
"Unit-I..V" headings for this non-credit subject. Draft-01 keyed these as
"Part A"/"Part B" (would never map to unit1/unit2 fields at merge);
draft-02 left units empty (verifier FAIL 'no units').

Fix: key the verbatim Part A / Part B prints as units "1"/"2" with the printed
headings kept verbatim in the text (same remedy class as B02's printed
structure mapping; content unchanged — only the dict keys move/land).
"""
import json

D1 = "/home/z/my-project/work/pipeline_v2/drafts/01_bca_y1_syllabus_2024-25.draft.json"
D2 = "/home/z/my-project/work/pipeline_v2/drafts/02_bca_y1_syllabus_2025-26.draft.json"

PART_B_YOGA_1 = """Part B: Yoga
a. Introduction of Yoga
Introduction of Yoga, Origin of Yoga, Aims and Objective of Yoga, Patanjali Yoga darshan, Hath yoga, Gheranda Samhita, Karm yoga, Gyan yoga.
b. Asanas, Pranayam and Meditation Practices
Meaning of Asanas, Objective of Asanas, rules and regulations of Asanas and Pranayams, Types of Yogasana.
Yogic postures: Standing Posture, Sitting posture, Supine posture, Prone posture, balancing Postures, Pranayam according to Patanjali and Hath Yoga, Meditaion Mudras.
c. Science of Yoga
Physiological effects of Asanas- Paranayama and meditation,stress management and yoga, Mental health and yoga practice, Health and Personality Development."""

PART_B_YOGA_2 = """Part B: Yoga
a. Introduction of Yoga
Introduction of Yoga, Origin of Yoga, Aims and Objective of Yoga, Patanjali Yoga darshan, Hath yoga, Gheranda Samhita, Karm yoga, Gyan yoga.
b. Asanas, Pranayam and Meditation Practices
Meaning of Asanas, Objective of Asanas, rules and regulations of Asanas and Pranayams, Types of Yogasana.
Yogic postures: Standing Posture, Sitting posture, Supine posture, Prone posture, balancing Postures, Pranayam according to Patanjali and Hath Yoga, Meditaion Mudras.
c. Science of Yoga
 Physiological effects of Asanas- Paranayama and meditation,stress management and    
 yoga, Mental health and yoga practice, Health and Personality Development."""


def fix(path, part_a_text, part_b_text, from_keys):
    j = json.load(open(path))
    hit = 0
    for s in j["subjects"]:
        if s.get("codes") and "BVA251" in [c.replace(" ", "") for c in s["codes"]]:
            u = s.get("units") or {}
            a = u.get(from_keys[0]) or u.get("1")
            b = u.get(from_keys[1]) or u.get("2")
            if from_keys == ("Part A", "Part B"):
                s["units"] = {"1": a, "2": b}
            else:
                s["units"] = {"1": part_a_text, "2": part_b_text}
            s.setdefault("quirks", []).append(
                "printed structure is 'Syllabus/Guidelines' with Part A: Sports/Games and Part B: Yoga "
                "(no Unit-I..V headings printed for this non-credit subject); recorded as units 1/2 with "
                "verbatim Part headings (B03 verify remedy)")
            hit += 1
    json.dump(j, open(path, "w"), indent=1, ensure_ascii=False)
    print(f"PATCHED|{path.split('/')[-1]}|subjects={hit}")


d1 = json.load(open(D1))
for s in d1["subjects"]:
    if s.get("codes") and "BVA251" in [c.replace(" ", "") for c in s["codes"]]:
        print("d1 units keys:", list((s.get("units") or {}).keys()))
        pa = s["units"].get("Part A", "")
        print("d1 Part A head:", pa[:80].replace("\n", " / "))

fix(D1, None, None, ("Part A", "Part B"))
fix(D2, None, PART_B_YOGA_2, ("", ""))  # draft-02: build part A from fulltext below
# draft-02 Part A must come from its own fulltext verbatim
j2 = json.load(open(D2))
ft = open("/home/z/my-project/work/pipeline_v2/parsed/02_bca_y1_syllabus_2025-26.fulltext.txt").read()
i = ft.find("Part A: Sports/Games")
k = ft.find("Part B: Yoga")
part_a2 = " ".join(ft[i:k].split())
pa2 = "\n".join(l.strip() for l in ft[i:k].splitlines() if l.strip())
for s in j2["subjects"]:
    if s.get("codes") and "BVA251" in [c.replace(" ", "") for c in s["codes"]]:
        s["units"]["1"] = pa2
json.dump(j2, open(D2, "w"), indent=1, ensure_ascii=False)
print("d2 Part A head:", pa2[:80].replace("\n", " / "))
print("PATCH-DONE")
