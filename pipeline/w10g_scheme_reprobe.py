#!/usr/bin/env python3
"""w10g_scheme_reprobe.py — B80 wave: W10g scheme-invariant round-3 re-probe
with header-mapped column extraction.

Applies the B79 lesson (w10c2 verdicts were partially false from locator
blindness) to the W9b scheme-invariant classes: CREDIT_FORMULA / SESS_SUM /
MARKS_SUM (269 rows still flagged after B75: 198 no_print_found +
71 stored_matches_no_print).

W9b's probe had no column mapping: it concatenated line-window numbers and
compared multisets, so a governing print that AGREES with storage but leaves
the total/credit cell blank (or prints 'NC' for a non-credit mandatory
course) could never yield accepted-print, and dual-code title blocks
(KNC501/ KNC502) killed the row capture outright.

W10g extraction (hardened):
  1. page.find_tables() cell-grid extraction, code anchored CELL-level
     (numbers = numeric cells right of the code cell — SN/title excluded);
  2. HEADER-mapped columns: L T P / CT TA Total(sessional) / PS TE PE
     (end-sem) / Total(grand) / Credit mapped by header tokens per table;
  3. newest-print-wins (RULES §3): scheme_docs() order (primary/newest
     first) is the governing order; older-session conflicts recorded in the
     note, never silently ignored;
  4. line-window fallback (dual-code-safe, whitespace-neutral) only where
     find_tables yields nothing.

Verdicts (per row, over ALL mapped candidates of the governing doc):
  accepted-print — every failed-invariant field print-verified: mapped print
                   value == stored, or print states NC/blank for credit with
                   stored 0 (non-credit mandatory courses), or print leaves
                   total blank while the stated components agree with
                   storage. Durable note 'W10g probe: accepted-print @ ...'
                   + audit v25 scan-side drop (v22 semantics).
  fixed          — mapped print value DIFFERS from stored on flagged-invariant
                   fields and the mapped repair satisfies ALL invariants
                   (scheme line proves the extraction error, §6b(4));
                   unique across governing candidates.
  keep           — no_print_found / ambiguous / conflicting rows, with
                   docs_tried + printed rows recorded in the durable note.

Deterministic fitz text layer only; zero T2T; resumable ckpt (W10G_RESUME).
"""
import argparse
import json
import os
import re
import sys
import time
from collections import Counter

import fitz

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC
import w9b_scheme_adjudicate as W9B
from w9b_scheme_adjudicate import (FIELDS, stored_vector, failed_invariants,
                                   parse_primary_quote, scheme_docs, resolve)

BASE = WC.BASE
CKPT = f"{BASE}/w10g_ckpt.json"
FLAGS = f"{BASE}/audit_flags.json"
MARK = "W10g probe:"
RULES3 = ("CREDIT_FORMULA", "SESS_SUM", "MARKS_SUM")
RULE2FIELD = {"CREDIT_FORMULA": "credit", "SESS_SUM": "sessional_total",
              "MARKS_SUM": "total_marks"}
BUDGET_S = float(os.environ.get("W10G_BUDGET", "1500"))

_doc_docs = {}
_tbl_cache = {}   # (sha, pno) -> [ {cells, pmap} ]
_line_cache = {}  # (sha, pno) -> [lines]
NUMCELL = re.compile(r"^\d{1,4}(?:\.\d+)?$")
HDR_TOKENS = {"l", "t", "p", "ct", "ta", "ese", "ps", "te", "pe", "total",
              "credit", "periods", "evaluation", "end semester", "scheme"}
NONCREDIT = re.compile(r"^\s*(?:NC|N\.C\.?|Non[- ]?Credit|NIL)\s*$", re.I)


def doc_open(sha, path):
    if sha not in _doc_docs:
        try:
            _doc_docs[sha] = fitz.open(path)
        except Exception:
            _doc_docs[sha] = None
    return _doc_docs[sha]


def _norm_cell(c):
    if isinstance(c, (list, tuple)):
        c = " ".join(str(x) for x in c if x)
    elif c is not None and not isinstance(c, str):
        c = str(c)
    return re.sub(r"\s+", " ", (c or "").replace("\n", " ")).strip()


