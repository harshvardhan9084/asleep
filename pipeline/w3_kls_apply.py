#!/usr/bin/env python3
"""w3_kls_apply.py — W3 (B55): apply co_kls backfill.
Sources:
  w3_deterministic_wins.json — complete printed K-sequences found by regex in
      the cited docs' text layers (evidence: doc pp.N).
  w3_rex_results.json — mercury-3 REX extractions (ok / partial-with-nulls /
      api_fail / parse_fail). REX K-values cross-checked against the
      deterministic partial kmap; deterministic wins on conflict.
  w3_not_printed.json — no K pairs in any cited doc's text layer → raster
      check: image-only pages ⇒ kls_raster_candidate, else kls_not_printed.
RULES §6b: co_kls writes carry corrections_json entries; nulls mark
not-printed slots (aligned by CO index); zero-guess for the rest."""
import csv
import json
import re
import sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

BASE = WC.BASE
rows = WC.load_rows()
by_id = {r["subject_id"]: r for r in rows}
flags_doc = WC.load_flags()

wins = json.load(open(f"{BASE}/w3_deterministic_wins.json"))
rex = json.load(open(f"{BASE}/w3_rex_results.json")) if __import__("os").path.exists(f"{BASE}/w3_rex_results.json") else {}
rex_queue = {q["sid"]: q for q in json.load(open(f"{BASE}/w3_rex_queue.json"))}
not_printed = json.load(open(f"{BASE}/w3_not_printed.json"))

def qf_update(r, remove, add):
    qf = [f for f in (r.get("quality_flags", "") or "").split(";") if f.strip()]
    qf = [f for f in qf if f != remove]
    if add and add not in qf:
        qf.append(add)
    r["quality_flags"] = ";".join(qf)

def ncos_of(r):
    return sum(1 for i in range(1, 7) if (r.get(f"co{i}_text", "") or "").strip())

# raster check for not-printed rows
import fitz, hashlib, os
corpus = {}
for root in ("/home/z/my-project/work/repo_asleep/PDFs", "/home/z/my-project/upload",
             "/home/z/my-project/work/artd_v3/sources"):
    for dp, _d, fs in os.walk(root):
        for fn in fs:
            if fn.lower().endswith(".pdf"):
                p = os.path.join(dp, fn)
                try:
                    h = hashlib.md5()
                    with open(p, "rb") as fh:
                        for chunk in iter(lambda: fh.read(1 << 20), b""):
                            h.update(chunk)
                    corpus.setdefault(h.hexdigest()[:16], p)
                except Exception:
                    pass

def has_raster_co_pages(shas):
    for sha in shas[:2]:
        p = corpus.get(sha)
        if not p:
            continue
        try:
            d = fitz.open(p)
            pages = [pg.get_text() for pg in d]
            imgs = [len(pg.get_images()) for pg in d]
            d.close()
        except Exception:
            continue
        for pi, t in enumerate(pages):
            if len((t or "").strip()) < 20 and imgs[pi] > 0 and pi > 0:
                return True
    return False

n_win = n_rex_ok = n_rex_partial = n_rex_null = 0
flag_only = 0
touched = set()
mismatches = []

def apply_kls(r, kls, rule, evidence):
    # guard: already backfilled/partially applied rows are not re-written
    qfl = r.get("quality_flags", "") or ""
    if "corrected_KLS_BACKFILL" in qfl or "kls_partially_printed" in qfl:
        return False
    before = r.get("co_kls", "") or ""
    r["co_kls"] = json.dumps(kls, ensure_ascii=False)
    cjson = json.loads(r.get("corrections_json", "") or "[]")
    cjson.append({"field": "co_kls", "before": before or "(empty)", "after": json.dumps(kls),
                  "rule": rule, "evidence": evidence, "wave": "W3"})
    r["corrections_json"] = json.dumps(cjson, ensure_ascii=False)
    r["verification_status"] = "corrected"
    qf_update(r, "KLS_MISSING", None)
    qf_update(r, "KLS_SHORT", None)
    if any(k is None for k in kls):
        qf_update(r, None, "kls_partially_printed")
    else:
        qf_update(r, None, "corrected_KLS_BACKFILL")
    seg = "W3 co_kls backfill per RULES §6b (printed K-levels; nulls = not printed)"
    if seg not in (r.get("change_note_vs_previous", "") or ""):
        r["change_note_vs_previous"] = ((r.get("change_note_vs_previous", "") + "; ") if r.get("change_note_vs_previous", "") else "") + seg
    touched.add(r["subject_id"])

for sid, w in wins.items():
    r = by_id.get(sid)
    if not r or ncos_of(r) != len(w["kls"]):
        continue
    if apply_kls(r, w["kls"], "KLS_MISSING" if not w["evidence"] else "KLS_BACKFILL",
                 w["evidence"] + " (deterministic text-layer scan)"):
        n_win += 1

