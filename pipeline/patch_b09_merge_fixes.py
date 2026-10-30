#!/usr/bin/env python3
"""patch_b09_merge_fixes.py — B09 pre-merge draft surgery (evidence-recorded,
B08 patch_b08_collisions.py precedent: verbatim evidence moves to quirks).

doc02::06 'Project' (2025-26 AI-ML y4): the print is the university-wide JOINT
section 'BCS753/ BCS851    Project' (one CO table, spans Sem VII+VIII). Within
BTech each printed code is ALREADY owned by its slot row per the B08 ingestion
of the identical AI&DS 2025-26 joint print:
    BCS753 -> project-1 (sem-7 slot; CO content ingested 2025-26, verified
             byte-identical to this draft's CO table)
    BCS851 -> project-ii (sem-8 slot; notes record the same joint section)
The draft's Tier-0 code-identity therefore hits BOTH rows (TIE). Resolving via
RETARGET would double-own BCS851 (G2 course-scoped violation). Remedy: strip
'BCS851' from the draft subject's codes so Tier-0 resolves UNIQUELY to
project-1 (the slot whose detailed content this print corroborates — verified
byte-identical COs); the print evidence for BCS851 stays verbatim in the
subject's quirks/flags. project-ii is not touched; no code ownership changes.
"""
import json, os, sys

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
STEM = "02_btech_ai-ml_y4_syllabus_2025-26"
KEY = "02_btech_ai-ml_y4_syllabus_2025-26::06::project"


def main():
    p = os.path.join(DRAFTS, STEM + ".draft.json")
    d = json.load(open(p))
    hit = 0
    for s in d["subjects"]:
        if s.get("name") == "Project" and "BCS851" in (s.get("codes") or []):
            s["codes"] = [c for c in s["codes"] if c != "BCS851"]
            s.setdefault("flags", []).append(
                "joint-print-bcs851-stripped-slot-row-already-owns")
            s.setdefault("quirks", []).append(
                "B09 pre-merge adjudication (patch_b09_merge_fixes.py): the printed joint heading "
                "'BCS753/ BCS851    Project' (one CO table, spans Sem VII+VIII) carries BCS851; "
                "BCS851 is already owned by the sem-VIII slot row project-ii per the B08 ingestion "
                "of the identical AI&DS 2025-26 joint print (both prints' CO tables verified "
                "byte-identical); BCS851 stripped from this draft subject's codes so Tier-0 "
                "resolves uniquely to project-1 — double ownership would violate G2 (course-"
                "scoped, RULES §5); the joint print remains recorded here verbatim.")
            hit += 1
    if hit != 1:
        print(f"UNEXPECTED|hits={hit}"); return 1
    with open(p, "w") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print(f"doc02::06 Project codes stripped to {s['codes']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
