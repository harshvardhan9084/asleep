#!/usr/bin/env python3
"""
Pipeline v2 — Step 1: Row-kind separation (owner architecture decision).
Main CSV  : row_kind == 'subject' ONLY (the idempotency unit).
Aux CSV   : everything else (semester_summary, elective_pool, program_rule, ...).
rr_sid    : NOT assigned here (owner rule: assigned once, after the whole catalog is done).
Both files keep the identical 57-col schema so merges stay uniform.
"""
import csv, sys

MAIN = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
AUX  = "/home/z/my-project/download/art_d_final/syllabus_aux.csv"
BACKUP = "/home/z/my-project/work/pipeline_v2/syllabus_extreme_rich.backup_v6.csv"

def main():
    with open(MAIN, encoding="utf-8-sig") as f:
        rdr = csv.DictReader(f)
        cols = rdr.fieldnames
        rows = list(rdr)

    subjects = [r for r in rows if r.get("row_kind") == "subject"]
    aux      = [r for r in rows if r.get("row_kind") != "subject"]

    # --- Gate A: no row may be lost
    assert len(subjects) + len(aux) == len(rows), "row count mismatch"
    # --- Gate B: subject_id uniqueness inside main
    sids = [r["subject_id"] for r in subjects]
    assert len(sids) == len(set(sids)), "duplicate subject_id in subject rows"

    with open(MAIN, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(subjects)
    with open(AUX, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(aux)

    print(f"OK main(subject)={len(subjects)} aux(non-subject)={len(aux)} schema={len(cols)} cols")
    from collections import Counter
    print("aux kinds:", dict(Counter(r["row_kind"] for r in aux)))

if __name__ == "__main__":
    main()