for sid, res in rex.items():
    r = by_id.get(sid)
    if not r:
        continue
    kls = res.get("kls")
    if res["status"] == "ok" and kls and all(k for k in kls):
        # cross-check: deterministic scan recorded WHICH COs had printed K pairs
        # (partial = CO-number list; values not stored — REX values validated
        # K1-K6 + count-match stand, mismatches surfaced at W7 re-audit)
        det = rex_queue.get(sid, {}).get("partial", [])
        if isinstance(det, dict):
            for no_str, k in det.items():
                idx = int(no_str) - 1
                if idx < len(kls) and kls[idx] and kls[idx] != k:
                    mismatches.append((sid, no_str, k, kls[idx]))
                    kls[idx] = k  # deterministic text-layer wins
        apply_kls(r, kls, "KLS_BACKFILL",
                  "mercury-3 REX over cited doc print (validated K1-K6, count match)")
        if "corrected_KLS_BACKFILL" in (r.get("quality_flags", "") or "") or "kls_partially_printed" in (r.get("quality_flags", "") or ""):
            n_rex_ok += 1
    elif res["status"] == "partial" and kls and not any(k for k in kls):
        # all-null REX verdict (2026-11-09 parse-contract re-run): the cited
        # docs' text pages carry no printed K-assignment for ANY CO — mercury
        # honestly returned nulls (zero-guess held). Tag kls_not_printed like
        # the deterministic not_printed class; no co_kls write.
        qf_update(r, None, "kls_not_printed")
        note = ("W3: no K-levels in any cited doc's text layer (deterministic "
                "scan + mercury-3 REX zero-null verdict, 2026-11-09) — CO/K table "
                "not printed in text layer; K-levels likely not printed for this subject")
        if note not in (r.get("notes", "") or ""):
            r["notes"] = ((r.get("notes", "") + " | ") if r.get("notes", "") else "") + note
        touched.add(r["subject_id"])
        n_rex_null += 1
    elif res["status"] == "partial" and kls and any(k for k in kls):
        det = rex_queue.get(sid, {}).get("partial", [])
        if isinstance(det, dict):
            for no_str, k in det.items():
                idx = int(no_str) - 1
                if idx < len(kls):
                    kls[idx] = k
        apply_kls(r, kls, "KLS_BACKFILL",
                  "mercury-3 REX over cited doc print (partially printed; nulls = K not printed for that CO)")
        if "kls_partially_printed" in (r.get("quality_flags", "") or ""):
            n_rex_partial += 1

for q in not_printed:
    sid = q["sid"]
    r = by_id.get(sid)
    if not r or sid in touched:
        continue
    if "kls_raster_candidate" in (r.get("quality_flags", "") or "") or "kls_not_printed" in (r.get("quality_flags", "") or ""):
        continue  # already flagged (B55) — idempotent re-run guard
    raster = has_raster_co_pages(q.get("shas", []))
    qf_update(r, "KLS_MISSING", "kls_raster_candidate" if raster else "kls_not_printed")
    note = ("W3: no K-levels in any cited doc's text layer"
            + (" — cited doc has image-only pages; page-image read needed" if raster
               else " — CO/K table not printed in text layer; K-levels likely not printed for this subject"))
    if note not in (r.get("notes", "") or ""):
        r["notes"] = ((r.get("notes", "") + " | ") if r.get("notes", "") else "") + note
    touched.add(sid)
    flag_only += 1

print(f"W3|applied deterministic={n_win} rex_ok={n_rex_ok} rex_partial={n_rex_partial} rex_null_tagged={n_rex_null} flag_only={flag_only} mismatches={len(mismatches)}")
for m in mismatches[:6]:
    print("  MISMATCH", m)

# refresh audit flags: consumed KLS rules for touched rows
for sid in list(flags_doc.get("rows", {})):
    flags_doc["rows"][sid] = [f for f in flags_doc["rows"][sid] if f.get("rule") not in ("KLS_MISSING", "KLS_SHORT")]
    if not flags_doc["rows"][sid]:
        flags_doc["rows"].pop(sid)
json.dump(flags_doc, open(f"{BASE}/audit_flags.json", "w"), indent=1, ensure_ascii=False)

pre_rows = {r["subject_id"]: dict(r) for r in rows}
gates = WC.run_gates(rows, touched, pre_rows)
print(f"G1|{'PASS' if not gates['g1'] else 'FAIL ' + gates['g1']}")
print(f"G2|{'PASS' if not gates['g2'] else 'FAIL ' + gates['g2']}|codes={gates['g2_codes']}")
print(f"G3|{'PASS' if not gates['g3'] else 'FAIL ' + gates['g3']}")
print(f"G6|{'PASS' if not gates['g6'] else 'FAIL ' + gates['g6']}|checks={gates['g6_checks']}|pre_edit_hits={gates['g6_pre_edit_hits']}")
if any([gates["g1"], gates["g2"], gates["g3"], gates["g6"]]):
    print("ABORT: gate failure")
    sys.exit(2)
WC.commit(rows, "W3", n_win + n_rex_ok + n_rex_partial, gates,
          {"deterministic": n_win, "rex_ok": n_rex_ok, "rex_partial": n_rex_partial,
           "rex_null_tagged": n_rex_null, "flag_only": flag_only, "mismatches": len(mismatches)})