def _header_map(grid, hit_i):
    """map column indices -> field names using the NEAREST header block above
    hit_i (multi-semester pages repeat the header per semester block)"""
    hdr_rows = []
    h = None
    for ri in range(hit_i - 1, -1, -1):
        cells = [_norm_cell(c).lower() for c in grid[ri]]
        hits = sum(1 for c in cells if c in HDR_TOKENS)
        if hits >= 2:
            h = ri
            break
    if h is None:
        return {}
    hdr_rows.append([_norm_cell(c).lower() for c in grid[h]])
    if h - 1 >= 0:
        cells = [_norm_cell(c).lower() for c in grid[h - 1]]
        if sum(1 for c in cells if c in HDR_TOKENS) >= 2:
            hdr_rows.insert(0, cells)   # group-header row above the token row
    if not hdr_rows:
        return {}
    ncol = len(grid[hit_i])
    coltok = [[] for _ in range(ncol)]
    for cells in hdr_rows:
        for ci in range(min(ncol, len(cells))):
            if cells[ci]:
                coltok[ci].append(cells[ci])
    # collapse merged spans: a None cell under a spanning header inherits it
    pmap = {}
    idx = {"L": None, "T": None, "P": None, "ct": None, "ta": None,
           "stt": None, "end": [], "tm": None, "credit": None}
    for ci, toks in enumerate(coltok):
        joined = " ".join(toks)
        if any(t == "ct" for t in toks):
            idx["ct"] = ci
        elif any(t == "ta" for t in toks):
            idx["ta"] = ci
        elif any(t == "credit" for t in toks):
            idx["credit"] = ci
        elif any(t == "total" for t in toks):
            # sessional Total sits with CT/TA block; grand Total elsewhere
            if idx["ct"] is not None and idx["stt"] is None and ci > idx["ct"]:
                idx["stt"] = ci
            elif idx["tm"] is None:
                idx["tm"] = ci
        if any(t == "l" for t in toks):
            idx["L"] = ci
        elif any(t == "t" for t in toks) and "total" not in joined \
                and not any(t == "ta" for t in toks):
            idx["T"] = ci
        elif any(t == "p" for t in toks) and "pe" not in toks and "ps" not in toks:
            idx["P"] = ci
        if any(t in ("ps", "te", "pe", "ese") for t in toks):
            idx["end"].append(ci)
    if idx["ct"] is None or idx["ta"] is None:
        return {}
    if idx["stt"] is None:
        # sessional Total = column right after TA within the CT block
        idx["stt"] = idx["ta"] + 1
    m = {"sessional_ct": idx["ct"], "sessional_ta": idx["ta"],
         "sessional_total": idx["stt"]}
    if idx["end"]:
        m["_end_cols"] = idx["end"]
    if idx["tm"] is not None:
        m["total_marks"] = idx["tm"]
    if idx["credit"] is not None:
        m["credit"] = idx["credit"]
    if idx["L"] is not None:
        m["L"] = idx["L"]
    if idx["T"] is not None:
        m["T"] = idx["T"]
    if idx["P"] is not None:
        m["P"] = idx["P"]
    return m


def _cell_val(c):
    cs = _norm_cell(c)
    if not cs:
        return None
    sq = re.sub(r"\s+", "", cs)
    if NUMCELL.match(sq):
        return float(sq)
    if NONCREDIT.match(cs):
        return "NC"
    return None


def _table_hits(sha, pno, page, codes, csq):
    key = (sha, pno)
    if key not in _tbl_cache:
        out = []
        try:
            tabs = page.find_tables()
            for tb in tabs.tables:
                try:
                    out.append(tb.extract())
                except Exception:
                    pass
        except Exception:
            pass
        _tbl_cache[key] = out
    hits = []
    for grid in _tbl_cache[key]:
        hit_i = hit = None
        for ci, cell in enumerate(grid):
            cs0 = _norm_cell(cell)
            if not cs0:
                continue
            cs = re.sub(r"[^A-Za-z0-9]", "", cs0).upper()
            k = next((k for k in csq if k in cs), None)
            if k:
                hit_i, hit = ci, k
                break
        if hit_i is None:
            continue
        cmap = _header_map(grid, hit_i)
        pmap = {}
        for f, ci in cmap.items():
            if f.startswith("_") or ci is None or ci >= len(grid[hit_i]):
                continue
            pmap[f] = _cell_val(grid[hit_i][ci])
        if "_end_cols" in cmap:
            for ci in cmap["_end_cols"]:
                if ci < len(grid[hit_i]):
                    v = _cell_val(grid[hit_i][ci])
                    if isinstance(v, float):
                        pmap.setdefault("ese_te_pe", v)
                        break
        # NC anywhere in the row (fullmatch-safe: titles/codes never match)
        # -> print states non-credit
        if pmap.get("credit") is None:
            for cell in grid[hit_i]:
                if NONCREDIT.match(_norm_cell(cell) or "x"):
                    pmap["credit"] = "NC"
                    break
        nums = [v for v in (pmap.get(f) for f in
                            ("L", "T", "P", "sessional_ct", "sessional_ta",
                             "sessional_total", "ese_te_pe", "total_marks"))
                if isinstance(v, float)]
        rowtext = " | ".join(_norm_cell(c) for c in grid if _norm_cell(c))[:220]
        hits.append({"page": pno + 1, "nums": nums, "rowtext": rowtext,
                     "hit": csq[hit], "via": "table", "pmap": pmap})
    return hits


