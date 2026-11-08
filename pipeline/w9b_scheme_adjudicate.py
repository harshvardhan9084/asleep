#!/usr/bin/env python3
"""w9b_scheme_adjudicate.py — W9b: scheme adjudications 401 (owner go
"Do [BOOK_TRUNC 574, scheme adjudications 401, W8c memo 71] now", 2026-11-08).

Classes: CREDIT_FORMULA 142 + SESS_SUM 133 + MARKS_SUM 126 (296 rows).
Adjudication per RULES §3 (latest print wins field-wise) and §6b(4) ("No
correction may change printed marks/scheme numbers without the scheme line
proving the extraction error"):

  probe    — find the printed scheme table row for the subject's code in the
             cited docs (source_scheme_line doc = primary/newest first, then
             source_history; verbatim pipe rows embedded in provenance parsed
             directly). Numbers captured per printed row (SN stripped,
             'N Hr' durations stripped).
  verdicts — printed_vec == stored_vec  -> accepted-print (the print itself
             violates the L+T+P/2 / component-sum arithmetic; the row
             faithfully mirrors the print — AKTU's own inconsistency)
             unique repair from printed numbers satisfying ALL applicable
             invariants (credit=L+T+P/2 OR print-consistent, total=sess+ese,
             sess=ct+ta, fields emptied when the print lacks the slot)
             -> fix-from-print (§3 latest-wins, corrections_json before/after)
             stored matches an older print while newest differs -> fix
             ambiguous or not found -> needs_review with probe note.

Owner directives: budget-guarded chunks (W9B_BUDGET) + checkpoint; no keys;
no rr_sid; T2T 0 (deterministic).
"""
import argparse
import json
import os
import re
import sys
import time

import fitz

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC
from collections import Counter

BASE = WC.BASE
CKPT = f"{BASE}/w9b_ckpt.json"
BUDGET_S = float(os.environ.get("W9B_BUDGET", "240"))
SMOKE = os.environ.get("W9B_SMOKE", "") == "1"
CORPUS = json.load(open(f"{BASE}/corpus_map.json"))
CODE_RE = re.compile(r"^[A-Z]{2,4}[- ]?[0-9]{3}[A-Z]?$")


def num(s):
    if s is None or s == "":
        return None
    try:
        v = float(str(s).strip())
        return v
    except Exception:
        return None


def stored_vector(r):
    keys = ["L", "T", "P", "sessional_ct", "sessional_ta", "sessional_total",
            "ese_te_pe", "total_marks", "credit"]
    return {k: num(r.get(k)) for k in keys}


def failed_invariants(v):
    out = []
    v = {k: num(x) for k, x in v.items()}
    L, T, P, cr = v["L"], v["T"], v["P"], v["credit"]
    if None not in (L, T, P, cr) and abs(cr - (L + T + P / 2)) > 0.01:
        out.append("credit")
    stt, ese, tm = v["sessional_total"], v["ese_te_pe"], v["total_marks"]
    if None not in (stt, ese, tm) and abs(tm - (stt + ese)) > 0.01:
        out.append("total_marks")
    ct, ta = v["sessional_ct"], v["sessional_ta"]
    if None not in (ct, ta, stt) and abs(stt - (ct + ta)) > 0.01:
        out.append("sessional_total")
    return out


def resolve(sha):
    if sha in CORPUS:
        return CORPUS[sha]
    hits = [v for k, v in CORPUS.items() if k.startswith(sha)]
    return hits[0] if len(hits) == 1 else None


def scheme_docs(r):
    """[(sha, pinned_page_or_None)] primary/newest first."""
    out, seen = [], set()
    for col in ("source_scheme_line", "source_history"):
        s = r.get(col, "") or ""
        for m in re.finditer(r"([^;#]+?\.pdf)#([0-9a-f]{12,16})", s):
            sha = m.group(2)
            tail = s[m.end():m.end() + 24]
            pm = re.match(r"\s+pp?\.(\d{1,4})\b", tail)
            pin = int(pm.group(1)) if pm else None
            if sha not in seen:
                seen.add(sha)
                out.append((sha, pin))
    return out


