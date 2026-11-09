#!/usr/bin/env python3
"""w10d_token_n_probe.py — W10d (2026-11-09): TOKEN_N_LOWER recorded-honest
adjudication. The audit's (n)+lowercase regex fires on printed inline
lecture-hour annotations ('(2) calendaring' = 2 printed lecture hours for that
topic) and academic notation ('LR(0) items') — AKTU prints per-topic lecture
hours inside unit text; several rows already carry wave notes documenting the
notation (coating-of-textiles, internet-java-programming, technology-of-dyeing-ii).

Probe: every flagged span (+/-40-char context) must be found verbatim
(normalized alphanumeric containment) in the cited source docs' text layers.
Rows with ALL spans verified get quality tag w10d_token_n_faithful_print + a
page-cited probe note — the recorded-honest class (B63/B71 precedent: auditor
v20 then skips evidence-recorded faithful prints). Rows with any unverified
span stay flagged (zero-guess, no tag). No primary-field writes. T2T 0
(deterministic; fitz text layers only).
"""
import json
import re
import sys

import fitz

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC
import audit_rules as AR

BASE = WC.BASE
CORPUS = json.load(open(f"{BASE}/corpus_map.json"))
PAT = re.compile(r"\(\d{1,2}\)\s+[a-z]")
TAG = "w10d_token_n_faithful_print"


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


rows = WC.load_rows()
pre_rows_by_id = {r["subject_id"]: dict(r) for r in rows}
flags = WC.load_flags()

targets = []
for sid, fl in flags.get("rows", {}).items():
    if any(f.get("rule") == "TOKEN_N_LOWER" for f in fl):
        targets.append(sid)
print(f"W10D|targets={len(targets)}")


_cache = {}


def doc_pages(sha):
    if sha in _cache:
        return _cache[sha]
    p = CORPUS.get(sha)
    pages = []
    if p:
        try:
            d = fitz.open(p)
            pages = [pg.get_text() or "" for pg in d]
            d.close()
        except Exception:
            pages = []
    _cache[sha] = pages
    return pages


def shas_for(r):
    out, seen = [], set()
    for col in ("source_syllabus", "source_history"):
        for m in re.finditer(r"#([0-9a-f]{12,16})", r.get(col, "") or ""):
            sha = m.group(1)
            if sha not in seen:
                seen.add(sha)
                out.append(sha)
    return out[:6]


n_ok = n_fail = 0
touched = set()
report = {}
for sid in targets:
    r = next((x for x in rows if x["subject_id"] == sid), None)
    if not r:
        continue
    hay = {}
    for c in AR.TEXT_FIELDS:
        v = r.get(c, "") or ""
        if v:
            hay[c] = v
    for col, i, t in AR.iter_book_strings(r):
        hay[f"{col}[{i}]"] = t
    spans = []
    for fld, text in hay.items():
        for m in PAT.finditer(text):
            ctx = text[max(0, m.start() - 40):m.end() + 40]
            spans.append((fld, ctx))
    shas = shas_for(r)
    evs, unverified = [], 0
    for fld, ctx in spans:
        nctx = norm(ctx)
        hit = None
        for sha in shas:
            pages = doc_pages(sha)
            for pi, pt in enumerate(pages):
                if nctx and nctx in norm(pt):
                    hit = f"{sha} pp.{pi+1}"
                    break
            if hit:
                break
        if hit:
            evs.append(f"{fld}@{hit}")
        else:
            unverified += 1
    if spans and unverified == 0:
        qf = [f for f in (r.get("quality_flags", "") or "").split(";") if f.strip()]
        if TAG not in qf:
            qf.append(TAG)
        r["quality_flags"] = ";".join(qf)
        ev_txt = f"{len(spans)}/{len(spans)} spans verified ({'; '.join(evs[:3])}{' …' if len(evs) > 3 else ''})"
        note = (f"W10d probe: {ev_txt} — (n)+lowercase spans verified verbatim in "
                f"cited docs (printed inline lecture-hour annotations / academic notation; faithful print, "
                f"RULES §6b evidence surfaces unchanged); TOKEN_N_LOWER recorded honest (audit v20 guard)")
        old = (r.get("notes", "") or "").strip()
        r["notes"] = (old + (" | " if old else "") + note).strip()
        touched.add(r["subject_id"])
        n_ok += 1
        report[sid] = {"spans": len(spans), "verdict": "faithful_print", "evidence": evs[:6]}
    else:
        n_fail += 1
        report[sid] = {"spans": len(spans), "verified": len(evs), "verdict": "stays_flagged(zero-guess)"}


print(json.dumps(report, indent=0, ensure_ascii=False)[:2800])
print(f"W10D|rows_ok={n_ok} rows_stay_flagged={n_fail} touched={len(touched)}")

gates = WC.run_gates(rows, touched, pre_rows_by_id)
print("GATES|" + json.dumps({k: (v if not isinstance(v, tuple) else v) for k, v in gates.items()}))
if not (gates["g1"] is None and gates["g2"] is None and gates["g3"] is None
        and gates["g6"] in (None, True)):
    print("W10D_ABORT|gates failed")
    sys.exit(2)
WC.commit(rows, "W10d", len(touched), gates,
          meta_extra={"wave": "W10d", "rows_tagged": n_ok, "rows_stay_flagged": n_fail,
                      "class": "TOKEN_N_LOWER recorded-honest (printed lecture-hour annotations/notation)",
                      "audit_version": "v20 guard"})
WC.refresh_flags_consumed({"TOKEN_N_LOWER": True, "__wave__": "W10d"})
print(f"W10D_APPLY|tagged={n_ok}|stay_flagged={n_fail}")