def row_candidates_tables(sha, d, codes):
    csq = {re.sub(r"[^A-Z0-9]", "", c.upper()): c for c in codes if c}
    csq = {k: v for k, v in csq.items() if len(k) >= 5}
    out = []
    for pno in range(d.page_count):
        out.extend(_table_hits(sha, pno, d[pno], codes, csq))
    out = [h for h in out if len(h["nums"]) >= 4]
    return out


def code_strip_re(code):
    ch = [c for c in code.upper() if c.isalnum()]
    if not ch:
        return None
    return re.compile(r"[A-Z0-9]?".join(re.escape(c) for c in ch))


def row_candidates_lines(sha, d, codes):
    """fallback line-window capture (no header mapping; multiset path only)"""
    csq = {re.sub(r"[^A-Z0-9]", "", c.upper()): c for c in codes if c}
    csq = {k: v for k, v in csq.items() if len(k) >= 5}
    strip_res = {re.sub(r"[^A-Z0-9]", "", c.upper()): code_strip_re(c)
                 for c in codes if c}
    out = []
    for pno in range(d.page_count):
        key = (sha, pno)
        if key not in _line_cache:
            txt = d[pno].get_text() or ""
            _line_cache[key] = txt.splitlines() if txt.strip() else []
        lines = _line_cache[key]
        for li, ln in enumerate(lines):
            sq = re.sub(r"[^A-Za-z0-9]", "", ln).upper()
            hit = next((k for k in csq if k in sq), None)
            if not hit:
                continue
            buf = [ln]
            nums_seen = 0
            for nxt in lines[li + 1:li + 12]:
                nsq = re.sub(r"[^A-Za-z0-9]", "", nxt).upper()
                if any(k in nsq for k in csq):
                    if nums_seen >= 4:
                        break
                    buf.append(nxt)
                    continue
                if re.fullmatch(r"\s*(?:Total|TOTAL)\s*", nxt or " "):
                    break
                if "*" in nxt:
                    break
                nd = re.findall(r"\d+(?:\.\d+)?", nxt)
                if nd:
                    buf.append(nxt)
                    nums_seen += len(nd)
                    continue
                if not nxt.strip():
                    continue
                if nums_seen < 4 and len(nxt.strip()) <= 60:
                    buf.append(nxt)
                    continue
                break
            rowtxt = " ".join(buf)
            rowtxt = re.sub(r"^\s*(?:SN)?\d{1,2}\s*[\.\|]\s*", "", rowtxt.strip())
            for k, rx in strip_res.items():
                if rx:
                    rowtxt = rx.sub(" ", rowtxt)
            rowtxt = re.sub(r"\d+(?:\.\d+)?\s*(?:Hr|HR|hr)\b", " ", rowtxt)
            nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", rowtxt)]
            if len(nums) >= 4:
                out.append({"page": pno + 1, "nums": nums,
                            "rowtext": re.sub(r"\s+", " ", rowtxt).strip()[:220],
                            "hit": csq[hit], "via": "lines", "pmap": {}})
    return out


def invariants_of(v):
    return set(failed_invariants({k: v.get(k) for k in FIELDS}))


