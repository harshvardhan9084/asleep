#!/usr/bin/env python3
"""w10f_locator_reprobe.py — W10f (B79): TYPE_EMPTY locator repair re-probe.

B76's durable no_code_print_found verdicts are partially FALSE: codes with
5+ letter prefixes (BMBAI304, RMBI MK08, BMBAOM04) escape the w10c2 variant
regex ^([A-Z]{2,4})(\\d{3}[A-Z]?)$ — the cited scheme pages DO print these
codes (verified B79: 4/4 sampled rows' codes print, e.g. BMBAI304 @
mba_business-analytics_y2_syllabus_2025-26.pdf#89395bea p.8).

This wave re-probes every TYPE_EMPTY row (subject_type still empty) with:
  locator  — token-concat match: windows of 1-3 adjacent whitespace tokens,
             punctuation-stripped squash equality, shape-guarded (first token
             letters-only; middle tokens letters-only; last token carries the
             digit tail) so scheme-table number columns cannot concat-fake a
             code.
  grammar  — the COMMITTED B74/B76 header grammar, unchanged: standalone
             whitelisted section header above the hit (MAX_GAP=8 lines),
             wrap-continuation rejection, table-column-header isolation,
             semester-break rejection, differing-intervening-header rejection
             (the exact B76 discriminator set from w10c2_adjudicate_apply).

Verdicts (ckpt w10f_ckpt.json):
  print_category       — >=1 surviving header page; ALL surviving agree;
                         category in WRITEABLE vocab            -> write
  conflicting_headers  — survivors disagree or category outside vocab
  code_found_no_header — code prints (pages listed) but no governing header
  code_really_absent   — token-concat locator also finds nothing
  no_primary_code      — 34 rows without any code (stay)

Notes: append-only "W10f probe:" segments ONLY where the W10f verdict differs
from the W10c2 durable record (locator repair) — keeps the CSV diff tight.
Writes mirror the W10c2 apply contract exactly (subject_type + norm +
corrections_json {before,after,rule:TYPE_EMPTY,wave:W10f} + verification_
status=corrected + corrected_W10F_LOCATOR tag + change_note). Gates
G1/G2/G3/G6 via wave_commit (caller pushes). T2T 0. No rr_sid; no keys.
"""
import json
import os
import re
import sys

import fitz

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC
from w10c2_fulldoc_probe import (corpus_map_load, HEADERS, HONOR_RE,
                                 WRITEABLE)

BASE = WC.BASE
MARK = "W10f probe:"
CKPT = f"{BASE}/w10f_ckpt.json"

COL_TOKENS = re.compile(r"^(s\.?\s*no\.?|sr\.?\s*no\.?|subject|code|subject\s+code|"
                        r"subject\s+name|name|periods?|sessional|evaluation\s+scheme|"
                        r"scheme|credit|ct|ta|te|pe|ps|ese|total|l|t|p)$", re.I)
SEM_BREAK = re.compile(r"\bsemeste?r\b", re.I)

WRAP_WORDS = {"science", "based", "open", "deptt", "departmental", "department",
              "elective", "electives", "professional", "value", "added",
              "mandatory", "practical", "core", "cores", "lab", "labs"}
MAX_GAP = 8

# ---------------------------------------------------------------- locator
def code_token_hits(text, pc_sq):
    """[(char_pos, n_tokens)] where 1-3 adjacent alnum tokens concat-squash
    exactly to pc_sq, shape-guarded against scheme number columns."""
    toks = [(m.group(0), m.start()) for m in re.finditer(r"[A-Za-z0-9]+", text)]
    out = []
    n = len(toks)
    for i in range(n):
        t0 = toks[i][0]
        acc = t0.lower()
        if len(pc_sq) >= 5 and re.sub(r"[^a-z0-9]", "", acc) == pc_sq:
            out.append((toks[i][1], 1))   # exact single-token equality (any shape)
            continue
        if not re.fullmatch(r"[A-Za-z]{2,8}", t0):
            continue
        for w in (2, 3):
            if i + w > n:
                break
            tm = toks[i + w - 1][0].lower()
            if w == 2:
                if not re.fullmatch(r"[a-z]{0,4}\d{2,3}[a-z]?", tm):
                    break
            else:
                if not re.fullmatch(r"[a-z]{1,6}", toks[i + 1][0].lower()) or \
                   not re.fullmatch(r"[a-z]{0,4}\d{1,3}[a-z]?", tm):
                    break
            acc = "".join(x[0].lower() for x in toks[i:i + w])
            if acc == pc_sq:
                out.append((toks[i][1], w))
                break
            if not pc_sq.startswith(acc):
                break
    return out


