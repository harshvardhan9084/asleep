#!/usr/bin/env python3
"""w9a2_notes.py — W9a2 (2026-11-10, B73): durable probe-verdict recording.

W9a round-2 probed the 168 BOOK_TRUNC leftovers (ckpt rebuilt post-reset #57;
B66's original verdicts were lost because they lived only in reset-volatile
work/ state). This wave makes the verdicts DURABLE: one page-cited segment per
probed entry appended to the row's notes (evidence surface; existing verbatim
content untouched, append-only per RULES §6b). Marker "W9a2 probe:" — the
auditor (v21) skips BOOK_TRUNC emission on `verified_complete @ <field>`
matches, so the recorded-honest drop survives future resets even without the
ckpt. Idempotent (segment-presence check). No primary-field writes; notes
only. T2T 0 (deterministic ckpt replay, no doc reads).
"""
import json
import sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

BASE = WC.BASE
CKPT = f"{BASE}/w9a_ckpt.json"
MARK = "W9a2 probe:"

ck = json.load(open(CKPT)).get("results", {})
rows = WC.load_rows()
by_id = {r["subject_id"]: r for r in rows}

VERB = {
    "verified_complete": "printed entry verified complete (verbatim print)",
    "print_garbled": "source print itself ends abruptly (print-faithful storage)",
    "corroborated_elsewhere": "same book printed in a different form elsewhere; row's own print not recoverable - stored form kept",
    "no_print_found": "no printed books-list entry recovered (text-layer + OCR + corpus index)",
    "sha_unresolved": "cited doc sha not locally resolvable - re-supply PDF to resume",
}

touched = {}
n_seg = 0
for key, v in sorted(ck.items()):
    sid, field = key.split("::", 1)
    r = by_id.get(sid)
    if r is None:
        continue
    st = v.get("status", "?")
    ev = (v.get("evidence") or "").strip()
    detail = VERB.get(st, st)
    if st == "no_print_found":
        try:
            detail += f", {int(v.get('pages_probed') or 0)} page(s) probed"
        except Exception:
            pass
    seg_field = f"{MARK} {st} @ {field}"
    seg = f"{seg_field} at {ev}" if ev else seg_field
    seg += f" — {detail}" if ev else f" — {detail}"
    old = r.get("notes", "") or ""
    if MARK in old and seg_field in old:
        continue  # idempotent: this entry's verdict already recorded
    r["notes"] = (old + " | " if old else "") + seg
    touched[sid] = r
    n_seg += 1

print(f"W9A2_NOTES|segments={n_seg}|rows={len(touched)}")

if not touched:
    print("W9A2_NOTES|nothing to do")
    sys.exit(0)

pre_rows_by_id = {r["subject_id"]: dict(r) for r in rows}
gates = WC.run_gates(rows, sorted(touched), pre_rows_by_id)
print("GATES|g1:", gates["g1"], "|g2:", gates["g2"], f"codes={gates['g2_codes']}",
      "|g3:", gates["g3"], "|g6:", gates["g6"], "|pre_hits:", gates["g6_pre_edit_hits"])
ok = all(gates[k] in (True, None) for k in ("g1", "g2", "g3", "g6"))
if not ok:
    print("WAVE_ABORT|gates failed")
    sys.exit(2)

WC.commit(rows, "W9a2", [], gates,
          {"probe_verdicts_recorded": n_seg, "rows": len(touched),
           "statuses": {s: sum(1 for v in ck.values() if v.get("status") == s)
                        for s in VERB}})
print("W9A2_NOTES|committed")