def provenance_verbatim(r, codes):
    """Verbatim pipe/number rows quoted inside the provenance itself."""
    out = []
    for col in ("source_scheme_line", "source_history"):
        s = r.get(col, "") or ""
        for seg in re.split(r"[;\n]", s):
            if "|" not in seg:
                continue
            sq = re.sub(r"[^A-Za-z0-9]", "", seg).upper()
            for c in codes:
                csq = re.sub(r"[^A-Z0-9]", "", c.upper())
                if csq and csq in sq:
                    out.append(seg.strip())
                    break
    return out


def printed_row_numbers(doc_path, codes, pin=None, max_pages=None):
    """Find the printed scheme row for any of `codes`; return number list."""
    try:
        d = fitz.open(doc_path)
    except Exception:
        return None
    code_sq = {re.sub(r"[^A-Z0-9]", "", c.upper()): c for c in codes if c}
    pages = []
    if pin is not None and 0 <= pin - 1 < d.page_count:
        pages.append(pin - 1)
    pin_i = pin - 1 if pin is not None else None
    rest = [i for i in range(d.page_count) if i != pin_i]
    if max_pages:
        rest = rest[:max_pages]
    pages += rest
    try:
        for pno in pages:
            txt = d[pno].get_text() or ""
            if not txt.strip():
                continue
            lines = txt.splitlines()
            for li, ln in enumerate(lines):
                sq = re.sub(r"[^A-Za-z0-9]", "", ln).upper()
                hit_code = None
                for csq in code_sq:
                    if len(csq) >= 5 and csq in sq:
                        hit_code = csq
                        break
                if not hit_code:
                    continue
                # capture the row: this line + continuations until a line with
                # another code or a long alphabetic-only line
                buf = [ln]
                for nxt in lines[li + 1:li + 3]:
                    nsq = re.sub(r"[^A-Za-z0-9]", "", nxt).upper()
                    if any(len(c) >= 5 and c in nsq for c in code_sq):
                        break
                    nums_here = re.findall(r"\d+(?:\.\d+)?", nxt)
                    if not nums_here:
                        break
                    buf.append(nxt)
                rowtxt = " ".join(buf)
                # strip leading SN ('5.' / '5 |' / 'SN5')
                rowtxt = re.sub(r"^\s*(?:SN)?\d{1,2}\s*[\.\|]\s*", "", rowtxt.strip())
                # remove the code tokens themselves (avoid digits in codes)
                rowtxt = re.sub(r"[A-Z]{2,4}[- ]?[0-9]{3}[A-Z]?", " ", rowtxt)
                # remove duration numbers ('3 Hr', '3Hr')
                rowtxt = re.sub(r"\d+(?:\.\d+)?\s*(?:Hr|HR|hr)\b", " ", rowtxt)
                nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", rowtxt)]
                if len(nums) >= 4:
                    return {"page": pno + 1, "numbers": nums,
                            "rowtext": re.sub(r"\s+", " ", rowtxt).strip()[:200]}
    finally:
        d.close()
    return None



NUMTOK = re.compile(r"\d+(?:\.\d+)?")



def clean_scheme_text(txt):
    """Kill filename/sha/page/ordinal/SN/code/duration digit noise from a
    quoted or probed scheme-row text before number capture."""
    t = txt or ""
    t = re.sub(r"\S*\.pdf", " ", t)
    t = re.sub(r"#[0-9a-fA-F]{6,16}", " ", t)
    t = re.sub(r"\bpp?\.\d+\b", " ", t)
    t = re.sub(r"\bSN-?\d+\b", " ", t)
    t = re.sub(r"(?<![A-Za-z0-9])\d{1,2}\s*\.\s*(?=\|)", " ", t)  # '7. |' ordinals
    t = re.sub(r"\bsem-[IVX]+\b", " ", t, flags=re.I)
    t = re.sub(r"[A-Z]{2,4}[- ]?[0-9]{3}[A-Z]?", " ", t)
    t = re.sub(r"\d+(?:\.\d+)?\s*(?:Hr|HR|hr)\b", " ", t)
    return t