def mapped_verdict(st, failed, cands):
    """verdict from header-mapped candidates (all from ONE governing doc).
    Returns (status, detail) with status in accepted-print/fixed/ambiguous."""
    if not cands:
        return None
    # conflicting mapped values across candidates of this doc -> ambiguous
    conflict = False
    key_fields = ("credit", "sessional_total", "total_marks", "sessional_ct",
                  "sessional_ta", "ese_te_pe")
    for f in key_fields:
        vals = {c["pmap"].get(f) for c in cands if c["pmap"].get(f) is not None}
        if len(vals) > 1:
            conflict = True
    if conflict:
        return ("ambiguous", "mapped print values conflict within the governing doc")

    # merge: first non-None mapped value per field
    merged = {}
    for c in cands:
        for f, v in c["pmap"].items():
            if v is not None and f not in merged and f in (list(FIELDS) + ["credit"]):
                merged[f] = v

    # repair check FIRST: mapped print values that differ from storage on
    # flagged-invariant fields (scheme line proves the extraction error).
    # B80 evidence standard: numeric header-mapped values ONLY — no emptying
    # (blank-cell semantics need the printed column header prose, and the
    # line-window audits showed adjacent-row digit bleed), page-cited.
    repair = {}
    for f in ("credit", "sessional_ct", "sessional_ta", "sessional_total",
              "ese_te_pe", "total_marks"):
        pv = merged.get(f)
        if isinstance(pv, float) and st[f] is not None \
                and abs(pv - st[f]) > 0.01:
            repair[f] = pv
    if repair:
        trial = dict(st)
        for f, v in repair.items():
            trial[f] = v
        if not invariants_of(trial):
            if all(f in ("credit", "sessional_ct", "sessional_ta",
                         "sessional_total", "ese_te_pe", "total_marks")
                   for f in repair):
                return ("fixed", {"fields": repair, "cand": cands[0]})
        return ("keep", f"mapped print differs ({repair}) but repair does not satisfy all invariants")

    # accepted-print: every failed field print-verified
    ok = True
    for f in failed:
        pv = merged.get(f)
        if f == "credit":
            if pv == "NC" and st[f] == 0:
                continue
            if isinstance(pv, float) and st[f] is not None \
                    and abs(pv - st[f]) <= 0.01:
                continue
            ok = False
            break
        # total_marks: print may leave the grand Total blank while stating
        # the components — print-consistent when components agree with storage
        if f == "total_marks" and pv is None:
            comp_ok = all(
                merged.get(g) is None or (st[g] is not None and abs(merged[g] - st[g]) <= 0.01)
                for g in ("sessional_total", "ese_te_pe"))
            if comp_ok and ("sessional_total" in merged or "ese_te_pe" in merged):
                continue
            ok = False
            break
        if isinstance(pv, float) and st[f] is not None and abs(pv - st[f]) <= 0.01:
            continue
        ok = False
        break
    if ok and failed:
        return ("accepted-print", {"fields": merged, "cand": cands[0]})
    return ("keep", f"print mapped but does not verify {sorted(failed)} (mapped={merged})")


def alias_consistent(rp, st, alias):
    for af, av in alias.items():
        rv = rp.get(af, st[af])
        if rv is None or rv == "":
            return False
        if abs(float(rv) - av) > 0.01:
            return False
    return True


def safe_repair(rp, alias):
    for f, vv in rp.items():
        if f in ("L", "T", "P"):
            return False
        if f == "credit":
            if alias.get("credit") is None or abs(float(vv) - alias["credit"]) > 0.01:
                return False
        if f in ("sessional_ct", "sessional_ta") and vv != "":
            return False
        if f in ("sessional_total", "ese_te_pe", "total_marks") \
                and vv != "" and alias.get(f) is None:
            return False
    return True


