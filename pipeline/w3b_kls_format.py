#!/usr/bin/env python3
"""w3b_kls_format.py — B56 addendum: normalize legacy co_kls STRING values
('CO1:K1, K2;CO2:K1, K2;...') to the JSON-array format used everywhere else
(["K1/K2", "K1/K2", ...] — multiple printed K-levels per CO joined with '/').
Content unchanged; format only; corrections_json entry per row.
Gate failures (pre-G6 containment-gap class) → row reverted + G6_CONTAINMENT_GAP flag."""
import csv
import json
import re
import sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

rows = WC.load_rows()
pre_rows_local = {r["subject_id"]: dict(r) for r in rows}

LEG = re.compile(r"CO\s*(\d)\s*[:\-]\s*([^;]+)", re.I)
n_fix = 0
touched = set()
for r in rows:
    v = (r.get("co_kls", "") or "").strip()
    if not v or v == "[]" or v.startswith("["):
        continue
    pairs = {}
    ok = True
    for m in LEG.finditer(v):
        no = int(m.group(1))
        ks = re.findall(r"K([1-6])", m.group(2).upper())
        if not ks:
            ok = False
            break
        pairs[no] = "/".join(f"K{k}" for k in dict.fromkeys(ks))
    if not ok or not pairs:
        continue
    n = max(pairs)
    if n != len(pairs):
        continue  # gaps in numbering — leave for W7 (zero-guess)
    kls = [pairs[i] for i in range(1, n + 1)]
    sid = r["subject_id"]
    cjson = json.loads(r.get("corrections_json", "") or "[]")
    cjson.append({"field": "co_kls", "before": v, "after": json.dumps(kls),
                  "rule": "KLS_FORMAT_NORMALIZE", "evidence": "legacy string format → JSON array (content unchanged; multiple printed K-levels per CO joined '/')", "wave": "W3b"})
    r["corrections_json"] = json.dumps(cjson, ensure_ascii=False)
    r["co_kls"] = json.dumps(kls, ensure_ascii=False)
    qf = [f for f in (r.get("quality_flags", "") or "").split(";") if f.strip()]
    if "corrected_KLS_FORMAT_NORMALIZE" not in qf:
        qf.append("corrected_KLS_FORMAT_NORMALIZE")
    r["quality_flags"] = ";".join(qf)
    touched.add(sid)
    n_fix += 1

print(f"W3b|normalized={n_fix} touched={len(touched)}")

def run_gates_and_prune():
    gates = WC.run_gates(rows, touched, pre_rows_local)
    if not gates["g6"]:
        return gates, set()
    fail = set(re.findall(r"([a-z0-9\-]+):", gates["g6"])) & touched
    pruned = set()
    for sid in fail:
        pre = pre_rows_local.get(sid)
        if pre:
            r = next(x for x in rows if x["subject_id"] == sid)
            for k in ("co_kls", "corrections_json", "quality_flags"):
                r[k] = pre.get(k, "")
            touched.discard(sid)
            pruned.add(sid)
    print(f"W3b|G6_GAP_PRUNE|{len(pruned)} rows reverted+flagged: {sorted(pruned)[:8]}")
    try:
        af = json.load(open(f"{WC.BASE}/audit_flags.json"))
    except Exception:
        af = {"rows": {}}
    for sid in pruned:
        fl = af["rows"].setdefault(sid, [])
        if not any(f.get("rule") == "G6_CONTAINMENT_GAP" for f in fl):
            fl.append({"rule": "G6_CONTAINMENT_GAP", "action": "needs_review",
                       "detail": "unit1 not provable in any currently-resolvable cited doc; W3b co_kls format normalization deferred", "field": "unit1_text"})
    json.dump(af, open(f"{WC.BASE}/audit_flags.json", "w"), indent=1, ensure_ascii=False)
    return gates, pruned

for attempt in range(3):
    gates, pruned = run_gates_and_prune()
    if not gates["g6"] or not pruned:
        break

print(f"G1|{'PASS' if not gates['g1'] else 'FAIL ' + gates['g1']}")
print(f"G2|{'PASS' if not gates['g2'] else 'FAIL ' + gates['g2']}|codes={gates['g2_codes']}")
print(f"G3|{'PASS' if not gates['g3'] else 'FAIL ' + gates['g3']}")
print(f"G6|{'PASS' if not gates['g6'] else 'FAIL ' + gates['g6']}|checks={gates['g6_checks']}")
if any([gates["g1"], gates["g2"], gates["g3"], gates["g6"]]):
    print("ABORT: gate failure")
    sys.exit(2)
WC.commit(rows, "W3b", n_fix, gates, {"normalized": n_fix})