# ------------------------------------------------- committed grammar (copy)
def governing_header_pos(text, pos):
    """B76-tight governing header above pos: whitelisted standalone line,
    gap<=8 lines, wrap-continuation rejected. Returns (cat, hpos, why)."""
    up = text[:pos]
    lines = up.splitlines()
    code_ln = len(lines) - 1
    best, best_ln = None, -1
    off = 0
    best_off = -1
    for i, ln in enumerate(lines):
        s = ln.strip()
        for hre, cat in HEADERS:
            if hre.match(s) and not HONOR_RE.match(s):
                best, best_ln, best_off = cat, i, off + ln.find(s)
        off += len(ln) + 1
    if best is None:
        return None, -1, None
    if code_ln - best_ln > MAX_GAP:
        return None, best_off, f"gap {code_ln - best_ln} lines"
    prev = next((l.strip() for l in reversed(lines[:best_ln]) if l.strip()), "")
    if prev:
        last = re.split(r"[^A-Za-z]+", prev)[-1].lower() if re.search(r"[A-Za-z]", prev) else ""
        if last in WRAP_WORDS:
            return None, best_off, f"wrap-continuation (prev line ends '{last}')"
    return best, best_off, None


def page_category(t, pos):
    """full B76 chain on one hit: header + 3 discriminators."""
    cat, hpos, why = governing_header_pos(t, pos)
    if cat is None:
        return None, why or "no governing header"
    between = t[hpos:pos]
    toks = set()
    for ln in between.splitlines():
        s = ln.strip()
        if s and COL_TOKENS.match(s):
            toks.add(s.lower())
    if len(toks) >= 3:
        return None, f"table column-header starts between header and code ({','.join(sorted(toks))[:5]})"
    if SEM_BREAK.search(between):
        return None, "semester break between header and code"
    inter = [(s, c) for ln in between.splitlines()
             for s in [ln.strip()]
             for hre, c in HEADERS if hre.match(s) and not HONOR_RE.match(s)]
    diff = [x for x in inter if x[1] != cat]
    if diff:
        return None, f"differing intervening header {diff[0][0]!r}->{diff[0][1]}"
    return cat, None