def multiset_verdict(st, failed, cands, alias):
    """W9b-style fallback over line-window candidates (no pmap)."""
    stored_nums = [x for x in (st[f] for f in FIELDS) if x is not None]
    for c in cands:
        if Counter(c["nums"]) == Counter(stored_nums):
            return ("accepted-print", {"cand": c, "fields": None})
    if alias and failed:
        if all(f in alias and st[f] is not None and abs(st[f] - alias[f]) <= 0.01
               for f in failed):
            return ("accepted-print", None)
    uniq = {}
    for c in cands:
        repairs, _ = W9B.candidate_repairs(st, c["nums"])
        repairs = [rp for rp in repairs if alias_consistent(rp, st, alias)]
        repairs = [rp for rp in repairs if safe_repair(rp, alias)]
        if not repairs:
            continue
        m = min(len(rp) for rp in repairs)
        for rp in repairs:
            if len(rp) == m:
                uniq[json.dumps(rp, sort_keys=True)] = (rp, c)
    if len(uniq) == 1:
        rp, c = list(uniq.values())[0]
        # B80 evidence standard: line-window repairs are not column-exact
        # (adjacent-row digit bleed) — demote to keep, never fix from them
        return ("keep", f"line-window print supports a repair {rp} but capture is not column-exact — stays flagged")
    if len(uniq) > 1:
        return ("ambiguous", f"{len(uniq)} distinct repairs")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--smoke", type=int, default=0)
    args = ap.parse_args()

    rows = WC.load_rows()
    by_id = {r["subject_id"]: r for r in rows}
    fl = json.load(open(FLAGS))
    targets = []
    for sid, fls in fl["rows"].items():
        cls = [f["rule"] for f in fls if f["rule"] in RULES3]
        if not cls:
            continue
        r = by_id.get(sid)
        if not r:
            continue
        st = stored_vector(r)
        failed = set(failed_invariants(st))
        if not failed:
            failed = {RULE2FIELD[c] for c in cls}
        codes = [r.get("primary_code", "")] + \
            [t.strip() for t in (r.get("all_codes", "") or "").split(";") if t.strip()]
        # provenance-cited codes: shared subjects print under branch-variant
        # codes (KNC501 in the CSE doc, BNC501 in the Civil doc) that the
        # all_codes column may not enumerate; the row's own provenance text
        # cites those variants verbatim — not a guess (print-cited tokens)
        for col in ("source_scheme_line", "source_history"):
            for mtok in re.findall(r"(?:[A-Z]{2,6})\s?(?:\d{2,3}[A-Z]?|MK\d{2})",
                                   (r.get(col, "") or "")):
                tok = re.sub(r"[^A-Z0-9]", "", mtok.upper())
                if len(tok) >= 5 and tok not in {re.sub(r"[^A-Z0-9]", "", c.upper()) for c in codes}:
                    codes.append(mtok.strip())
        seen = set()
        codes = [c for c in codes if c and not (c in seen or seen.add(c))]
        targets.append({"sid": sid, "codes": codes, "failed": sorted(failed),
                        "stored": st})
    if args.smoke:
        targets = targets[:args.smoke]
    print(f"W10G|targets={len(targets)}", flush=True)

    ck = {"results": {}}
    if os.path.exists(CKPT) and os.environ.get("W10G_RESUME", "") == "1":
        ck = json.load(open(CKPT))
    res = ck.setdefault("results", {})

    t0 = time.time()
    n_new = 0
    for t in targets:
        sid = t["sid"]
        if sid in res:
            continue
        if time.time() - t0 > BUDGET_S:
            print(f"W10G|budget_stop|done={n_new}", flush=True)
            break
        r = by_id[sid]
        st = t["stored"]
        alias = {}
        q = parse_primary_quote(r)
        if q["cr"] is not None:
            alias["credit"] = q["cr"]
        if q["ltp"]:
            alias["L"], alias["T"], alias["P"] = q["ltp"]
        if q["sw"] is not None and "sessional_total" not in alias:
            alias["sessional_total"] = q["sw"]
        if q["ps"] is not None and "sessional_total" not in alias:
            alias["sessional_total"] = q["ps"]
        if q["te"] is not None and "ese_te_pe" not in alias:
            alias["ese_te_pe"] = q["te"]
        for k in ("ct", "ta", "ese", "total"):
            if q.get(k) is not None:
                alias[{"ct": "sessional_ct", "ta": "sessional_ta",
                       "ese": "ese_te_pe", "total": "total_marks"}[k]] = q[k]

        docs = scheme_docs(r)[:6]
        # §3 latest-print-wins: govern by the doc with the NEWEST session tag
        # in its filename (provenance order kept as tiebreak; W9b trusted the
        # provenance order, but B80 evidence shows a 2022-23 doc can sit first
        # in source_scheme_line while the row's effective session is 2024-25)
        def _sess_key(sha_pin):
            m = re.search(r"(20\d{2})-(\d{2})",
                          os.path.basename(resolve(sha_pin[0]) or ""))
            return (-(int(m.group(1)) * 100 + int(m.group(2))) if m else 9)
        docs = sorted(docs, key=_sess_key)
        docs_tried = []
        gov_cands = []     # candidates from the governing (newest) doc
        older_prints = []  # conflicting mapped evidence from older docs
        gov = None
        n_lines = 0
        for sha, pin in docs:
            path = resolve(sha)
            if not path or not os.path.exists(path):
                docs_tried.append(f"{sha}:unresolved")
                continue
            d = doc_open(sha, path)
            if d is None:
                docs_tried.append(f"{sha}:unreadable")
                continue
            docs_tried.append(f"{os.path.basename(path)}#{sha}")
            cands = row_candidates_tables(sha, d, t["codes"])
            if not cands:
                cands = row_candidates_lines(sha, d, t["codes"])
                n_lines += len(cands)
            mapped = [c for c in cands if c["pmap"]]
            if gov is None:
                if cands:
                    gov = sha
                    gov_cands = cands
                continue
            for c in mapped:
                older_prints.append({f: c["pmap"].get(f) for f in
                                     ("credit", "sessional_total",
                                      "total_marks")})

        verdict = None
        detail = None
        gov_mapped = [c for c in gov_cands if c["pmap"]]
        gov_unmapped = [c for c in gov_cands if not c["pmap"]]
        if gov_mapped:
            verdict, detail = mapped_verdict(st, t["failed"], gov_mapped)
        if verdict is None and gov_unmapped:
            mv = multiset_verdict(st, t["failed"], gov_unmapped, alias)
            if mv:
                verdict, detail = mv
        if verdict is None:
            verdict = "no_print_found"
            detail = docs_tried

        c = None
        v = {"status": verdict}
        if verdict == "fixed":
            v["fields"] = detail.get("fields") if isinstance(detail, dict) else detail
            if isinstance(detail, dict):
                c = detail.get("cand")
        elif verdict == "accepted-print" and isinstance(detail, dict):
            c = detail.get("cand")
            if detail.get("fields"):
                v["mapped"] = detail["fields"]
            else:
                v["mapped"] = {k: detail.get(k) for k in
                               ("credit", "sessional_total", "total_marks",
                                "sessional_ct", "sessional_ta", "ese_te_pe")
                               if k in detail}
        elif isinstance(detail, dict):
            v["mapped"] = {k: detail.get(k) for k in
                           ("credit", "sessional_total", "total_marks",
                            "sessional_ct", "sessional_ta", "ese_te_pe")
                           if k in detail}
        if c:
            v["evidence"] = f"{os.path.basename(resolve(gov))}#{gov} p.{c['page']}"
            v["rowtext"] = c.get("rowtext", "")[:200]
        elif verdict == "accepted-print" and gov:
            v["evidence"] = f"{os.path.basename(resolve(gov))}#{gov}"
        if older_prints:
            v["older_prints"] = older_prints[:2]
        if verdict == "no_print_found":
            v["docs_tried"] = docs_tried
        v["via"] = {"lines": n_lines, "gov": gov}
        res[sid] = v
        n_new += 1
        if n_new % 15 == 0:
            json.dump(ck, open(CKPT, "w"), indent=1, ensure_ascii=False)
            print(f"W10G|progress|done={n_new}", flush=True)

    ck["results"] = res
    json.dump(ck, open(CKPT, "w"), indent=1, ensure_ascii=False)
    summ = Counter(v["status"] for v in res.values())
    print(f"W10G_PROBE|done={n_new}|total={len(res)}|{dict(summ)}", flush=True)

    if not args.apply:
        return 0
    apply_changes(res, targets, fl, by_id)


