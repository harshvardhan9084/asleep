#!/usr/bin/env python3
"""w8c_type_vocab.py — W8c subject_type vocab normalization (owner go 2026-11-08
"continue with both" = W8b + W8c). Zero-guess discipline: every applied value
is (a) a normalization ALREADY RECORDED in this row's own subject_type_norm by
prior committed waves (owner-reviewed through B63), or (b) an owner-sanctioned
literal mapping (laboratory/workshop -> lab), or (c) a print-token decision
already recorded on other committed rows (VA -> value-added-mandatory;
'Basic Science Course' phrase -> core). Everything else STAYS flagged
TYPE_RAW needs_review and lands in w8c_decision_memo.json for the owner.
RULES §6b: every write carries corrections_json before/after + quality_flags
tag + change_note seg. Gates G1/G2/G3/G6 must PASS before commit."""
import json
import re
import sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

rows = WC.load_rows()
flags_doc = json.load(open(WC.AUDIT_FLAGS))
raw_sids = {sid for sid, fl in flags_doc.get("rows", {}).items()
            for f in fl if f.get("rule") == "TYPE_RAW" and f.get("action", "").startswith("fix:")}
print(f"W8C|targets={len(raw_sids)}")

CONTROLLED_TYPES = {"theory", "lab", "practical", "core", "departmental-elective",
                    "open-elective", "elective", "value-added-mandatory"}

pre_rows = {r["subject_id"]: dict(r) for r in rows}
edits_by_sid = {}
touched = set()
memo = {}


def bump(sid):
    edits_by_sid[sid] = edits_by_sid.get(sid, 0) + 1


def corrections_append(r, entry):
    cj = r.get("corrections_json", "") or ""
    try:
        arr = json.loads(cj) if cj.strip() else []
    except Exception:
        arr = []
    arr.append(entry)
    r["corrections_json"] = json.dumps(arr, ensure_ascii=False)


def qf_tag(r, rule):
    qf = r.get("quality_flags", "") or ""
    tag = "corrected_" + rule.split("/")[1]
    tags = [t for t in qf.split(";") if t]
    if tag not in tags:
        tags.append(tag)
    r["quality_flags"] = ";".join(tags)


def note_seg(r, seg):
    if seg not in (r.get("change_note_vs_previous", "") or ""):
        prev = r.get("change_note_vs_previous", "") or ""
        r["change_note_vs_previous"] = (prev + "; " if prev else "") + seg


def apply_type(r, value, rule, evidence):
    before = (r.get("subject_type", "") or "").strip()
    r["subject_type"] = value
    if (r.get("subject_type_norm", "") or "").strip() != value:
        r["subject_type_norm"] = value
    corrections_append(r, {"field": "subject_type", "before": before, "after": value,
                           "rule": rule, "evidence": evidence, "wave": "W8c"})
    qf_tag(r, rule)
    note_seg(r, f"W8c §6b normalization ({rule}: subject_type -> controlled vocab; "
                "before preserved in corrections_json; print kept verbatim in subject_category_print)")
    touched.add(r["subject_id"])
    bump(r["subject_id"])


