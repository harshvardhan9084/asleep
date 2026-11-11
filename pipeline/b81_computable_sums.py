#!/usr/bin/env python3
"""b81_computable_sums.py — owner directive 2026-11-11: "Inventing a data and
calculating a data is different!"

Policy: where every component of a deterministic sum/formula is already
printed in the row's own cells, the derived cell is CALCULATED, not left for
review.  Only pure-missing components stay needs_review.

Rebuild the marks/credit DAG from the FINEST printed components (one pass):
  sessional_total = sessional_ct + sessional_ta
  total_marks     = sessional_total + ese_te_pe
  credit          = L + T + P/2            (audit v25 CREDIT_FORMULA formula)
Coarse cells that disagree with the recomputed value are corrected
(superseded print preserved in corrections_json before-field); coarse cells
that are empty are filled.  Rows carrying a W9b2/W10g accepted-print
attestation are skipped entirely (attested faithful prints are never
overwritten).  No value is ever invented: a component that is absent blocks
its whole chain.

Usage:  b81_computable_sums.py --dry-run   (default: plan only, no writes)
        b81_computable_sums.py --apply
"""
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import merge_draft as MD  # gate_g1/g2/g3/g6, REF_HEADER (stdlib-only import)

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
FLAGS_PATH = "/home/z/my-project/work/pipeline_v2/audit_flags.json"
PARSED_DIR = "/home/z/my-project/work/pipeline_v2/parsed"
BACKUP_DIR = "/home/z/my-project/work/pipeline_v2/backup"
RESULT_PATH = "/home/z/my-project/work/pipeline_v2/b81_result.json"
AUDIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_rules.py")

ATTEST = ("W9b2 probe: accepted-print", "W10g probe: accepted-print")


def num(x):
    try:
        return float(x) if str(x).strip() else None
    except Exception:
        return None


def fmt(v):
    """Match CSV conventions: integer-style cells dominate (2675 int vs 3 dot
    in credit; 100% int in every marks column) — integral values print bare,
    non-integral keep one minimal decimal (e.g. 3.5)."""
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s


def first_pin(r):
    """Real provenance pin for evidence: first #sha16 citation with its doc
    name, taken verbatim from the row's own provenance chain."""
    for col in ("source_scheme_line", "source_syllabus", "source_history"):
        txt = r.get(col, "") or ""
        m = re.search(r"([A-Za-z0-9_.\-]+\.pdf)#([0-9a-f]{16})", txt)
        if m:
            return f"{m.group(1)}#{m.group(2)}"
    m = re.search(r"#([0-9a-f]{16})", r.get("source_syllabus", "") or "")
    return f"sha16:{m.group(1)}" if m else "no-sha-pin"


def plan_row(r):
    """Return (updates, reasons) or (None, None) if nothing to do.
    updates: list of (field, before, after, kind, formula_desc)"""
    if any(a in (r.get("notes", "") or "") for a in ATTEST):
        return None, "attested-print-skip"
    L, T, P, cr = num(r.get("L")), num(r.get("T")), num(r.get("P")), num(r.get("credit"))
    ct, ta = num(r.get("sessional_ct")), num(r.get("sessional_ta"))
    stt, ese, tm = num(r.get("sessional_total")), num(r.get("ese_te_pe")), num(r.get("total_marks"))
    updates = []

    # --- marks DAG rebuilt from finest printed components
    base_stt = (ct + ta) if (ct is not None and ta is not None) else stt
    new_tm = (base_stt + ese) if (base_stt is not None and ese is not None) else None

    if ct is not None and ta is not None and stt is not None and abs(stt - (ct + ta)) > 0.01:
        updates.append(("sessional_total", fmt(stt), fmt(ct + ta), "fix",
                        f"sessional_ct {fmt(ct)} + sessional_ta {fmt(ta)} (audit v25 SESS_SUM)"))
    elif ct is not None and ta is not None and stt is None:
        updates.append(("sessional_total", "", fmt(ct + ta), "fill",
                        f"sessional_ct {fmt(ct)} + sessional_ta {fmt(ta)} (audit v25 SESS_SUM)"))
    stt_eff = (ct + ta) if (ct is not None and ta is not None) else stt

    if stt_eff is not None and ese is not None and tm is not None and abs(tm - (stt_eff + ese)) > 0.01:
        updates.append(("total_marks", fmt(tm), fmt(stt_eff + ese), "fix",
                        f"sessional_total {fmt(stt_eff)} + ese_te_pe {fmt(ese)} (audit v25 MARKS_SUM)"))
    elif stt_eff is not None and ese is not None and tm is None:
        updates.append(("total_marks", "", fmt(stt_eff + ese), "fill",
                        f"sessional_total {fmt(stt_eff)} + ese_te_pe {fmt(ese)} (audit v25 MARKS_SUM)"))

    # --- credit formula
    if None not in (L, T, P, cr) and abs(cr - (L + T + P / 2)) > 0.01:
        updates.append(("credit", fmt(cr), fmt(L + T + P / 2), "fix",
                        f"L {fmt(L)} + T {fmt(T)} + P/2 {fmt(P / 2)} (audit v25 CREDIT_FORMULA)"))
    elif (L is not None and T is not None and P is not None and cr is None):
        updates.append(("credit", "", fmt(L + T + P / 2), "fill",
                        f"L {fmt(L)} + T {fmt(T)} + P/2 {fmt(P / 2)} (audit v25 CREDIT_FORMULA)"))

    return (updates, None) if updates else (None, "no-op")