# ---------------------------------------------------------------- main
def main():
    smoke = os.environ.get("W10F_SMOKE", "") == "1"
    rows = WC.load_rows()
    by_id = {r["subject_id"]: r for r in rows}
    fl = json.load(open(f"{BASE}/audit_flags.json"))["rows"]
    prev_ck = {}
    if os.path.exists(f"{BASE}/w10c2_ckpt.json"):
        prev_ck = json.load(open(f"{BASE}/w10c2_ckpt.json")).get("results", {})
    corpus = corpus_map_load()

    targets = [sid for sid, lst in fl.items()
               if any(x["rule"] == "TYPE_EMPTY" for x in lst)
               and not (by_id[sid].get("subject_type") or "").strip()]
    if smoke:
        targets = targets[:6]
    print(f"W10F|targets={len(targets)}", flush=True)

    _docs = {}
    def doc_pages(path):
        if path not in _docs:
            try:
                d = fitz.open(path)
                _docs[path] = [(i + 1, d[i].get_text() or "") for i in range(d.page_count)]
                d.close()
            except Exception:
                _docs[path] = []
        return _docs[path]

    def resolve(sha):
        if sha in corpus:
            return corpus[sha]
        pre = [k for k in corpus if k.startswith(sha)]
        return corpus[pre[0]] if pre else None

    results = {}
    if os.path.exists(CKPT) and os.environ.get("W10F_RESUME", "") == "1":
        try:
            results = json.load(open(CKPT))
            print(f"W10F|resume: {len(results)} verdicts loaded", flush=True)
        except Exception:
            results = {}
    todo = [s for s in targets if s not in results]
    for idx, sid in enumerate(todo):
        r = by_id[sid]
        pc = (r.get("primary_code") or "").strip().upper()
        if not pc:
            results[sid] = {"status": "no_primary_code", "evidence": ""}
            continue
        pc_sq = re.sub(r"[^a-z0-9]", "", pc.lower())
        shas, seen = [], set()
        for col in ("source_syllabus", "source_history"):
            for m in re.finditer(r"#([0-9a-f]{12,16})", r.get(col, "") or ""):
                if m.group(1) not in seen:
                    seen.add(m.group(1))
                    shas.append(m.group(1))
        unresolved, found, catpages, rejected = [], [], [], []
        for sha in shas[:6]:
            path = resolve(sha)
            if not path or not os.path.exists(path):
                unresolved.append(sha)
                continue
            base = os.path.basename(path)
            docpages = doc_pages(path)
            sha_catpages, sha_plain = [], []
            for pno, t in docpages:
                hits = code_token_hits(t, pc_sq)
                if not hits:
                    continue
                found.append(f"{base}#{sha} p.{pno}")
                cat, why = page_category(t, hits[0][0])
                if cat:
                    sha_catpages.append((pno, cat))
                elif why and why != "no governing header":
                    rejected.append(f"p.{pno}: {why}")
                else:
                    sha_plain.append(pno)
            catpages += [(sha, base, p, c) for (p, c) in sha_catpages]
        if not found and not catpages:
            if unresolved and len(unresolved) == len(shas):
                results[sid] = {"status": "sha_unresolved", "evidence": ",".join(unresolved)}
            else:
                results[sid] = {"status": "code_really_absent", "evidence": ""}
            continue
        cats = sorted({c for (_s, _b, _p, c) in catpages})
        ev_h = "; ".join(f"{b}#{s} p.{p}->{c}" for (s, b, p, c) in catpages)
        if len(cats) == 1 and cats[0] in WRITEABLE:
            results[sid] = {"status": "print_category", "category": cats[0],
                            "evidence": ev_h,
                            "plain_pages": [e for e in found if e not in ev_h][:4]}
        elif len(cats) > 1:
            results[sid] = {"status": "conflicting_headers", "evidence": ev_h}
        elif cats:
            results[sid] = {"status": "conflicting_headers",
                            "evidence": ev_h + " (category outside writeable vocab)"}
        else:
            results[sid] = {"status": "code_found_no_header",
                            "evidence": "; ".join(found[:6]),
                            "rejected_headers": rejected[:6]}
        if unresolved:
            results[sid]["unresolved_shas"] = ",".join(unresolved)
        if (idx + 1) % 15 == 0:
            json.dump(results, open(CKPT, "w"), indent=1)
            print(f"W10F|{idx + 1}/{len(todo)} done", flush=True)

    json.dump(results, open(CKPT, "w"), indent=1)
    from collections import Counter
    st = Counter(v["status"] for v in results.values())
    print(f"W10F_PROBE|done={len(results)}|{dict(st)}")

    # ---------------- apply (mirror w10c2/w10c contract) ----------------
    n_notes = n_writes = 0
    touched = {}
    prev_status = lambda s: (prev_ck.get(s) or {}).get("status")
    for sid, v in results.items():
        r = by_id.get(sid)
        if r is None:
            continue
        st_old = prev_status(sid)
        flipped = (st_old is None) or (st_old != v["status"])
        seg = ""
        if flipped or v["status"] == "print_category":
            ev = (v.get("evidence") or "").strip()
            cat = f" -> {v['category']}" if v.get("category") else ""
            core = f"{MARK} {v['status']}{cat}"
            if v["status"] == "code_really_absent":
                core += " (cited docs full text layer, token-concat locator)"
            if v["status"] == "code_found_no_header" and st_old == "no_code_print_found":
                core += " (corrects W10c2 locator: code prints)"
            if v["status"] == "print_category" and st_old in ("no_header_above", "no_code_print_found"):
                core += " (new pages via token-concat locator)"
            seg = f"{core} at {ev}" if ev else core
        if seg and seg[:80] not in (r.get("notes", "") or ""):
            old = r.get("notes", "") or ""
            r["notes"] = (old + " | " if old else "") + seg
            n_notes += 1
        if v["status"] == "print_category":
            if (r.get("subject_type") or "").strip():
                continue
            cat = v["category"]
            r["subject_type"] = cat
            r["subject_type_norm"] = cat
            cjson = json.loads(r.get("corrections_json") or "[]")
            if not any(e.get("rule") == "TYPE_EMPTY" and e.get("after") == cat
                       for e in cjson):
                cjson.append({"field": "subject_type", "before": "", "after": cat,
                              "rule": "TYPE_EMPTY",
                              "evidence": f"printed governing section header at {v.get('evidence','')} "
                                          "(token-concat locator repair; B76 grammar chain)",
                              "wave": "W10f"})
                r["corrections_json"] = json.dumps(cjson, ensure_ascii=False)
            r["verification_status"] = "corrected"
            qf = [f for f in (r.get("quality_flags", "") or "").split(";") if f.strip()]
            if "corrected_W10F_LOCATOR" not in qf:
                qf.append("corrected_W10F_LOCATOR")
            r["quality_flags"] = ";".join(qf)
            note = "W10f(TYPE_EMPTY): subject_type set from printed scheme section header per RULES §6b — locator repair, print evidence page-cited in corrections_json"
            if note not in (r.get("change_note_vs_previous", "") or ""):
                prevn = r.get("change_note_vs_previous", "") or ""
                r["change_note_vs_previous"] = (prevn + "; " if prevn else "") + note
            touched[sid] = r
            n_writes += 1

    print(f"W10F_APPLY|writes={n_writes}|note_rows={n_notes}")
    pre_rows_by_id = {r["subject_id"]: dict(r) for r in rows}
    gates = WC.run_gates(rows, sorted(touched), pre_rows_by_id)
    print("GATES|g1:", gates["g1"], "|g2:", gates["g2"], f"codes={gates['g2_codes']}",
          "|g3:", gates["g3"], "|g6:", gates["g6"], "|pre_hits:", gates["g6_pre_edit_hits"])
    ok = all(gates[k] in (True, None) for k in ("g1", "g2", "g3", "g6"))
    if not ok:
        print("WAVE_ABORT|gates failed")
        return 2
    WC.commit(rows, "W10f", n_writes, gates,
              {"writes": n_writes, "note_rows": n_notes,
               "verdicts": dict(Counter(v["status"] for v in results.values()))})
    print("W10F_APPLY|committed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