n_a = n_b = n_c = n_d = 0
for r in rows:
    sid = r["subject_id"]
    if sid not in raw_sids:
        continue
    if (r.get("row_kind", "subject") or "subject") != "subject":
        continue
    st = (r.get("subject_type", "") or "").strip()
    nrm = (r.get("subject_type_norm", "") or "").strip()
    prn = (r.get("subject_category_print", "") or "").strip()
    if nrm in CONTROLLED_TYPES and nrm != st:
        apply_type(r, nrm, "W4/TYPE_NORM_RECORDED",
                   "value already recorded in this row's subject_type_norm by a prior committed "
                   "wave (owner-reviewed through B63); pure copy, zero new interpretation")
        n_a += 1
        continue
    # norm absent/invalid: only owner-sanctioned or print-recorded literals
    if st.lower() in ("laboratory", "workshop") and "lab" not in (r.get("subject_name", "") or "").lower():
        apply_type(r, "lab", "W4/TYPE_NORM_OWNER_LAB",
                   "owner-sanctioned mapping laboratory/workshop->lab (go 2026-11-08); consistent "
                   "with committed PC lab-nature rows (print 'PC'->lab recorded x10)")
        n_c += 1
        continue
    if st.lower() in ("laboratory", "workshop"):
        apply_type(r, "lab", "W4/TYPE_NORM_OWNER_LAB",
                   "owner-sanctioned mapping laboratory/workshop->lab (go 2026-11-08); subject name "
                   "itself denotes lab/workshop delivery")
        n_c += 1
        continue
    if prn == "VA":
        apply_type(r, "value-added-mandatory", "W4/TYPE_NORM_PRINT_VA",
                   "print token 'VA' recorded -> value-added-mandatory on 3 committed rows "
                   "(subject_category_print kept verbatim)")
        n_b += 1
        continue
    if "basic science course" in st.lower():
        apply_type(r, "core", "W4/TYPE_NORM_PRINT_BSC",
                   "phrase 'Basic Science Course' recorded -> core on committed rows (print 'BSC'->core x5, "
                   "'Basic Science Course'->core x2, 'Basic Science Course (BSC)'->core x1)")
        n_d += 1
        continue
    key = (prn, st)
    memo.setdefault(f"{prn}||{st}", {"print": prn, "raw": st, "count": 0})
    memo[f"{prn}||{st}"]["count"] += 1

print(f"W8C|recorded_copy={n_a} print_VA={n_b} owner_lab={n_c} print_BSC={n_d} "
      f"touched={len(touched)} left_flagged={sum(m['count'] for m in memo.values())}")

json.dump({"ts_run": "W8c", "applied": {"recorded_copy": n_a, "print_VA": n_b,
                                        "owner_lab": n_c, "print_BSC": n_d},
           "left_flagged": sorted(memo.values(), key=lambda m: -m["count"])},
          open(f"{WC.BASE}/w8c_decision_memo.json", "w"), indent=1, ensure_ascii=False)

# --- gates + commit (same defer-on-G6 protocol as W8a) ------------------------
def run_and_maybe_defer(rows, touched, pre_rows):
    gates = WC.run_gates(rows, touched, pre_rows)
    deferred = []
    if gates["g6"]:
        for part in gates["g6"].split(";"):
            sid = part.split(":")[0].strip()
            if sid in touched:
                deferred.append(sid)
        for sid in deferred:
            rows[rows.index(next(r for r in rows if r["subject_id"] == sid))] = dict(pre_rows[sid])
            touched.discard(sid)
        if deferred:
            print(f"W8C|g6_gap_deferred={len(deferred)}: {', '.join(deferred)}")
            gates = WC.run_gates(rows, touched, pre_rows)
    return gates, deferred


gates, deferred = run_and_maybe_defer(rows, touched, pre_rows)
print(f"G1|{'PASS' if not gates['g1'] else 'FAIL ' + gates['g1']}")
print(f"G2|{'PASS' if not gates['g2'] else 'FAIL ' + gates['g2']}|codes={gates['g2_codes']}")
print(f"G3|{'PASS' if not gates['g3'] else 'FAIL ' + gates['g3']}")
print(f"G6|{'PASS' if not gates['g6'] else 'FAIL ' + gates['g6']}|checks={gates['g6_checks']}|pre_edit_hits={gates['g6_pre_edit_hits']}")
if any([gates["g1"], gates["g2"], gates["g3"], gates["g6"]]):
    print("ABORT: gate failure")
    sys.exit(2)
applied = sum(edits_by_sid.get(s, 0) for s in touched)
WC.commit(rows, "W8c", applied, gates,
          {"recorded_copy": n_a, "print_VA": n_b, "owner_lab": n_c, "print_BSC": n_d,
           "applied": applied, "touched": len(touched),
           "left_flagged": sum(m["count"] for m in memo.values()),
           "g6_gap_deferred": deferred})
print("W8C|COMMIT_OK")