def parse_primary_quote(r):
    """Structured values quoted from the PRIMARY (newest) scheme doc inside
    source_scheme_line: L-T-P triples, 'N cr', 'N SW', 'PS N + TE N', bare
    numbers. Returns {cr, sw, ltp, marks:[...] , raw:[...]} (None = not said)."""
    ssl = r.get("source_scheme_line", "") or ""
    first = re.split(r";\s*", ssl)[0] if ssl else ""
    first = clean_scheme_text(first)
    out = {"cr": None, "sw": None, "ltp": None, "ps": None, "te": None,
           "raw": [], "text": first[:160]}
    m = re.search(r"(\d+)\s*-\s*(\d+)\s*-\s*(\d+)", first)
    if m:
        out["ltp"] = (float(m.group(1)), float(m.group(2)), float(m.group(3)))
    m = re.search(r"(\d+(?:\.\d+)?)\s*cr\b", first, re.I)
    if m:
        out["cr"] = float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*SW\b", first, re.I)
    if m:
        out["sw"] = float(m.group(1))
    m = re.search(r"PS\s*(\d+(?:\.\d+)?)\s*\+\s*TE\s*(\d+(?:\.\d+)?)", first, re.I)
    if m:
        out["ps"] = float(m.group(1))
        out["te"] = float(m.group(2))
    for lab, key in (("CT", "ct"), ("TA", "ta"), ("ESE", "ese"),
                     ("TOTAL(?:\\s*MARKS)?", "total"), ("SW", "sw2")):
        mm = re.search(lab + r"\s*:?\s*(\d+(?:\.\d+)?)", first, re.I)
        if mm:
            out.setdefault(key, float(mm.group(1)))
    out["raw"] = [float(x) for x in NUMTOK.findall(first)]
    return out



# --- invariant-gated unique repair search ------------------------------------
FIELDS = ["L", "T", "P", "sessional_ct", "sessional_ta", "sessional_total",
          "ese_te_pe", "total_marks", "credit"]


def invariants_ok(v):
    f = failed_invariants(v)
    return not f, f


def candidate_repairs(stored, printed_nums, limit=60000):
    """All vectors reachable by changing 1-3 fields to printed numbers (or ''
    when the print plausibly lacks the slot) that satisfy all invariants."""
    st = dict(stored)
    from itertools import combinations
    pn = sorted(set(printed_nums))
    repairs = []
    slots = [f for f in FIELDS]
    n = 0
    for k in (1, 2, 3):
        for combo in combinations(slots, k):
            opts = []
            for f in combo:
                o = [x for x in pn if x != st[f]]
                if f in ("sessional_ct", "sessional_ta") and "" not in o:
                    o = o + [""]  # print may lack the component split
                opts.append([(x, x) for x in o])
            for pick in _product(opts):
                v = dict(st)
                for (f, (old, newv)) in zip(combo, pick):
                    v[f] = newv
                n += 1
                if n > limit:
                    return repairs, False
                ok, _ = invariants_ok(v)
                if ok:
                    delta = {f: v[f] for f in FIELDS if v[f] != st[f]}
                    # every CHANGED value must come from the print (zero-guess)
                    if delta and all(x is None or x == "" or x in pn
                                     for x in delta.values()):
                        # ct/ta emptying must be symmetric (a print lacks the
                        # component split entirely, never one half of it)
                        e1 = delta.get("sessional_ct") == ""
                        e2 = delta.get("sessional_ta") == ""
                        n1 = "sessional_ct" in delta
                        n2 = "sessional_ta" in delta
                        if (n1 or n2) and (e1 != e2):
                            continue
                        repairs.append(delta)
    return repairs, True


def _product(opts):
    from itertools import product
    return product(*opts)


