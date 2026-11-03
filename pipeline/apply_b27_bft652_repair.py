#!/usr/bin/env python3
"""apply_b27_bft652_repair.py — B27 post-commit code-ownership repair (RULES §4
brain clause: determine-then-fix, keep proof; recorded B21 REPAIRS class applied
post-commit per the b07_verify_fixes/apply_b04_fixnotes script pattern).

Evidence (print probes of btech_ft_s5-6_syllabus_2024-25.pdf, sha16 dc6eee55aae5dadc):
  - p.2 scheme table row: "BFT652 | DAIRY TECHNOLOGY LAB" (and "BFT651 | BAKERY
    TECHNOLOGY LAB" on the row above it);
  - p.41 detailed header: "SUBJECT CODE: KFT-652 | COURSE TITLE: DAIRY
    TECHNOLOGY LAB" (p.40: "SUBJECT CODE: KFT-651 | COURSE TITLE: BAKERY
    TECHNOLOGY LAB").
The B26-era ladder mis-assigned BOTH KFT-652 and BFT652 onto
bakery-technology-lab. The B27 commit already transferred KFT-652/KFT 652 to
dairy-technology-lab via the recorded CODE-REASSIGNED executor (the 2020-21
draft carries KFT-652, which fired the auto class); BFT652 was NOT in any
B27 draft's codes (the B-era twin print was only probed post-commit), so the
executor never saw it. This repair moves BFT652 with the same recorded
semantics: stripped from bakery-technology-lab (narrative retained in
code_history_all), added to dairy-technology-lab, change notes on both rows.
G2 single ownership restored for (BTech, BFT652). No other field is touched.
"""
import csv, re

CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
REF_HEADER = ["subject_id","row_kind","subject_name","subject_name_print","primary_code",
"all_codes","code_history_all","status","university_name","course_name","branch_names",
"program_year","semester_slots","effective_session_latest","first_introduced_session",
"subject_type","subject_category_print","L","T","P","credit","sessional_ct","sessional_ta",
"sessional_total","ese_te_pe","total_marks","evaluation_note","has_detailed_syllabus",
"prerequisites","co_count","co1_text","co2_text","co3_text","co4_text","co6_text","co5_text",
"co_kls","units_count","lectures_per_unit","unit1_text","unit2_text","unit3_text","unit4_text",
"unit5_text","textbooks_structured","reference_books_structured","experiments_structured",
"choice_group_id","choice_group_policy","eligibility_print","k_era_pool_codes","source_syllabus",
"source_scheme_line","source_history","change_note_vs_previous","notes","objectives_print"]

rows = list(csv.DictReader(open(CSV, newline="", encoding="utf-8")))
by_id = {r["subject_id"]: r for r in rows}

bak = by_id["bakery-technology-lab"]
dai = by_id["dairy-technology-lab"]

toks = [t.strip() for t in bak["all_codes"].split(";") if t.strip()]
assert "BFT652" in toks, f"BFT652 not on bakery-technology-lab: {bak['all_codes']}"
bak["all_codes"] = ";".join(t for t in toks if t != "BFT652")
seg_b = ("; BFT652 re-assigned by AKTU to DAIRY TECHNOLOGY LAB per the 2024-25 "
         "scheme print (btech_ft_s5-6_syllabus_2024-25.pdf#dc6eee55aae5dadc p.2 scheme row "
         "'BFT652 DAIRY TECHNOLOGY LAB' + p.41 detailed header 'SUBJECT CODE: KFT-652 / "
         "COURSE TITLE: DAIRY TECHNOLOGY LAB') — narrative mention retained "
         "(code-reassigned across sessions; owner directive 2026-10-28 §1b era model; "
         "B27 post-commit repair apply_b27_bft652_repair.py)")
bak["code_history_all"] = (bak.get("code_history_all", "") or "") + seg_b
bak["change_note_vs_previous"] = (bak.get("change_note_vs_previous", "") or "") + \
    "; BFT652 ownership transferred to dairy-technology-lab per the 2024-25 printed scheme row (B27 post-commit repair, RULES §4 keep-proof)"

dtoks = [t.strip() for t in dai["all_codes"].split(";") if t.strip()]
assert "BFT652" not in dtoks
dai["all_codes"] = ";".join(dtoks + ["BFT652"])
dai["change_note_vs_previous"] = (dai.get("change_note_vs_previous", "") or "") + \
    "; BFT652 ownership recorded per the 2024-25 print (p.2 scheme row 'BFT652 DAIRY TECHNOLOGY LAB'; the KFT-652 twin was already transferred by the B27 CODE-REASSIGNED executor) — B27 post-commit repair"

with open(CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=REF_HEADER, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in REF_HEADER})

# gate re-check (G2 semantics, BTech scope)
def norm_code(c): return re.sub(r"[^A-Z0-9]", "", c.upper())
def exact_code(t): return bool(re.fullmatch(r"[A-Z]{2,4}\d{3}[A-Z]?", t))
own, dups = {}, []
for r in rows:
    toks = set()
    for f in ("primary_code", "all_codes"):
        for c in (r.get(f, "") or "").split(";"):
            c = norm_code(c)
            if exact_code(c):
                toks.add(c)
    for t in toks:
        k = (r["course_name"], t)
        if k in own and own[k] != r["subject_id"]:
            dups.append((k, own[k], r["subject_id"]))
        own[k] = r["subject_id"]
print(f"REPAIR OK | G2-semantics codes={len({t for _, t in own})} dups={len(dups)}")
print(f"  bakery-technology-lab all_codes = {bak['all_codes']}")
print(f"  dairy-technology-lab   all_codes = {dai['all_codes']}")
