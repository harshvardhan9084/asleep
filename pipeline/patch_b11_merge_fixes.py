#!/usr/bin/env python3
"""patch_b11_merge_fixes.py — CRON-20261031-B11 merge-time draft fixes
(B09 02::06 strip precedent: 'BCS851 stripped from the draft subject — its
slot row already owns it; print evidence verbatim in quirks').

doc04 (btech_bt_syllabus-aicte_2018-19, AICTE model curriculum, sha16
7ddb3baa8918a1d1) prints FOLDED scheme rows: the practical subjects carry the
THEORY subject's code because the scheme table prints one code cell covering
both (the doc's own quirks: 'no separate lab code printed; code KAS201
inherited from the Sem-II Physics/Chemistry scheme row (printed KAS201/
KAS201)'). The live commit's pre-adjudicated CODE-REASSIGNED-ACROSS-SESSIONS
handler would TRANSFER those parent codes off the theory rows onto the lab
rows (B3 BBC102 model) — but that model is for genuine NEWEST-print slot
reassignments, NOT for same-session folded prints: the published AKTU scheme
(registry @579d476) owns KAS101;KAS201→physics, KAS102;KAS202→chemistry,
KEE101;KEE201→basic-electrical-engineering, KCS101;KCS201→programming-for-
problem-solving, and the modern lab codes are DISTINCT (KCS-151P;KCS-251P,
KEE-151P;KEE-251P, KAS-152P;KAS-252P families already on the lab rows).
Zero-guess (RULES §4): the published mapping stays; the inherited parent
codes are STRIPPED from the 7 lab drafts (01,03,07,09,13,19,21) and from the
two 'KAS201/ KAS201' collision drafts (14,15); every strip is recorded in a
per-subject quirk citing the evidence; the verbatim prints remain in the
drafts' scheme non_subject_rows. The lab subjects then resolve by NAME to
their existing era-family rows (physics-lab, chemistry-practical,
programming-for-problem-solving-lab; the BEE Laboratory drafts RETARGET to
baisc-electrical-engineering-laboratory via TIER2_OVERRIDES).

Idempotent: strips only when the exact expected code set matches.
"""
import json, os, sys

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
STEM = "04_btech_bt_syllabus-aicte_2018-19"

# subject index -> (expected codes, theory-owner note, code to strip)
STRIPS = {
    1:  (["KAS101"], "physics=KAS101;KAS201"),
    3:  (["KAS102"], "chemistry=KAS102;KAS202"),
    7:  (["KEE101"], "basic-electrical-engineering=KEE101;KEE201"),
    9:  (["KCS101"], "programming-for-problem-solving=KCS101;KCS201"),
    13: (["KAS201"], "physics=KAS101;KAS201"),
    19: (["KEE201"], "basic-electrical-engineering=KEE101;KEE201"),
    21: (["KCS201"], "programming-for-problem-solving=KCS101;KCS201"),
    14: (["KAS201"], "physics=KAS101;KAS201 (the Sem-II 'KAS201/ KAS201 Physics/Chemistry' cell is a duplicated same-session print)"),
    15: (["KAS201"], "physics=KAS101;KAS201 (the Sem-II 'KAS201/ KAS201 Physics/Chemistry' cell is a duplicated same-session print)"),
}


def main():
    path = os.path.join(DRAFTS, f"{STEM}.draft.json")
    d = json.load(open(path))
    n = 0
    for idx, (expected, owner_note) in STRIPS.items():
        s = d["subjects"][idx]
        if s.get("codes") != expected:
            if not s.get("codes"):
                continue  # already stripped (idempotent re-run)
            raise SystemExit(f"ABORT: subject {idx} codes {s.get('codes')} != expected {expected}")
        s["codes"] = []
        q = ("merge adjudication (B11): the scheme row folds this subject under a "
             f"theory/inherited code cell, so the draft carries no code of its own — "
             f"the printed parent code is stripped at merge per the recorded B09 02::06 "
             f"strip precedent; the published AKTU scheme owns it for the theory subject "
             f"(registry @579d476: {owner_note}); modern lab codes are distinct "
             f"(KCS-151P/KEE-151P/KAS-252P families); verbatim print stays in the draft's "
             f"scheme non_subject_rows.")
        qs = s.get("quirks") or []
        if not any(x.startswith("merge adjudication (B11)") for x in qs):
            qs.append(q)
            s["quirks"] = qs
            n += 1
    with open(path, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    print(f"PATCHED|{STEM}|strips+quirks={n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