def main():
    apply = "--apply" in sys.argv
    rows = list(csv.DictReader(open(CSV_PATH)))
    fields = list(rows[0].keys())
    assert fields == MD.REF_HEADER, "header drift vs REF_HEADER"
    by_id = {r["subject_id"]: r for r in rows}
    fl = json.load(open(FLAGS_PATH))
    flagged = fl.get("rows", {})

    stats = {"flagged_targets": 0, "fix_cells": 0, "fill_cells": 0, "rows_changed": 0,
             "attested_skip": 0, "rule_fixes": {}, "fills": {}}
    changes = []  # (sid, field, before, after, kind, formula)
    for sid, fls in flagged.items():
        rules = {f["rule"] for f in fls}
        if not (rules & {"CREDIT_FORMULA", "SESS_SUM", "MARKS_SUM"}):
            continue
        stats["flagged_targets"] += 1
        r = by_id.get(sid)
        if not r:
            continue
        upd, why = plan_row(r)
        if why == "attested-print-skip":
            stats["attested_skip"] += 1
            continue
        if not upd:
            print(f"WARN|no-plan|{sid}|{sorted(rules)}")
            continue
        for field, before, after, kind, formula in upd:
            changes.append((sid, field, before, after, kind, formula))

    # --- sweep ALL rows for silent fills + silent inconsistencies (the audit
    # never fired on these: empty coarse cells fire no flag)
    for r in rows:
        sid = r["subject_id"]
        if sid in flagged:
            continue  # flagged rows already planned above
        upd, why = plan_row(r)
        if upd:
            for field, before, after, kind, formula in upd:
                changes.append((sid, field, before, after, kind, formula))

    for _, _, _, _, kind, formula in changes:
        if kind == "fix":
            stats["fix_cells"] += 1
            key = formula.split(" (")[1].rstrip(")")
            stats["rule_fixes"][key] = stats["rule_fixes"].get(key, 0) + 1
        else:
            stats["fill_cells"] += 1
            stats["fills"][formula.split(" (")[1].rstrip(")")] = \
                stats["fills"].get(formula.split(" (")[1].rstrip(")"), 0) + 1

    print(f"B81|plan|targets={stats['flagged_targets']}|fix={stats['fix_cells']}"
          f"|fill={stats['fill_cells']}|rule_fixes={stats['rule_fixes']}|fills={stats['fills']}")

    if not apply:
        for sid, field, before, after, kind, formula in changes[:12]:
            print(f"  DRY {sid} {field}: {before!r} -> {after!r} [{kind}] {formula}")
        return

    # --- apply
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    bkp = os.path.join(BACKUP_DIR, f"pre_commit_B81_{stamp}.csv")
    import shutil
    shutil.copy2(CSV_PATH, bkp)

    by_id = {r["subject_id"]: r for r in rows}
    touched = set()
    for sid, field, before, after, kind, formula in changes:
        r = by_id[sid]
        old = r.get(field, "") or ""
        r[field] = after
        entry = {
            "field": field,
            "before": before,
            "after": after,
            "rule": f"B81_COMPUTED_{field.upper()}_{kind.upper()}",
            "evidence": (f"calculated {field}={after} from the row's own printed component "
                         f"cells ({formula}); superseded print {before!r} preserved in before; "
                         f"provenance pin {first_pin(r)}; owner directive 2026-11-11: "
                         f"calculating is not inventing"),
            "wave": "W11a",
        }
        try:
            cj = json.loads(r.get("corrections_json", "") or "[]")
        except Exception:
            cj = []
        cj.append(entry)
        r["corrections_json"] = json.dumps(cj, ensure_ascii=False)
        touched.add(sid)
        stats["rows_changed"] += 1

    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MD.REF_HEADER, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    # --- gates (identical functions to the merge-time commit gate)
    g1 = MD.gate_g1(MD.REF_HEADER)
    g2, ncodes = MD.gate_g2(rows)
    g3 = MD.gate_g3(rows)
    g6, checks = MD.gate_g6(rows, touched, PARSED_DIR)
    gates = {"G1": g1 or "PASS", "G2": (g2 or f"PASS codes={ncodes}"),
             "G3": g3 or "PASS", "G6": (g6 or f"PASS containment_checks={checks}")}
    print("GATES|" + " | ".join(f"{k} {v}" for k, v in gates.items()))
    stats["gates"] = gates
    stats["touched_rows"] = len(touched)

    # --- audit re-scan
    pre = os.path.join(BACKUP_DIR, "audit_flags_preB81.json")
    if os.path.exists(FLAGS_PATH):
        import shutil as _s
        _s.copy2(FLAGS_PATH, pre)
    rc = subprocess.run([sys.executable, AUDIT, "--csv", CSV_PATH,
                         "--out", FLAGS_PATH, "--quiet"], capture_output=True, text=True, timeout=600)
    if rc.returncode != 0:
        print("AUDIT|FAIL", rc.stderr[-400:])
        sys.exit(2)
    new = json.load(open(FLAGS_PATH))
    stats["flags_before"] = fl.get("total_flags")
    stats["flags_after"] = new.get("total_flags")
    stats["summary_after"] = new.get("summary")
    stats["backup"] = bkp
    stats["applied_utc"] = datetime.now(timezone.utc).isoformat()
    json.dump(stats, open(RESULT_PATH, "w"), indent=1)
    print(f"B81|done|flags {stats['flags_before']} -> {stats['flags_after']}")
    print("SUMMARY|" + json.dumps(new.get("summary")))


if __name__ == "__main__":
    main()
