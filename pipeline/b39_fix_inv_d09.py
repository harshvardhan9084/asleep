#!/usr/bin/env python3
"""b39_fix_inv_d09.py — correct 09_btech_y3-4_syllabus_2010-11.inv.json.

The deterministic scanner anchored every elective's detail to p.11 (the
printed 'List of Electives for B.Tech (Information Technology)' page). The
REAL detail sections were located deterministically by line-start
CODE+name occurrence scan (each elective code appears at its list page AND
at its detail page; the LAST occurrence is the detail section). Scheme-page
entries (p.2-10 audit/lab/GP/EOE-slot rows) have no detail in this doc.
EOE-071/074 & EOE-081/084 are printed slot ranges ('EOE-071 to EOE-074').
"""
import json, re

STEM = "09_btech_y3-4_syllabus_2010-11"
P = f"/home/z/my-project/work/pipeline_v2/inv/{STEM}.inv.json"
inv = json.load(open(P))
old = {re.sub(r"[^A-Z0-9]", "", e["code_print"].split("/")[0]): e for e in inv}

# detail codes -> real detail page (last line-start occurrence; scan verified)
DETAIL_PG = {
    "ECS501": 12, "ECS502": 13, "ECS503": 14, "ECS504": 15, "ECS505": 16,
    "EIT501": 17, "EIT505": 17, "ECS601": 19, "ECS602": 19, "ECS603": 21,
    "ECS604": 22, "EIT601": 22, "EIT602": 23, "ECS701": 24, "ECS702": 25,
    "EIT701": 26, "ECS801": 28,
    "EIT061": 29, "EIT062": 30, "EIT063": 31, "ECS071": 31, "ECS072": 32,
    "ECS073": 33, "ECS074": 34, "ECS075": 34, "ECS076": 36, "ECS077": 36,
    "EIT071": 37, "EIT072": 38, "EIT073": 39, "EIT074": 41, "ECS081": 42,
    "ECS082": 43, "ECS083": 44, "ECS084": 45, "ECS085": 46, "ECS086": 47,
    "ECS087": 47, "ECS088": 48, "EIT081": 49, "EIT082": 50,
}
NAME_OVERRIDE = {"EIT505": "Information Security and Cyber Laws"}

out = []
for code, pg in DETAIL_PG.items():
    e = old.get(code, {})
    out.append({"class": "detail", "code_print": e.get("code_print", code),
                "name_print": NAME_OVERRIDE.get(code, e.get("name_print", "")),
                "page": pg})
# scheme-only rows: everything else, verbatim from the old inv
for ncode, e in old.items():
    if ncode in DETAIL_PG:
        continue
    s = {"class": "scheme_only", "code_print": e.get("code_print", ncode),
         "name_print": e.get("name_print", ""), "page": e.get("page", 0)}
    if ncode in ("EOE071", "EOE081"):
        s["slot_print"] = True
        s["name_print"] = "Open Elective-I (printed slot: EOE-071 to EOE-074)" if ncode == "EOE071" else "Open Elective-II (printed slot: EOE-081 to EOE-084)"
    if ncode in ("EOE074", "EOE084"):
        continue  # same printed slot range; one slot row each (dedupe)
    out.append(s)

json.dump(out, open(P, "w"), indent=1, ensure_ascii=False)
det = sum(1 for x in out if x["class"] == "detail")
print(f"doc09 inv fixed: {len(out)} entries (detail {det}, scheme_only {len(out)-det})")
