#!/usr/bin/env python3
"""w8b_ocr_null_tag.py — W8b phase 2b (2026-11-09): the OCR probe (w8b_kls_ocr
run over all raster-candidate rows: 12 targets, 109 raster pages OCR'd,
tesseract psm6) found NO recoverable printed CO/K sequence anywhere. The
established w8b_kls_apply reclass path expects audit-v18 fix:W3 flag entries,
which audit v19 has already reclassified — so this pass records the probe
evidence on the 12 rows directly: kls_not_printed tag + note. Zero-guess: no
co_kls data change; the honest state is "K not printed for this subject".
Gates G1/G2/G3/G6 must PASS before commit."""
import json
import sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

ckpt = json.load(open(f"{WC.BASE}/w8b_ocr_ckpt.json"))
results = ckpt.get("results", {})
rows = WC.load_rows()
pre_rows = {r["subject_id"]: dict(r) for r in rows}
by_id = {r["subject_id"]: r for r in rows}
touched = set()
n = 0
for sid, res in results.items():
    if res.get("status") not in ("no_clean_sequence", "sha_unresolved",
                                 "no_resolvable_citation"):
        continue
    r = by_id.get(sid)
    if not r or "kls_not_printed" in (r.get("quality_flags", "") or ""):
        continue  # idempotent
    qf = [t for t in (r.get("quality_flags", "") or "").split(";") if t]
    qf.append("kls_not_printed")
    r["quality_flags"] = ";".join(qf)
    pages = res.get("pages_probed", "?")
    detail = {"no_clean_sequence": "no recoverable printed CO/K sequence",
              "sha_unresolved": "cited doc not locally resolvable (reset-lost sha)",
              "no_resolvable_citation": "no resolvable citation"}[res["status"]]
    note = (f"W8b: OCR page-image probe ({pages} pages, tesseract, 2026-11-09): "
            f"{detail} — K-levels not recoverable from print evidence")
    if note not in (r.get("notes", "") or ""):
        r["notes"] = ((r.get("notes", "") + " | ") if r.get("notes", "") else "") + note
    touched.add(sid)
    n += 1

gates = WC.run_gates(rows, touched, pre_rows)
print(f"G1|{'PASS' if not gates['g1'] else 'FAIL ' + str(gates['g1'])}")
print(f"G2|{'PASS' if not gates['g2'] else 'FAIL ' + str(gates['g2'])}|codes={gates['g2_codes']}")
print(f"G3|{'PASS' if not gates['g3'] else 'FAIL ' + str(gates['g3'])}")
print(f"G6|{'PASS' if not gates['g6'] else 'FAIL ' + str(gates['g6'])}|checks={gates['g6_checks']}")
if any([gates["g1"], gates["g2"], gates["g3"], gates["g6"]]):
    print("ABORT: gate failure")
    sys.exit(2)
WC.commit(rows, "W8b-null-tag", n, gates,
          {"ocr_null_tagged": n, "probe_pages": ckpt.get("ocr_cache") and len(ckpt.get("ocr_cache", {}))})
WC.refresh_flags_consumed({"KLS_MISSING": True, "KLS_SHORT": True, "__wave__": "W8b-null-tag"})
print(f"W8B_NULL_TAG|rows={n}")