def vec_multiset(v):
    xs = [x for x in (v[f] for f in FIELDS) if x is not None]
    from collections import Counter
    return Counter(xs)


# --- stages ------------------------------------------------------------------
def stage_classify():
    rows = WC.load_rows()
    by_id = {r["subject_id"]: r for r in rows}
    fl = json.load(open(f"{BASE}/audit_flags.json"))
    plan = []
    seen = set()
    for sid, fls in fl["rows"].items():
        for f in fls:
            if f["rule"] not in ("CREDIT_FORMULA", "SESS_SUM", "MARKS_SUM"):
                continue
            if sid in seen:
                break
            seen.add(sid)
            r = by_id.get(sid)
            if not r:
                continue
            codes = [r.get("primary_code", "")] + \
                [t.strip() for t in (r.get("all_codes", "") or "").split(";") if t.strip()]
            plan.append({"sid": sid, "codes": codes,
                         "stored": stored_vector(r),
                         "failed": failed_invariants(stored_vector(r))})
    if SMOKE:
        plan = plan[:3]
    json.dump(plan, open(f"{BASE}/w9b_plan.json", "w"), indent=1)
    print(f"W9B_CLASSIFY|rows={len(plan)}")
    return 0


def stage_probe():
    plan = json.load(open(f"{BASE}/w9b_plan.json"))
    ck = json.load(open(CKPT)) if os.path.exists(CKPT) else {"results": {}}
    res = ck["results"]
    t0 = time.time()
    rows = WC.load_rows()
    by_id = {r["subject_id"]: r for r in rows}
    todo = [p for p in plan if p["sid"] not in res]
    if SMOKE:
        todo = todo[:3]
    print(f"W9B_PROBE|todo={len(todo)}|budget={BUDGET_S}s", flush=True)
    done = 0
    for p in todo:
        if time.time() - t0 > BUDGET_S:
            print(f"W9B_PROBE|budget_stop|done={done}", flush=True)
            break
        r = by_id[p["sid"]]
        entry = None
        ver = provenance_verbatim(r, p["codes"])
        if ver:
            rowtxt = clean_scheme_text(ver[0])
            rowtxt = re.sub(r"(?:CT|TA|ESE|Total|SESSIONAL|PS|TE|PE|CT\+TA)\s*:\s*",
                            " ", rowtxt, flags=re.I)
            nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", rowtxt)]
            if len(nums) >= 4:
                entry = {"page": 0, "numbers": nums, "rowtext": ver[0][:200],
                         "via": "provenance"}
        docs = scheme_docs(r)
        if entry is None:
            for sha, pin in docs:
                path = resolve(sha)
                if not path or not os.path.exists(path):
                    continue
                e = printed_row_numbers(path, p["codes"], pin=pin, max_pages=400)
                if e:
                    e["via"] = f"{os.path.basename(path)}#{sha}"
                    entry = e
                    break
        res[p["sid"]] = entry or {"miss": True, "docs_tried": [s for s, _ in docs]}
        done += 1
        if done % 10 == 0:
            ck["results"] = res
            json.dump(ck, open(CKPT, "w"), indent=1, ensure_ascii=False)
    ck["results"] = res
    json.dump(ck, open(CKPT, "w"), indent=1, ensure_ascii=False)
    from collections import Counter
    c = Counter("miss" if v.get("miss") else "hit" for v in res.values())
    print(f"W9B_PROBE|done={done}|total={len(res)}|{dict(c)}")
    return 0


