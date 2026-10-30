#!/usr/bin/env python3
"""patch_b08_collisions.py — B08 pre-merge adjudication of the 2016-17 AG y4
document-level code collision (B06 repair_baseline_g2g3.py precedent: baseline
repairs happen BEFORE the merge commit, with evidence recorded).

EVIDENCE (fulltext of 02_btech_ag_y4_syllabus_2016-17, verified 2026-10-30):
The document prints NAG codes in TWO unreliable layers plus one reliable one:
  - DETAIL pages (subject pages carrying Unit/CO/book content) are AUTHORITATIVE:
      OE-I  details: NAG-011 Plastic Applications, NAG-012 Precision Agriculture
            and System Management, NAG-013 Food Quality & Control   (p.3)
      OE-II details: NAG-021 Design of Agricultural Machinery, NAG-022 Micro
            Irrigation Systems Design, NAG-023 Seed Process Engg   (pp.3-4)
      DE-III details: NAG-031 Testing of Agricultural Machinery and Tractor,
            NAG-032 Groundwater Wells and Pumps Engg, NAG-033 Food Packaging
            Technology   (p.8)
      DE-IV details: NAG-071 Post-Harvest Engineering..., NAG-042 Agricultural
            Structures & Environmental Control (p.16), NAG-043 Wasteland
            Development
      DE-V  details: NAG-081 Renewable Energy Sources, NAG-082 Crop Process
            Engg, NAG-083 Tractor Design Principle
  - POOL LISTS (OE/DE member lists) REUSE codes across pools: OE-1 list prints
    NAG-031/032/033 for the OE-I subjects (= the DE-III detail segment); OE-2
    list prints NAG-041/042/043 (= DE-IV segment); DE-III list prints
    NAG-051/052/053; DE-IV list reprints NAG-041/042/043 for DIFFERENT subjects
    (Post-Harvest/AgriStructures/Wasteland); DE-V list prints NAG-051/052/053
    for DIFFERENT subjects (Renewable/CropProcess/TractorDesign).
  - CROSS-SESSION REUSE: NAG-011/012/013/021/022/023 are ALREADY OWNED by the
    2015-16 y3 sem-6 rows (watershed-planning-and-management,
    food-processing-plant-design-layout, land-development-machinery,
    minor-irrigation-and-command-area-development,
    development-of-processed-products-and-equipments,
    production-technology-and-agricultural-machineries) — the 2016-17 y4
    document reprints the SAME tokens on its detail pages for DIFFERENT
    subjects (document-level code reuse across sessions, the recorded
    CODE-REASSIGNED-ACROSS-SESSIONS class).

ACTIONS (recorded per RULES §4 brain clause — evidence conclusive per layer):
  1. DRAFTS: strip pool-list prints from the 13 collision subjects' codes,
     keep the detail-page print (authoritative). The stripped tokens move to
     subject quirks verbatim (never silently dropped).
  2. CSV BASELINE: move the 5 reused tokens (NAG-011/012/021/022/023 — NOT
     NAG-013, which the ladder's CODE-REASSIGNED name-transfer adjudicates
     live via the food-quality-control name-identity row) OUT of the 2015-16
     rows' ownership (primary_code/all_codes), into code_history narratives.
     watershed (keeps RAG072) and minor-irrigation (keeps RAG080) stay coded;
     the other three rows become codeless identity rows (G3: empty primary is
     skipped; notes flag needs_review for the owner).
  3. The 2016-17 detail-code rows then append cleanly via TIER2_OVERRIDES /
     natural T3 (see merge_draft.py B08 adjudications).

Idempotent: guarded by marker strings.
"""
import csv, json, os, shutil, sys
from datetime import datetime

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
BASE = "/home/z/my-project/work/pipeline_v2"
MARK = "PATCH-B08-COLLISION"

