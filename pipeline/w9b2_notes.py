#!/usr/bin/env python3
"""w9b2_notes.py — W9b2 (2026-11-10, B75): durable scheme-probe recording.

W9b round-2 probed the 281 scheme-flag rows (CREDIT_FORMULA / SESS_SUM /
MARKS_SUM) code-anchored in the cited docs. Verdicts (w9b_adjudication.json,
reset-volatile) become DURABLE note segments "W9b2 probe:" (evidence surface,
append-only per RULES §6b). The accepted-print verdict (printed scheme row
matches storage verbatim — AKTU's own table breaks the arithmetic, B67
committed class) additionally enables the auditor v22 scan-side skip via the
notes marker, making the recorded-honest drop reset-proof. Idempotent.
No primary-field writes (verdicts carry zero invariant-consistent repairs —
adjudicate produced 0 edits). T2T 0.
"""
import json
import sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

BASE = WC.BASE
MARK = "W9b2 probe:"

adj = json.load(open(f"{BASE}/w9b_adjudication.json"))
vd = adj.get("verdicts", {})
rows = WC.load_rows()
by_id = {r["subject_id"]: r for r in rows}

VERB = {
    "accepted-print": "printed scheme row matches storage verbatim (AKTU's own table breaks the arithmetic) — recorded-honest",
    "no_print_found": "no printed scheme row recoverable (cited scheme docs missing or code-anchored row not found)",
    "stored_matches_no_print": "printed row found but its numbers support no invariant-consistent repair — stored form kept (zero-guess)",
    "sha_unresolved": "cited scheme docs not locally resolvable post-reset",
    "ambiguous": "multiple invariant-consistent repairs possible — not adjudicable without the printed column header",
}

n_seg = 0
touched = {}
for sid, v in sorted(vd.items()):
    r = by_id.get(sid)
    if r is None:
        continue
    st = v.get("status", "?")
    ev = (v.get("evidence") or "").strip()
    rowtext = (v.get("rowtext") or "").strip()
    core = f"{MARK} {st} — {VERB.get(st, st)}"
    if rowtext:
        core += f"; printed row: {rowtext[:80]}"
    seg = f"{core} ({ev})" if ev else core
    old = r.get("notes", "") or ""
    if f"{MARK} {st}" in old:
        continue  # idempotent
    r["notes"] = (old + " | " if old else "") + seg
    touched[sid] = r
    n_seg += 1

print(f"W9B2_NOTES|segments={n_seg}|rows={len(touched)}")
if not touched:
    print("W9B2_NOTES|nothing to do")
    sys.exit(0)

pre_rows_by_id = {r["subject_id"]: dict(r) for r in rows}
gates = WC.run_gates(rows, [], pre_rows_by_id)
print("GATES|g1:", gates["g1"], "|g2:", gates["g2"], f"codes={gates['g2_codes']}",
      "|g3:", gates["g3"], "|g6:", gates["g6"])
ok = all(gates[k] in (True, None) for k in ("g1", "g2", "g3", "g6"))
if not ok:
    print("WAVE_ABORT|gates failed")
    sys.exit(2)

WC.commit(rows, "W9b2", [], gates,
          {"verdict_notes": n_seg,
           "statuses": {s: sum(1 for v in vd.values() if v.get("status") == s)
                        for s in VERB}})
print("W9B2_NOTES|committed")