def apply_changes(res, targets, fl, by_id):
    RULE2FIELD_L = RULE2FIELD
    edits = []
    notes_map = {}
    failed_by_sid = {t["sid"]: t["failed"] for t in targets}
    for sid, v in res.items():
        if by_id.get(sid) is None:
            continue
        seg = None
        if v["status"] == "accepted-print":
            fls = [f["rule"] for f in fl["rows"].get(sid, []) if f["rule"] in RULES3]
            flds = ",".join(sorted({RULE2FIELD_L[c] for c in fls})) or "scheme"
            mapped = v.get("mapped") or {}
            mp = " ".join(f"{k}={mapped[k]}" for k in sorted(mapped)) or "quote-verified"
            seg = (f"{MARK} accepted-print @ {flds} at {v.get('evidence','provenance-quote')}"
                   f" newest-print-wins printed[{mp}] row={v.get('rowtext','')[:110]}")
        elif v["status"] == "fixed":
            rp = v["fields"]
            ev = v.get("evidence", "")
            for f, nv in rp.items():
                cur = WC.field_get(by_id[sid], f)
                edits.append({"sid": sid, "field": f, "before": "" if cur is None else str(cur),
                              "after": fmt_val(nv), "rule": "W10G_SCHEME",
                              "evidence": f"{ev} header-mapped printed scheme row: {v.get('rowtext','')[:110]}"})
            seg = f"{MARK} fixed @ {','.join(sorted(rp))} at {ev} (header-mapped print proves extraction error, §6b(4))"
        elif v["status"] == "ambiguous":
            seg = f"{MARK} ambiguous @ {v.get('evidence','') or v.get('docs_tried','')[:1]} printed rows conflict/not adjudicable — stays flagged"
        elif v["status"] == "keep":
            seg = f"{MARK} keep @ {v.get('evidence','')} printed row mapped but does not verify the flagged fields — stays flagged"
        else:
            seg = (f"{MARK} no_print_found @ cited scheme docs scanned"
                   f" ({', '.join(v.get('docs_tried', [])[:3]) or 'none resolvable'})"
                   f" — no printed scheme row recoverable")
        if seg:
            notes_map[sid] = seg
    rows2 = WC.load_rows()
    by_id2 = {r["subject_id"]: r for r in rows2}
    n_notes = 0
    for sid, seg in notes_map.items():
        r = by_id2.get(sid)
        if r is None or seg in (r.get("notes", "") or ""):
            continue
        r["notes"] = ((r.get("notes", "") + " | ") if r.get("notes", "") else "") + seg
        n_notes += 1
    edits_applied = 0
    skipped = []
    if edits:
        for e in edits:
            r = by_id2[e["sid"]]
            cur = WC.field_get(r, e["field"])
            cur = "" if cur is None else str(cur)
            if cur != e["before"]:
                skipped.append((e["sid"], e["field"], f"cell changed {cur!r}!={e['before']!r}"))
                continue
            WC.field_set(r, e["field"], e["after"])
            cjson = json.loads(r.get("corrections_json", "") or "[]")
            cjson.append({"field": e["field"], "before": e["before"],
                          "after": e["after"], "rule": e["rule"],
                          "evidence": e["evidence"], "wave": "W10G"})
            r["corrections_json"] = json.dumps(cjson, ensure_ascii=False)
            r["verification_status"] = "corrected"
            qf = [f for f in (r.get("quality_flags", "") or "").split(";") if f.strip()]
            if f"corrected_{e['rule']}" not in qf:
                qf.append(f"corrected_{e['rule']}")
            r["quality_flags"] = ";".join(qf)
            seg2 = "W10G(W10G_SCHEME): scheme-number fix from header-mapped printed scheme row per RULES §6b(4) — before-form preserved in corrections_json"
            if seg2 not in (r.get("change_note_vs_previous", "") or ""):
                r["change_note_vs_previous"] = ((r.get("change_note_vs_previous", "") + "; ") if r.get("change_note_vs_previous", "") else "") + seg2
            edits_applied += 1
    touched = sorted(set(list(notes_map.keys()) + [e["sid"] for e in edits]))
    pre_rows_by_id = {r["subject_id"]: dict(r) for r in WC.load_rows()}
    gates = WC.run_gates(rows2, touched, pre_rows_by_id)
    print("GATES|", json.dumps({k: v for k, v in gates.items() if k != "g6_checks"}))
    WC.commit(rows2, "W10G_B80_scheme_reprobe", edits_applied, gates,
              meta_extra={"notes_appended": n_notes, "skipped": skipped[:8]})
    print(f"W10G_APPLY|notes={n_notes}|fixes={edits_applied}|skipped={skipped[:4]}")


def fmt_val(nv):
    if nv == "":
        return ""
    return str(int(nv)) if float(nv) == int(float(nv)) else str(nv)


if __name__ == "__main__":
    sys.exit(main())