STEM02 = "02_btech_ag_y4_syllabus_2016-17"
# idx -> (new codes, stripped tokens, evidence note)
CODE_FIX = {
    0:  (["NAG-011"], ["NAG-031"], "detail p.3 prints NAG-011 for Plastic Applications in Agriculture; the OE-1 pool list (p.7) prints NAG-031 for it, but NAG-031 is the DE-III DETAIL print of Testing of Agricultural Machinery and Tractor (p.8) — pool-list print is the unreliable layer"),
    1:  (["NAG-012"], ["NAG-032"], "detail p.3 prints NAG-012 for Precision Agriculture and System Management; the OE-1 pool list prints NAG-032 for it, but NAG-032 is the DE-III detail print of Groundwater Wells and Pumps Engg (p.8)"),
    2:  (["NAG-013"], ["NAG-033"], "detail p.3 prints NAG-013 for Food Quality & Control; the OE-1 pool list prints NAG-033 for it, but NAG-033 is the DE-III detail print of Food Packaging Technology (p.8)"),
    3:  (["NAG-021"], ["NAG-041"], "detail pp.3-4 print NAG-021 for Design of Agricultural Machinery; the OE-2 pool list prints NAG-041 for it, but NAG-041 is reprinted by the DE-IV pool list for Post-Harvest Engineering (whose own detail print is NAG-071)"),
    4:  (["NAG-022"], ["NAG-042"], "detail p.3 prints NAG-022 for Micro Irrigation Systems Design; the OE-2 pool list prints NAG-042 for it, but NAG-042 is the DE-IV detail print of Agricultural Structures & Environmental Control (p.16)"),
    5:  (["NAG-023"], ["NAG-043"], "detail p.4 prints NAG-023 for Seed Process Engg; the OE-2 pool list prints NAG-043 for it, but NAG-043 is the DE-IV detail print of Wasteland Development"),
    8:  (["NAG-031"], ["NAG-051"], "DE-III detail p.8 prints NAG-031 for Testing of Agricultural Machinery and Tractor; the DE-III pool list prints NAG-051 for it, but NAG-051 is reprinted by the DE-V pool list for Renewable Energy Sources (whose own detail print is NAG-081)"),
    9:  (["NAG-032"], ["NAG-052"], "DE-III detail p.8 prints NAG-032 for Groundwater, Wells and Pumps Engg; the DE-III pool list prints NAG-052 for it, but NAG-052 is reprinted by the DE-V pool list for Crop Process Engg (detail NAG-082)"),
    10: (["NAG-033"], ["NAG-053"], "DE-III detail p.8 prints NAG-033 for Food Packaging Technology; the DE-III pool list prints NAG-053 for it, but NAG-053 is reprinted by the DE-V pool list for Tractor Design Principle (detail NAG-083)"),
    15: (["NAG-071"], ["NAG-041"], "DE-IV detail prints NAG-071 for Post-Harvest Engineering of Horticultural, Medicinal and Aromatic Crops; the DE-IV pool list prints NAG-041 for it, but NAG-041 is also the OE-2 pool print of Design of Agricultural Machinery (detail NAG-021)"),
    18: (["NAG-081"], ["NAG-051"], "DE-V detail prints NAG-081 for Renewable Energy Sources (draft prints the typo 'Renewal'); the DE-V pool list prints NAG-051 for it, but NAG-051 is also the DE-III pool print of Testing of Agricultural Machinery and Tractor (detail NAG-031)"),
    19: (["NAG-082"], ["NAG-052"], "DE-V detail prints NAG-082 for Crop Process Engg; the DE-V pool list prints NAG-052 for it, but NAG-052 is also the DE-III pool print of Groundwater Wells and Pumps Engg (detail NAG-032)"),
    20: (["NAG-083"], ["NAG-053"], "DE-V detail prints NAG-083 for Tractor Design Principle; the DE-V pool list prints NAG-053 for it, but NAG-053 is also the DE-III pool print of Food Packaging Technology (detail NAG-033)"),
}
# 2015-16 rows losing the reused tokens (row_id -> remaining primary/all)
BASELINE_MOVE = {
    "watershed-planning-and-management": ("RAG072", "RAG072", "NAG-011"),
    "minor-irrigation-and-command-area-development": ("RAG080", "RAG080", "NAG-021"),
    "food-processing-plant-design-layout": ("", "", "NAG-012"),
    "development-of-processed-products-and-equipments": ("", "", "NAG-022"),
    "production-technology-and-agricultural-machineries": ("", "", "NAG-023"),
}


def fix_drafts():
    path = os.path.join(DRAFTS, f"{STEM02}.draft.json")
    d = json.load(open(path))
    n = 0
    for i, s in enumerate(d.get("subjects", [])):
        if i not in CODE_FIX:
            continue
        codes, stripped, ev = CODE_FIX[i]
        if any(MARK in str(q) for q in (s.get("quirks") or [])):
            continue
        old = s.get("codes", [])
        s["codes"] = codes
        s.setdefault("quirks", []).append(f"{MARK}: pool-list prints {';'.join(stripped)} stripped from codes. {ev}. Printed evidence kept verbatim here per RULES §6.")
        s.setdefault("flags", []).append("code_collision_in_document_pool_list_stripped")
        n += 1
    json.dump(d, open(path, "w"), indent=1, ensure_ascii=False)
    print(f"DRAFTS|{STEM02}|codes fixed on {n} subjects")


def fix_baseline():
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    bkp = f"{BASE}/backup/pre_baseline_patch_{ts.replace(':', '').replace('+', 'p')}.csv"
    shutil.copy(CSV_PATH, bkp)
    with open(CSV_PATH) as f:
        rdr = csv.DictReader(f)
        header = rdr.fieldnames
        rows = list(rdr)
    n = 0
    for r in rows:
        rid = r.get("subject_id", "")
        if rid in BASELINE_MOVE and MARK not in (r.get("notes") or ""):
            new_primary, new_all, token = BASELINE_MOVE[rid]
            r["primary_code"] = new_primary
            r["all_codes"] = new_all
            narr = (f"{token} (2015-16, sem-6 print) — token REPRINTED by the 2016-17 y4 "
                    f"document on its detail pages for a different subject (document-level "
                    f"code reuse across sessions); ownership moved to the newer print per "
                    f"CODE-REASSIGNED-ACROSS-SESSIONS semantics; the newer subject row is "
                    f"appended by B08 (CRON-20261030-B08).")
            r["code_history_all"] = ((r.get("code_history_all", "") + "; " if r.get("code_history_all") else "") + narr)
            r["change_note_vs_previous"] = ((r.get("change_note_vs_previous", "") + "; " if r.get("change_note_vs_previous") else "") +
                                            f"{MARK}: {token} ownership moved to the 2016-17 reprint row (evidence: 02_btech_ag_y4_syllabus_2016-17 detail pages; backup {os.path.basename(bkp)})")
            note_add = f"{MARK}: ownership token {token} moved to the newer-session reprint row; this row keeps its name/history identity" + \
                       ("" if new_primary else "; NOW CODELESS (printed token reused by the newer document) — needs_review")
            r["notes"] = ((r.get("notes", "") + " | " if r.get("notes") else "") + note_add)
            n += 1
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in header})
    print(f"BASELINE|{n} rows patched|backup={bkp}")


def main():
    fix_drafts()
    fix_baseline()
    return 0


if __name__ == "__main__":
    sys.exit(main())
