#!/usr/bin/env python3
"""schema_v2.py — B51: owner decision D2 (2026-11-08). Adds the 6 schema-v2
columns (RULES §5 G1 v2) and populates the derived ones:
  quality_flags        ← audit_rules.py machine flags (current state)
  code_family          ← primary_code prefix family (deterministic)
  verification_status  ← unreviewed (flags present) / reviewed_clean (none)
  subject_name_display / subject_type_norm / corrections_json  ← empty (W4/W1 fill)
Then G1(v2)/G2/G3/G6 + backup + write + last_commit.json."""
import csv
import json
import re
import shutil
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import merge_draft as MD

CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
BASE = "/home/z/my-project/work/pipeline_v2"

with open(CSV, newline="", encoding="utf-8") as f:
    rdr = csv.DictReader(f)
    hdr = rdr.fieldnames
    rows = list(rdr)
print(f"IN|rows={len(rows)} cols={len(hdr)}")
assert hdr == MD.REF_HEADER[:57] or hdr == MD.REF_HEADER, "unexpected input header"

flags_doc = json.load(open(f"{BASE}/audit_flags.json"))
flag_rows = flags_doc.get("rows", {})

n_qf = n_cf = 0
for r in rows:
    sid = r.get("subject_id", "")
    fl = flag_rows.get(sid, [])
    r.setdefault("subject_name_display", "")
    r.setdefault("subject_type_norm", "")
    r.setdefault("quality_flags", "")
    r.setdefault("corrections_json", "")
    r.setdefault("code_family", "")
    r.setdefault("verification_status", "")
    if not r["quality_flags"]:
        rules = []
        for x in fl:
            rl = x.get("rule", "")
            if rl not in rules:
                rules.append(rl)
        r["quality_flags"] = ";".join(rules)
        n_qf += 1
    if not r["code_family"]:
        m = re.match(r"^([A-Z]{2,4})\d{3}", (r.get("primary_code", "") or "").strip().upper())
        if m:
            r["code_family"] = m.group(1)
            n_cf += 1
    if not r["verification_status"]:
        r["verification_status"] = "unreviewed" if fl else "reviewed_clean"

# ---- gates
g1 = MD.gate_g1(list(rows[0].keys()))
g2, ncodes = MD.gate_g2(rows)
g3 = MD.gate_g3(rows)
g6, checks = MD.gate_g6(rows, set(), f"{BASE}/parsed", frozenset())
print(f"G1|{'PASS' if not g1 else 'FAIL ' + g1}")
print(f"G2|{'PASS' if not g2 else 'FAIL ' + g2}|codes={ncodes}")
print(f"G3|{'PASS' if not g3 else 'FAIL ' + g3}")
print(f"G6|{'PASS' if not g6 else 'FAIL ' + g6}|containment_checks={checks} (no touched rows)")
if g1 or g2 or g3 or g6:
    print("ABORT: gate failure")
    sys.exit(2)

ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
import os
os.makedirs(f"{BASE}/backup", exist_ok=True)
bkp = f"{BASE}/backup/pre_commit_{ts.replace(':', '').replace('+', 'p')}.csv"
shutil.copy(CSV, bkp)
with open(CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=MD.REF_HEADER, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in MD.REF_HEADER})
json.dump({"ts": ts, "mode": "wave_commit", "wave": "B51-schema-v2",
           "rows": len(rows), "quality_flags_set": n_qf, "code_family_set": n_cf,
           "gates": {"g1": None, "g2": None, "g2_codes": ncodes, "g3": None,
                     "g6": None, "g6_checks": checks}}, open(f"{BASE}/last_commit.json", "w"), indent=1)
print(f"COMMIT_OK|rows={len(rows)} cols=63|quality_flags={n_qf}|code_family={n_cf}|backup={bkp}")
