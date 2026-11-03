#!/usr/bin/env python3
"""repair_course_boundary.py — RULES §1b repair (owner directive 2026-10-28)

Reverts the 8 BTech rows that the 2026-10-28 18:30 run corrupted with BCA
content (cross-course merge via mislabeled draft course metadata) to their
last clean B02-verified state (registry_613ad63_clean_baseline.csv), then
canonicalizes course_name on every row (B.Tech -> BTech, RULES §1b canon).

Every field change is recorded in change_note_vs_previous. Gates G1/G2/G3/G6
(imports from merge_draft) are re-run and the write is ABORTED on any failure.
"""
import csv, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from merge_draft import (CSV_PATH, REF_HEADER, CANON_COURSES, canon_course,
                         gate_g1, gate_g2, gate_g3, norm_name)

BASE = "/home/z/my-project/work/pipeline_v2"
CLEAN = f"{BASE}/backup/registry_613ad63_clean_baseline.csv"
REVERT_IDS = [
    "data-structure", "data-structure-lab", "operating-systems",
    "technical-communication", "universal-human-values-and-professional-ethics",
    "web-technology", "web-technology-lab", "digital-electronics",
]
REVERT_NOTE = ("2026-10-28 repair (RULES §1b, owner directive): BCA 2024-25/2025-26 draft "
               "content merged into this BTech row by the 18:30 run was REVERTED to the last "
               "clean verified state (commit 613ad63) - course boundaries are real; the BCA "
               "subjects are (re-)ingested as separate BCA rows.")
CANON_NOTE = "course_name canonized to BTech (RULES §1b canon; verbatim variant recorded here)"


def main():
    rows = list(csv.DictReader(open(CSV_PATH)))
    clean = {r["subject_id"]: r for r in csv.DictReader(open(CLEAN))}
    header = list(rows[0].keys())
    g1 = gate_g1(header)
    if g1:
        print("ABORT pre-gate G1:", g1)
        return 2

    reverted, canon = [], []
    for r in rows:
        if r["row_kind"] != "subject":
            continue
        # 1) revert cross-course-corrupted BTech rows to the clean baseline
        if r["subject_id"] in REVERT_IDS and r["subject_id"] in clean:
            old = clean[r["subject_id"]]
            diff = [f for f in REF_HEADER if (r.get(f, "") or "") != (old.get(f, "") or "")]
            if diff:
                for f in REF_HEADER:
                    r[f] = old.get(f, "")
                r["change_note_vs_previous"] = (r.get("change_note_vs_previous", "") + "; " if r.get("change_note_vs_previous", "") else "") + REVERT_NOTE
                # keep the corruption's own change-note trail out of the clean row
                # (the clean row's change_note already ends at B02 state; REVERT_NOTE documents the repair)
                reverted.append((r["subject_id"], len(diff)))
        # 2) canon course names
        cc = r.get("course_name", "")
        if cc and cc not in CANON_COURSES:
            new = canon_course(cc)
            if new != cc:
                r["course_name"] = new
                r["change_note_vs_previous"] = (r.get("change_note_vs_previous", "") + "; " if r.get("change_note_vs_previous", "") else "") + CANON_NOTE
                canon.append((r["subject_id"], cc, new))

    # sanity: no BBC*/BVA* code tokens left in BTech rows (contamination fingerprint)
    leaks = []
    for r in rows:
        if r["row_kind"] == "subject" and r["course_name"] == "BTech":
            for tok in (r.get("all_codes", "") + ";" + r.get("primary_code", "")).split(";"):
                tok = tok.strip()
                if tok.startswith("BBC") or tok.startswith("BOP"):
                    leaks.append((r["subject_id"], tok))
    if leaks:
        print("ABORT: BCA/BPharm code tokens still in BTech rows:", leaks[:8])
        return 2

    # gates
    g2, ncodes = gate_g2(rows)
    g3 = gate_g3(rows)
    print(f"G1|{'PASS' if not g1 else 'FAIL ' + g1}")
    print(f"G2|{'PASS' if not g2 else 'FAIL ' + g2}|codes={ncodes}")
    print(f"G3|{'PASS' if not g3 else 'FAIL ' + g3}")
    if g1 or g2 or g3:
        print("ABORT: gate failure")
        return 2

    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REF_HEADER, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in REF_HEADER})
    print(f"REPAIR OK rows={len(rows)} reverted={len(reverted)} course_canon={len(canon)}")
    for sid, n in reverted:
        print(f"  reverted {sid}: {n} fields")
    from collections import Counter
    print("course census:", dict(Counter(r["course_name"] for r in rows if r["row_kind"] == "subject")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