def stage_adjudicate():
    plan = json.load(open(f"{BASE}/w9b_plan.json"))
    ck = json.load(open(CKPT))
    res = ck["results"]
    rows = WC.load_rows()
    by_id = {r["subject_id"]: r for r in rows}
    from collections import Counter
    summ = Counter()
    edits = []
    verdicts = {}
    for p in plan:
        sid = p["sid"]
        r = by_id[sid]
        st = p["stored"]
        failed = set(p["failed"])
        quote = parse_primary_quote(r)
        pr = res.get(sid)
        # assemble primary-print evidence: structured quote fields + raw numbers
        via_bits = []
        if quote["cr"] is not None or quote["ltp"] or quote["raw"]:
            via_bits.append("provenance-quote")
        if pr and not pr.get("miss") and pr.get("via") == "provenance":
            raw_nums = list(pr["numbers"])  # same source as the quote - no union
            via_bits.append("provenance-pipe")
        else:
            raw_nums = list(quote["raw"])
            if pr and not pr.get("miss"):
                raw_nums = raw_nums + pr["numbers"]
                via_bits.append(pr.get("via", "doc-probe") + (f" p.{pr['page']}" if pr.get("page") else ""))
        if not raw_nums and not (pr and not pr.get("miss")):
            st_status = "sha_unresolved" if all(not B_resolve(sha) for sha, _ in scheme_docs(r)) \
                else "no_print_found"
            verdicts[sid] = {"status": st_status}
            summ[st_status] += 1
            continue

        # structured alias values from the primary quote
        alias = {}
        if quote["cr"] is not None:
            alias["credit"] = quote["cr"]
        if quote["ltp"]:
            alias["L"], alias["T"], alias["P"] = quote["ltp"]
        if quote["sw"] is not None:
            alias["sessional_total"] = quote["sw"]
        if quote["ps"] is not None:
            alias["sessional_total"] = quote["ps"]
        if quote["te"] is not None:
            alias["ese_te_pe"] = quote["te"]
        if quote.get("ct") is not None:
            alias["sessional_ct"] = quote["ct"]
        if quote.get("ta") is not None:
            alias["sessional_ta"] = quote["ta"]
        if quote.get("ese") is not None:
            alias["ese_te_pe"] = quote["ese"]
        if quote.get("total") is not None:
            alias["total_marks"] = quote["total"]
        if quote.get("sw2") is not None and "sessional_total" not in alias:
            alias["sessional_total"] = quote["sw2"]

        # 0) accepted-print: the printed row's number multiset EQUALS the
        #    stored vector's multiset -> the row faithfully mirrors the print;
        #    the arithmetic break lives in AKTU's own scheme table
        stored_nums = [x for x in (st[f] for f in FIELDS) if x is not None]
        if Counter(stored_nums) == Counter(raw_nums):
            verdicts[sid] = {"status": "accepted-print",
                             "evidence": "; ".join(via_bits),
                             "rowtext": (pr.get("rowtext", "") if pr and not pr.get("miss") else quote["text"])}
            summ["accepted-print"] += 1
            continue

        # 1) accepted-print: every flagged field that the primary print states
        #    agrees with storage (the print itself breaks the arithmetic)
        checked = 0
        ok = True
        for f in failed:
            if f in alias:
                checked += 1
                if st[f] is None or abs(st[f] - alias[f]) > 0.01:
                    ok = False
                    break
        if ok and checked:
            verdicts[sid] = {"status": "accepted-print",
                             "evidence": "; ".join(via_bits),
                             "rowtext": quote["text"]}
            summ["accepted-print"] += 1
            continue

        # 2) unique invariant repair from printed numbers, filtered by the
        #    print's own structured column assignment (alias): a repair may
        #    not contradict any column the print states
        repairs, _ = candidate_repairs(st, raw_nums)
        def _alias_consistent(rp):
            for af, av in alias.items():
                rv = rp.get(af, st[af])
                if rv is None or rv == "":
                    return False  # emptying a print-stated column contradicts it
                if abs(float(rv) - av) > 0.01:
                    return False
            return True
        repairs = [rp for rp in repairs if _alias_consistent(rp)]

        # SAFE-REPAIR policy (W9b): no L/T/P changes (contact-hour semantics
        # need full column mapping); credit only to its print-stated value;
        # ct/ta only emptied, never renumbered; marks fields only to values
        # the print states in a labeled/structured position.
        def _safe(rp):
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
        repairs = [rp for rp in repairs if _safe(rp)]
        # prefer minimal-cardinality repairs, then invariant-relevant fields
        if repairs:
            # 1) prefer the print-lacks-the-split reading (empty ct/ta) over
            #    inventing a component split - ONLY when the failed invariants
            #    actually involve the sessional/marks chain (never for a
            #    credit-only mismatch: unflagged marks stay untouched)
            if "sessional_total" in failed or "total_marks" in failed:
                emptied = [rp for rp in repairs
                           if rp.get("sessional_ct") == "" and rp.get("sessional_ta") == ""]
                if emptied:
                    repairs = emptied
            # 2) minimal-cardinality
            m = min(len(rp) for rp in repairs)
            repairs = [rp for rp in repairs if len(rp) == m]
            # 3) invariant-relevant fields only
            inv_fields = set(failed) | {"sessional_ct", "sessional_ta"}
            tight = [rp for rp in repairs if set(rp) <= inv_fields]
            if tight:
                repairs = tight
        uniq = {json.dumps(g, sort_keys=True): g for g in repairs}
        ev = "; ".join(via_bits)
        if len(uniq) == 1:
            rp = list(uniq.values())[0]
            verdicts[sid] = {"status": "fixed", "fields": rp,
                             "evidence": ev, "rowtext": quote["text"]}
            edits.append((sid, rp))
            summ["fixed"] += 1
        elif len(uniq) > 1:
            verdicts[sid] = {"status": "ambiguous", "n": len(uniq),
                             "evidence": ev, "rowtext": quote["text"]}
            summ["ambiguous"] += 1
        else:
            verdicts[sid] = {"status": "stored_matches_no_print",
                             "evidence": ev, "rowtext": quote["text"]}
            summ["stored_matches_no_print"] += 1
    json.dump({"verdicts": verdicts,
               "summary": dict(summ),
               "edits": edits}, open(f"{BASE}/w9b_adjudication.json", "w"),
              indent=1, ensure_ascii=False)
    print(f"W9B_ADJUDICATE|{dict(summ)}")
    return 0


