#!/usr/bin/env python3
"""wave_commit.py — shared apply+gates+commit machinery for the correction
waves (W1/W2/W5/W6...). Used by the wave scripts; NOT a corpus-ingest path.

Edits format (JSONL or list of dicts):
  {"sid": "...", "field": "unit3_text" | "textbooks_structured[2]",
   "before": "<current exact substring>", "after": "<replacement>",
   "rule": "AUTH_TYPO_warshal", "evidence": "doc#sha16 pp.12 + ref ..."}

Rules (owner directive D1 → RULES §6b):
  * primary field fixed; "before" preserved in corrections_json;
  * verification_status → corrected; quality_flags tag updated;
  * change_note_vs_previous + notes quirk appended;
  * gates G1(v2)/G2/G3/G6(touched, pre-edit fallback probe) must PASS.
"""
import csv
import json
import re
import shutil
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import merge_draft as MD  # REF_HEADER + gates (single source of truth)

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
BASE = "/home/z/my-project/work/pipeline_v2"
AUDIT_FLAGS = f"{BASE}/audit_flags.json"


def load_rows(path=CSV_PATH):
    with open(path, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        hdr = rdr.fieldnames
        rows = list(rdr)
    if hdr != MD.REF_HEADER:
        raise SystemExit(f"WAVE_ABORT|header mismatch: {len(hdr)} cols, expected v2 {len(MD.REF_HEADER)} (run schema_v2.py first)")
    return rows


def load_flags():
    try:
        return json.load(open(AUDIT_FLAGS))
    except Exception:
        return {"rows": {}}


def _entry_key(col):
    return "exp" if col == "experiments_structured" else "book"


def field_get(row, field):
    m = re.fullmatch(r"(\w+)\[(\d+)\]", field)
    if m:
        col, idx = m.group(1), int(m.group(2))
        arr = json.loads(row.get(col, "") or "[]")
        if idx >= len(arr):
            raise KeyError(f"{row.get('subject_id')}:{field} index out of range")
        b = arr[idx]
        return b.get(_entry_key(col)) if isinstance(b, dict) else b
    return row.get(field, "") or ""


def field_set(row, field, value):
    m = re.fullmatch(r"(\w+)\[(\d+)\]", field)
    if m:
        col, idx = m.group(1), int(m.group(2))
        arr = json.loads(row.get(col, "") or "[]")
        if isinstance(arr[idx], dict):
            arr[idx][_entry_key(col)] = value
        else:
            arr[idx] = value
        row[col] = json.dumps(arr, ensure_ascii=False)
    else:
        row[field] = value


def apply_edits(rows, edits, wave, flags_doc, note_extra=""):
    """Returns (rows, per_sid_corrections). Validates every before-substring."""
    by_id = {r["subject_id"]: r for r in rows}
    per_sid = {}
    skipped = []
    for e in edits:
        r = by_id.get(e["sid"])
        if r is None:
            skipped.append((e["sid"], "row missing"))
            continue
        cur = field_get(r, e["field"])
        if e["before"] not in cur:
            skipped.append((e["sid"], f"before-substring not found in {e['field']}"))
            continue
        new = cur.replace(e["before"], e["after"]) if e.get("all") else cur.replace(e["before"], e["after"], 1)
        field_set(r, e["field"], new)
        cjson = json.loads(r.get("corrections_json", "") or "[]")
        cjson.append({"field": e["field"], "before": e["before"], "after": e["after"],
                      "rule": e["rule"], "evidence": e["evidence"], "wave": wave})
        r["corrections_json"] = json.dumps(cjson, ensure_ascii=False)
        r["verification_status"] = "corrected"
        qf = [f for f in (r.get("quality_flags", "") or "").split(";") if f.strip()]
        qf = [f for f in qf if not f.startswith(e["rule"])]
        if f"corrected_{e['rule']}" not in qf:
            qf.append(f"corrected_{e['rule']}")
        r["quality_flags"] = ";".join(qf)
        seg = f"{wave}({e['rule']}): primary-field correction per RULES §6b — before-form preserved in corrections_json"
        if seg not in (r.get("change_note_vs_previous", "") or ""):
            r["change_note_vs_previous"] = ((r.get("change_note_vs_previous", "") + "; ") if r.get("change_note_vs_previous", "") else "") + seg
        per_sid.setdefault(e["sid"], []).append(e)
    if note_extra:
        for sid in per_sid:
            r = by_id[sid]
            if note_extra not in (r.get("notes", "") or ""):
                r["notes"] = ((r.get("notes", "") + " | ") if r.get("notes", "") else "") + note_extra
    return rows, per_sid, skipped


def run_gates(rows, touched_ids, pre_rows_by_id, parsed_dir=f"{BASE}/parsed"):
    g1 = MD.gate_g1(list(rows[0].keys()))
    g2, ncodes = MD.gate_g2(rows)
    g3 = MD.gate_g3(rows)
    g6, checks = MD.gate_g6(rows, set(touched_ids), parsed_dir, frozenset())
    pre_hit_rows = []
    if g6:
        fail_sids = set(re.findall(r"([a-z0-9\-]+):", g6))
        fail_sids &= set(touched_ids)
        if fail_sids:
            pre_rows = [pre_rows_by_id[s] for s in fail_sids if s in pre_rows_by_id]
            g6_pre, _ = MD.gate_g6(pre_rows, fail_sids, parsed_dir, frozenset())
            if not g6_pre:
                pre_hit_rows = sorted(fail_sids)
                g6 = None
    return {"g1": g1, "g2": g2, "g2_codes": ncodes, "g3": g3, "g6": g6,
            "g6_checks": checks, "g6_pre_edit_hits": pre_hit_rows}


def commit(rows, wave, edits_applied, gates, meta_extra=None):
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    import os
    os.makedirs(f"{BASE}/backup", exist_ok=True)
    bkp = f"{BASE}/backup/pre_commit_{ts.replace(':', '').replace('+', 'p')}.csv"
    shutil.copy(CSV_PATH, bkp)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MD.REF_HEADER, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in MD.REF_HEADER})
    rec = {"ts": ts, "mode": "wave_commit", "wave": wave,
           "rows": len(rows), "edits_applied": edits_applied, "gates": gates}
    if meta_extra:
        rec.update(meta_extra)
    with open(f"{BASE}/last_commit.json", "w") as fh:
        json.dump(rec, fh, indent=1)
    print(f"WAVE_COMMIT_OK|{wave}|rows={len(rows)}|edits={edits_applied}|backup={bkp}")


def refresh_flags_consumed(wave_rules_fixed):
    """Mark audit_flags entries as consumed so later waves/re-audit see the state."""
    try:
        doc = json.load(open(AUDIT_FLAGS))
    except Exception:
        return
    for sid, fl in list(doc.get("rows", {}).items()):
        keep = []
        for f in fl:
            rl = f.get("rule", "")
            if rl in wave_rules_fixed and f.get("action", "").startswith("fix:"):
                continue
            keep.append(f)
        if keep:
            doc["rows"][sid] = keep
        else:
            doc["rows"].pop(sid, None)
    doc["consumed_by"] = doc.get("consumed_by", []) + [{"wave": wave_rules_fixed.get("__wave__", "?") if isinstance(wave_rules_fixed, dict) else "?", "rules": list(k for k in wave_rules_fixed if k != "__wave__")}]
    json.dump(doc, open(AUDIT_FLAGS, "w"), indent=1, ensure_ascii=False)
