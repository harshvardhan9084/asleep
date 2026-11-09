#!/usr/bin/env python3
"""w10c_apply.py — W10c apply (2026-11-10, B74).

Writes subject_type ONLY for print_category verdicts (same-page governing
section header, individually reproduced) mapping EXACTLY into committed
vocab: open-elective / departmental-elective / elective (W10b L4 + W8c/W9c
committed classes; "Department Elective-<slot>" prints map to
departmental-elective per the printed section the code sits in).
cross_page_section (doc-continuity) is NOT written — demonstrated unsafe on
textile-era scheme docs (cores listed pages after an unrelated section
header); those rows keep the flag with the probe note (zero-guess, RULES §4).
Every write: corrections_json {before,after,rule,evidence page cite} +
verification_status=corrected + corrected_W10C_CATEGORY quality tag +
change_note + subject_type_norm mirror + durable notes marker "W10c probe:".
All non-written targets get the durable probe note only. T2T 0.
"""
import json
import sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

BASE = WC.BASE
MARK = "W10c probe:"
WRITEABLE = ("open-elective", "departmental-elective", "elective")

ck = json.load(open(f"{BASE}/w10c_ckpt.json")).get("results", {})
rows = WC.load_rows()
by_id = {r["subject_id"]: r for r in rows}

def seg_for(sid, v):
    st = v.get("status", "?")
    ev = (v.get("evidence") or "").strip()
    cat = f" -> {v.get('category')}" if v.get("category") else ""
    core = f"{MARK} {st}{cat}"
    if st == "no_code_print_found":
        core += f" ({v.get('pages_probed') or 'text-layer'} pages probed)"
    return f"{core} at {ev}" if ev else core

n_notes = n_writes = 0
touched = {}
for sid, r in by_id.items():
    v = ck.get(sid)
    if not v:
        continue
    seg = seg_for(sid, v)
    if f"{MARK} {v.get('status')}" in (r.get("notes", "") or ""):
        pass  # idempotent on status level
    elif seg[:80] not in (r.get("notes", "") or ""):
        old = r.get("notes", "") or ""
        r["notes"] = (old + " | " if old else "") + seg
        n_notes += 1
    if v.get("status") == "print_category" and v.get("category") in WRITEABLE:
        if (r.get("subject_type") or "").strip():
            continue  # filled elsewhere meanwhile
        cat = v["category"]
        r["subject_type"] = cat
        r["subject_type_norm"] = cat
        cjson = json.loads(r.get("corrections_json") or "[]")
        if not any(e.get("rule") == "TYPE_EMPTY" and e.get("after") == cat
                   for e in cjson):
            cjson.append({"field": "subject_type", "before": "", "after": cat,
                          "rule": "TYPE_EMPTY", "evidence": v.get("evidence", ""),
                          "wave": "W10c"})
            r["corrections_json"] = json.dumps(cjson, ensure_ascii=False)
        r["verification_status"] = "corrected"
        qf = [f for f in (r.get("quality_flags", "") or "").split(";") if f.strip()]
        if "corrected_W10C_CATEGORY" not in qf:
            qf.append("corrected_W10C_CATEGORY")
        r["quality_flags"] = ";".join(qf)
        note = "W10c(TYPE_EMPTY): subject_type set from printed scheme section header per RULES §6b — print evidence page-cited in corrections_json"
        if note not in (r.get("change_note_vs_previous", "") or ""):
            prev = r.get("change_note_vs_previous", "") or ""
            r["change_note_vs_previous"] = (prev + "; " if prev else "") + note
        touched[sid] = r
        n_writes += 1

print(f"W10C_APPLY|writes={n_writes}|note_rows={n_notes}")

if not touched:
    print("W10C_APPLY|nothing to commit (notes-only updates need commit too if any)")
    if n_notes:
        pre = {r["subject_id"]: dict(r) for r in rows}
        gates = WC.run_gates(rows, [], pre)
        print("GATES|g1:", gates["g1"], "|g2:", gates["g2"], f"codes={gates['g2_codes']}",
              "|g3:", gates["g3"], "|g6:", gates["g6"])
        ok = all(gates[k] in (True, None) for k in ("g1", "g2", "g3", "g6"))
        if ok:
            WC.commit(rows, "W10c", [], gates, {"probe_notes": n_notes, "writes": 0})
            print("W10C_APPLY|committed notes-only")
        else:
            print("WAVE_ABORT|gates failed")
    sys.exit(0)

pre_rows_by_id = {r["subject_id"]: dict(r) for r in rows}
gates = WC.run_gates(rows, sorted(touched), pre_rows_by_id)
print("GATES|g1:", gates["g1"], "|g2:", gates["g2"], f"codes={gates['g2_codes']}",
      "|g3:", gates["g3"], "|g6:", gates["g6"], "|pre_hits:", gates["g6_pre_edit_hits"])
ok = all(gates[k] in (True, None) for k in ("g1", "g2", "g3", "g6"))
if not ok:
    print("WAVE_ABORT|gates failed")
    sys.exit(2)

WC.commit(rows, "W10c", [], gates,
          {"writes": n_writes, "probe_note_rows": n_notes,
           "verdicts": {s: sum(1 for v in ck.values() if v.get("status") == s)
                        for s in ("print_category", "cross_page_section",
                                  "no_header_above", "no_code_print_found")}})
print("W10C_APPLY|committed")
