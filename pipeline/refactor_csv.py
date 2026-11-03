#!/usr/bin/env python3
"""One-time refactor per owner ruling (Task 29 ruling set, item: row-kind separation).

Main CSV keeps ONLY row_kind='subject' rows (the idempotency unit).
All other row kinds (elective_pool, program_rule, semester_summary) migrate verbatim
to syllabus_aux_rows.csv (same 57-column schema).

- Studying-path columns (university_name / course_name / branch_names) already exist
  since registry v4 — verified present, nothing to add.
- rr_sid is NOT assigned here (owner assigns at the very end).
- Backup written before any mutation; refuses to run twice (idempotent guard).
"""
import csv, hashlib, os, shutil, sys

BASE = "/home/z/my-project"
MAIN = f"{BASE}/download/art_d_final/syllabus_extreme_rich.csv"
AUX  = f"{BASE}/download/art_d_final/syllabus_aux_rows.csv"
BACKUP = f"{BASE}/work/pipeline_v2/backups/syllabus_extreme_rich.pre_refactor.csv"

EXPECTED_COLS = 57

def main():
    if os.path.exists(AUX):
        print("AUX already exists -> refactor already done, refusing to run twice.")
        sys.exit(2)
    os.makedirs(os.path.dirname(BACKUP), exist_ok=True)

    with open(MAIN, newline="", encoding="utf-8") as f:
        rdr = csv.reader(f)
        header = next(rdr)
        rows = list(rdr)

    assert len(header) == EXPECTED_COLS, f"header has {len(header)} cols, expected {EXPECTED_COLS}"
    kind_idx = header.index("row_kind")
    subj_rows = [r for r in rows if r[kind_idx] == "subject"]
    aux_rows  = [r for r in rows if r[kind_idx] != "subject"]

    # Backup (bit-identical copy)
    shutil.copy2(MAIN, BACKUP)
    sha = hashlib.sha256(open(BACKUP, "rb").read()).hexdigest()[:16]

    with open(MAIN, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(subj_rows)
    with open(AUX, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(aux_rows)

    kinds = {}
    for r in aux_rows:
        kinds[r[kind_idx]] = kinds.get(r[kind_idx], 0) + 1
    print(f"backup: {BACKUP} (sha256 {sha})")
    print(f"main: {len(subj_rows)} subject rows (was {len(rows)})")
    print(f"aux:  {len(aux_rows)} rows by kind: {kinds}")
    assert len(subj_rows) + len(aux_rows) == len(rows), "row count mismatch!"

if __name__ == "__main__":
    main()
