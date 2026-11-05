#!/usr/bin/env python3
"""b36_adjudicate_maths5.py — CRON-20261105-B36 adjudication for
10_btech_s3-4_kas304-404-maths-v_2019-20::00::mathematics-v (TIE code identity
across rows).

The draft (Mercury-3 extraction of the 3-page detailed print, verbatim 5 units
+ COs + books verified) prints 'Mathematics-V (B. Tech. Bio
Technology/Agriculture Engineering) (Effective from the Session: 2019-20),
Subject Code KAS304/KAS404' — ONE subject with a dual slot-code cell (BioTech
sem-III / Ag-Engg sem-IV offering of the same AICTE-model course).

Current Tier-0 owners (both 2019-20 scheme-row prints, units 0):
  - engineering-science-course-maths-v ('Engineering Science Course/ Maths V',
    primary KOE031-38 pool range) owns KAS304;
  - maths-v-engineering-science-course ('Maths V/Engineering Science Course',
    primary KAS404) owns KAS404.
Recorded resolution (B17 SLOT-CODE-TRANSFER + B31 08::00 soft-computing
convergence class, update-first): RETARGET the detailed print onto the
KAS404-primary slot row maths-v-engineering-science-course — it gains the
verbatim units/COs/books (backfill: the slot rows print none) and KAS304 joins
its codes (the transfer strips KAS304 from the pool-range row, which keeps its
KOE031-38 range print + narrative history per the recorded B08/B17 executor);
the draft name 'MATHEMATICS-V' and the dual-slot cell print are recorded as the
detailed print evidence. Zero-GAP: the detailed content lands on the same-course
slot row instead of a duplicate new row (update first > append second)."""
MD = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
MARK = "B36 (CRON-20261105-B36) maths-v KAS304/KAS404 dual-slot convergence"

src = open(MD).read()
if MARK in src:
    print("  (already injected)")
else:
    block = '''
# ---- B36 (CRON-20261105-B36) maths-v KAS304/KAS404 dual-slot convergence ----
TIER2_OVERRIDES.update({
    "10_btech_s3-4_kas304-404-maths-v_2019-20::00::mathematics-v": {
        "action": "RETARGET", "target": "maths-v-engineering-science-course",
        "reason": "B36 dual-slot convergence (recorded B17 SLOT-CODE-TRANSFER + B31 08::00 soft-computing class, update-first): the detailed 2019-20 print (B.Tech BioTechnology/Agriculture Engineering, subject code cell 'KAS304/KAS404' — ONE subject, BioTech sem-III / Ag-Engg sem-IV offering of the same AICTE-model course; verbatim 5 units + COs + books, Mercury-3 extraction containment-verified) TIEs at Tier-0 across the two scheme-row slot prints engineering-science-course-maths-v (KOE031-38 pool range; owns KAS304) and maths-v-engineering-science-course (primary KAS404). The KAS404-primary row is the convergence target: it gains the verbatim units/COs/books (both slot rows print none — backfill), KAS304 joins its codes via the recorded transfer (the pool-range row keeps its KOE031-38 range print + narrative history, G2-exempt), and the 'Mathematics-V' name + dual-slot cell print are recorded as the detailed print evidence (same-session 2019-20 detailed print fieldwise-fills empty fields; update first > append second — no duplicate row)."},
})
'''
    lines = src.split("\n")
    starts = [i for i, l in enumerate(lines) if l.startswith("TIER2_OVERRIDES.update({")]
    assert starts
    s = starts[-1]; depth = 0; e = None
    for i in range(s, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if depth == 0 and i > s:
            e = i; break
    assert e is not None
    lines.insert(e + 1, block)
    open(MD, "w").write("\n".join(lines))
    print("  injected after TIER2_OVERRIDES ending line", e + 1)
