#!/usr/bin/env python3
"""b69_owner_prune.py — OWNER DIRECTIVE 2026-11-09 (verbatim): "delete those
~12-18 rows whose are not subjects of any kind" + "Delete 'k era pool codes'
immediately".

Structural prune (no value edits, zero-guess not implicated):
  R1: drop rows with row_kind != 'subject'  (2 elective_pool + 2 program_rule
      + 8 semester_summary = 12 rows; none carries a course code).
  R2: drop the k_era_pool_codes column (1 non-empty cell in 3,097 rows, and
      that single cell lived on a pool row deleted by R1 — column carried no
      data on any real subject row; pool membership lives in all_codes +
      choice_group_id on the subject rows themselves).
Schema: 63 -> 62 cols (v2.1, owner-ordered; REF_HEADER updated in merge_draft.py).
Gates G1/G2/G3/G6 must PASS before write (G6 touched = none: pure deletion).
"""
import csv, json, sys, shutil
from datetime import datetime, timezone

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import merge_draft as MD
import wave_commit as WC

rows = list(csv.DictReader(open(WC.CSV_PATH)))
assert len(rows) == 3097 and len(rows[0]) == 63, f"pre-state unexpected: {len(rows)}x{len(rows[0])}"

drop = [r for r in rows if r["row_kind"] != "subject"]
keep = [r for r in rows if r["row_kind"] == "subject"]
drop_ids = sorted(r["subject_id"] for r in drop)
assert len(drop) == 12 and len(keep) == 3085, f"drop count {len(drop)} != 12"

# R2: column removal on kept rows
for r in keep:
    r.pop("k_era_pool_codes", None)

hdr = [c for c in MD.REF_HEADER if c != "k_era_pool_codes"]
assert "k_era_pool_codes" not in hdr and len(hdr) == 62

g1 = MD.gate_g1(hdr)
g2, ncodes = MD.gate_g2(keep)
g3 = MD.gate_g3(keep)
g6, checks = MD.gate_g6(keep, set(), f"{WC.BASE}/parsed", frozenset())
print(f"GATES|g1={g1}|g2={g2} codes={ncodes}|g3={g3}|g6={g6} checks={checks}")
if g1 or g2 or g3 or g6:
    print("PRUNE_ABORT|gates failed"); sys.exit(2)

ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
bkp = f"{WC.BASE}/backup/pre_prune_{ts.replace(':', '').replace('+', 'p')}.csv"
shutil.copy(WC.CSV_PATH, bkp)
with open(WC.CSV_PATH, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=hdr, lineterminator="\n")
    w.writeheader()
    for r in keep:
        w.writerow({c: r.get(c, "") for c in hdr})

report = {"batch": "CRON-AUTO-B69", "ts": ts, "rows": f"3097->3085", "cols": "63->62 (schema v2.1 owner-ordered)",
          "dropped_rows": drop_ids, "dropped_col": "k_era_pool_codes",
          "col_cells_before": 1, "backup": bkp,
          "gates": {"g1": "PASS 62-col", "g2": f"PASS codes={ncodes}", "g3": "PASS", "g6": f"PASS checks={checks}"}}
json.dump(report, open(f"{WC.BASE}/b69_prune_report.json", "w"), indent=1)
print(f"PRUNE_OK|rows=3085 cols=62|dropped={drop_ids}")