def B_resolve(sha):
    return resolve(sha)


def stage_apply():
    adj = json.load(open(f"{BASE}/w9b_adjudication.json"))
    edits = adj["edits"]
    rows = WC.load_rows()
    by_id = {r["subject_id"]: r for r in rows}
    FIELD_COL = {f: f for f in FIELDS}
    wl = []
    for sid, rp in edits:
        for f, newv in rp.items():
            cur = by_id[sid].get(FIELD_COL[f], "") or ""
            if cur.strip() == "":
                curv = ""
            else:
                curv = cur.strip()
            newvs = "" if newv == "" else (f"{newv:g}" if isinstance(newv, float) else str(newv))
            wl.append({"sid": sid, "field": FIELD_COL[f], "before": curv,
                       "after": newvs, "rule": "W9b/SCHEME_LATEST_PRINT",
                       "evidence": "printed scheme row " + adj["verdicts"][sid].get("evidence", "")
                                   + f" — printed row: {adj['verdicts'][sid].get('rowtext', '')[:120]}"})
    # merge per-sid multi-field edits into change-note-friendly order
    rows, per_sid, skipped = WC.apply_edits(rows, wl, "W9b", None,
                                            note_extra="W9b scheme adjudication (latest print wins / print-proved extraction error)")
    WC.commit(rows, "W9b", len(wl) - len(skipped), {"note": "gates by caller"},
              meta_extra={"wave": "W9b", "field_edits": len(wl) - len(skipped),
                          "rows": len(per_sid), "skipped": len(skipped)})
    if skipped:
        print("W9B_APPLY_SKIPS:", skipped[:5])
    print(f"W9B_APPLY|field_edits={len(wl) - len(skipped)}|rows={len(per_sid)}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["classify", "probe", "adjudicate", "apply"])
    a = ap.parse_args()
    sys.exit({"classify": stage_classify, "probe": stage_probe,
              "adjudicate": stage_adjudicate, "apply": stage_apply}[a.stage]())
