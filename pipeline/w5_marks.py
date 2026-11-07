#!/usr/bin/env python3
"""w5_marks.py — W5 (B57): marks/credit variance adjudication, deterministic pass.
Owner definition: faithful-print keep+flag vs extraction-error fix-from-print.
SAFE AUTONOMOUS SCOPE (documented): rows whose source_scheme_line prints a
marks-scale integer set EQUAL to the row's marks fields are classified
formula_variance_faithful_print (the row mirrors the print; the FORMULA
variance is the print's own arithmetic — kept, flagged). Rows that do NOT
match are w5_scheme_mismatch needs_review — positional certainty for
fix-from-print requires per-row evidence reads (owner-visible, not guessed).
Flag-only changes; G6-fail rows pruned (containment-gap class)."""
import csv
import json
import re
import sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

rows = WC.load_rows()
pre_rows_local = {r["subject_id"]: dict(r) for r in rows}
flags_doc = WC.load_flags()

def num(x):
    try:
        return float(x) if str(x).strip() else None
    except Exception:
        return None

targets = set()
for sid, fl in flags_doc.get("rows", {}).items():
    if any(f.get("rule") in ("CREDIT_FORMULA", "MARKS_SUM", "SESS_SUM") for f in fl):
        targets.add(sid)

n_faithful = n_mismatch = 0
touched = set()
for sid in targets:
    r = next((x for x in rows if x["subject_id"] == sid), None)
    if not r:
        continue
    marks = [num(r.get(k)) for k in ("sessional_ct", "sessional_ta", "sessional_total", "ese_te_pe", "total_marks")]
    marks = [int(v) for v in marks if v is not None]
    line = r.get("source_scheme_line", "") or ""
    ints = [int(t) for t in re.findall(r"\d{2,3}", line) if not re.fullmatch(r"(19|20)\d{2}", t)]
    if len(marks) >= 4 and len(ints) >= len(marks):
        if sorted(marks) == sorted(ints[:len(marks)]) or sorted(marks) == sorted(ints[-len(marks):]):
            tag, old = "formula_variance_faithful_print", True
            n_faithful += 1
        else:
            tag, old = "w5_scheme_mismatch", False
            n_mismatch += 1
    else:
        tag, old = "w5_scheme_mismatch", False
        n_mismatch += 1
    qf = [f for f in (r.get("quality_flags", "") or "").split(";") if f.strip()
          and f not in ("CREDIT_FORMULA", "MARKS_SUM", "SESS_SUM")]
    if tag not in qf:
        qf.append(tag)
    r["quality_flags"] = ";".join(qf)
    touched.add(sid)

print(f"W5|faithful_print={n_faithful} scheme_mismatch_needs_review={n_mismatch} touched={len(touched)}")

def gates_and_prune():
    gates = WC.run_gates(rows, touched, pre_rows_local)
    if not gates["g6"]:
        return gates, set()
    fail = set(re.findall(r"([a-z0-9\-]+):", gates["g6"])) & touched
    pruned = set()
    for sid in fail:
        pre = pre_rows_local.get(sid)
        if pre:
            r = next(x for x in rows if x["subject_id"] == sid)
            r["quality_flags"] = pre.get("quality_flags", "")
            touched.discard(sid)
            pruned.add(sid)
    print(f"W5|G6_GAP_PRUNE|{len(pruned)}: {sorted(pruned)[:6]}")
    return gates, pruned

for attempt in range(3):
    gates, pruned = gates_and_prune()
    if not gates["g6"] or not pruned:
        break

print(f"G1|{'PASS' if not gates['g1'] else 'FAIL ' + gates['g1']}")
print(f"G2|{'PASS' if not gates['g2'] else 'FAIL ' + gates['g2']}|codes={gates['g2_codes']}")
print(f"G3|{'PASS' if not gates['g3'] else 'FAIL ' + gates['g3']}")
print(f"G6|{'PASS' if not gates['g6'] else 'FAIL ' + gates['g6']}|checks={gates['g6_checks']}")
if any([gates["g1"], gates["g2"], gates["g3"], gates["g6"]]):
    print("ABORT: gate failure")
    sys.exit(2)
WC.commit(rows, "W5", len(touched), gates, {"faithful": n_faithful, "mismatch": n_mismatch})
